"""Case orchestration: documents -> extraction -> facts -> mappings -> rules -> draft -> chain -> CaseResult.

State is kept as plain JSON so a case can be re-run (step change: rules only) or extended (new document:
extraction only for the new document, rules for everything) without repeating LLM calls.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Optional

from .chain import build_chain, build_claim_summary
from .draft import build_draft
from .extract import extract_documents, run_mappings
from .facts import build_fact_table
from .llm import LLM, get_llm
from .models import (AbstainFlags, CaseDiff, CaseResult, Document, DocumentSummary, Extraction, MappingRun, RejectedFact, Span,
                     StatedFields)
from .rules.engine import RulesInput, run_rules


def _ex_to_json(doc: Document, ex: Extraction, span: Span) -> dict[str, Any]:
    return {"doc_id": doc.id, "extraction": ex.model_dump(), "span": span.model_dump()}


def _ex_from_json(docs: dict[str, Document], item: dict[str, Any]):
    return docs[item["doc_id"]], Extraction(**item["extraction"]), Span(**item["span"])


def new_state(docs: list[Document], step: str, stated: StatedFields, abstain: AbstainFlags, notes: str = "", case_id: Optional[str] = None) -> dict[str, Any]:
    return {"case_id": case_id or f"case_{uuid.uuid4().hex[:10]}", "documents": [d.model_dump() for d in docs], "step": step,
            "stated": stated.model_dump(), "abstain": abstain.model_dump(), "notes_ignored": notes, "extractions": [],
            "rejected": [], "mappings": [], "meta": {}, "result": None}


def run_extraction(state: dict[str, Any], only_doc_ids: Optional[list[str]] = None, llm: Optional[LLM] = None) -> None:
    llm = llm or get_llm()
    docs = [Document(**d) for d in state["documents"]]
    todo = [d for d in docs if only_doc_ids is None or d.id in only_doc_ids]
    verified, rejected, meta = extract_documents(todo, llm)
    keep_ids = {d.id for d in todo}
    state["extractions"] = [e for e in state["extractions"] if e["doc_id"] not in keep_ids] + [_ex_to_json(d, ex, sp) for d, ex, sp in verified]
    state["rejected"] = [r for r in state["rejected"] if r["doc_id"] not in keep_ids] + [r.model_dump() for r in rejected]
    state["meta"].update({k: v for k, v in meta.items()})
    state.setdefault("llm", {})
    state["llm"] = {"provider": llm.provider, "model": llm.model}


def run_case(state: dict[str, Any], llm: Optional[LLM] = None, today: Optional[date] = None, rerun_mappings: bool = True) -> CaseResult:
    """Build facts, run mappings (LLM, cached) and rules (pure), then draft + chain. Mutates state['result']."""
    llm = llm or get_llm()
    docs = {d["id"]: Document(**d) for d in state["documents"]}
    stated = StatedFields(**state["stated"])
    abstain = AbstainFlags(**state["abstain"])
    verified = [_ex_from_json(docs, e) for e in state["extractions"]]
    facts = build_fact_table(verified, stated)
    if rerun_mappings or not state.get("mappings"):
        monet = stated.monetised == "yes" if stated.monetised in ("yes", "no") else None
        mappings = run_mappings(facts, monet, llm)
        state["mappings"] = [m.model_dump() for m in mappings]
    else:
        mappings = [MappingRun(**m) for m in state["mappings"]]
    out = run_rules(RulesInput(facts=facts, mappings=mappings, step=state["step"], stated=stated, abstain=abstain, today=today))
    draft = build_draft(out, stated, llm)
    claim_summary = build_claim_summary(out.facts, out.stage)
    chain = build_chain(out, draft, mappings, claim_summary)
    rejected = [RejectedFact(**r) for r in state["rejected"]]
    doc_summaries = []
    for d in docs.values():
        m = state["meta"].get(d.id, {})
        doc_summaries.append(DocumentSummary(id=d.id, filename=d.filename, doc_type=d.doc_type, lines=d.lines, sha256=d.sha256,
                                             extraction_failed=bool(m.get("extraction_failed")), extraction_error=m.get("error"),
                                             n_facts=sum(1 for e in state["extractions"] if e["doc_id"] == d.id)))
    result = CaseResult(
        case_id=state["case_id"], rules_version=out.rules_version, stage=out.stage, available_steps=out.available_steps,
        chosen_step=out.chosen_step, verdict=out.verdict, verdict_explanation=out.verdict_explanation, claim_summary=claim_summary,
        statement=out.statement, facts=out.facts, rejected_facts=rejected, rule_results=out.rule_results, routes=out.routes,
        gap_fixes=out.gap_fixes, draft=draft, chain=chain, deadlines=out.deadlines, mapping_runs=mappings, step_evidence=out.step_evidence,
        stated=stated, abstain_flags=abstain, documents=doc_summaries, notes_ignored=True,
        llm={**state.get("llm", {}), "cached_calls": llm.cache_hits, "live_calls": llm.calls},
    )
    state["result"] = result.model_dump()
    return result


def diff_results(before: Optional[dict[str, Any]], after: CaseResult, added_docs: list[Document]) -> CaseDiff:
    if before is None:
        return CaseDiff(verdict_before="none", verdict_after=after.verdict, added_documents=[d.filename for d in added_docs])
    bf = {f["key"]: f for f in before["facts"]}
    af = {f.key: f for f in after.facts}
    changed_facts = []
    added_ids = {d.id for d in added_docs}
    for k, f in af.items():
        old = bf.get(k)
        from_new = any(s.doc_id in added_ids for s in f.sources)
        if old is None or old["status"] != f.status or str(old.get("value")) != str(f.value):
            changed_facts.append({"key": k, "before": (old or {}).get("value"), "before_status": (old or {}).get("status"),
                                  "after": f.value, "after_status": f.status, "doc_filename": f.sources[0].doc_filename if f.sources else None,
                                  "from_added_document": from_new})
    for k in bf:
        if k not in af:
            changed_facts.append({"key": k, "before": bf[k].get("value"), "before_status": bf[k]["status"], "after": None, "after_status": "removed"})
    br = {r["rule_id"]: r for r in before["rule_results"]}
    changed_rules = []
    for r in after.rule_results:
        old = br.get(r.rule_id)
        if old and old["status"] != r.status:
            changed_rules.append({"rule_id": r.rule_id, "rule_name": r.rule_name, "before": old["status"], "after": r.status, "explanation": r.explanation})
    vb, va = before["verdict"], after.verdict
    parts = []
    priority = ["grant_statement", "governing_terms_clause", "content_id_administrator_name", "licence_version", "email_date", "publish_date", "monetised_on_publish"]
    key_fact = next((c for k in priority for c in changed_facts if c.get("from_added_document") and c["key"] == k), None)
    if key_fact:
        parts.append(f"fact {key_fact['key']} (from {key_fact['doc_filename']}" + (f", {af['email_date'].value}" if key_fact['key'] == 'grant_statement' and 'email_date' in af else "") + ")")
    if changed_rules:
        parts.append("flipped " + ", ".join(f"{c['rule_id']} from {c['before'].replace('_', ' ')} to {c['after']}" for c in changed_rules))
    summary = ("What changed: " + " ".join(parts) + (f" → verdict moved from {_v(vb)} to {_v(va)}." if vb != va else f"; verdict unchanged ({_v(va)}).")) if parts else \
        (f"Verdict moved from {_v(vb)} to {_v(va)}." if vb != va else "Nothing that the rules rely on changed.")
    return CaseDiff(verdict_before=vb, verdict_after=va, changed_facts=changed_facts, changed_rule_results=changed_rules,
                    added_documents=[d.filename for d in added_docs], summary=summary)


def _v(v: str) -> str:
    return {"evidence_ready": "Evidence ready", "evidence_gap": "Evidence gap", "needs_adviser": "Needs an adviser"}.get(v, v)
