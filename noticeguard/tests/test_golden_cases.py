"""Golden tests: full pipeline on Maya, Leo and Leo + email from the committed LLM cache (no network)."""
from __future__ import annotations

import os
from datetime import date

import pytest

from app.ingest import load_folder
from app.llm import LLM
from app.main import DATA, DEMO_SETS
from app.models import AbstainFlags
from app.pipeline import diff_results, new_state, run_case, run_extraction


class OfflineLLM(LLM):
    """Cache-only: any uncached call is a test failure, never a network call."""

    def _call(self, *a, **k):  # pragma: no cover
        raise AssertionError("golden tests must run entirely from cache/llm; an uncached LLM call was attempted")


@pytest.fixture(scope="module", params=[("gemini", "gemini-3.8-flash"), ("claude_cli", "sonnet")], ids=["gemini", "historical-claude"])
def llm(request):
    provider, model = request.param
    return OfflineLLM(provider=provider, model=model, use_cache=True)


def _run(name: str, llm: LLM, extra_folder: str | None = None):
    spec = DEMO_SETS[name]
    folders = ["maya"] if name == "maya" and llm.provider == "claude_cli" else spec["folders"]
    docs = [d for f in folders for d in load_folder(DATA / f)]
    state = new_state(docs, spec["step"], spec["stated"], AbstainFlags(), "I paid for this, I'm obviously right, just write it")
    run_extraction(state, llm=llm)
    result = run_case(state, llm=llm, today=date(2026, 9, 27))
    return state, result


def _rule(res, rid):
    return next(r for r in res.rule_results if r.rule_id == rid)


def test_maya_ready_for_dispute(llm):
    _, res = _run("maya", llm)
    assert res.verdict == "evidence_ready" and res.stage == "claim" and res.chosen_step == "dispute"
    r2 = _rule(res, "R2")
    assert r2.status == "pass" and r2.data["version_in_force"] == "v2"
    # cites both the certificate and terms v3 §9.1 governing clauses
    assert "clause 9.1" in r2.explanation and "certificate" in r2.explanation
    assert "governing_terms_clause" in r2.facts_used
    r3 = _rule(res, "R3")
    assert r3.status == "pass" and r3.data["covered_by"] == "permitted_use[cert:4.1]" and "clause 4.1" in r3.explanation
    r5 = _rule(res, "R5")
    assert r5.status == "pass" and "administered by Northline Rights on behalf of Glasswork Audio" in r5.explanation
    assert [c.status for c in res.statement.components] == ["supported"] * 3
    assert res.routes[0].title.lower().startswith("ask glasswork") and res.routes[1].step == "dispute" and res.routes[1].evidence_status == "evidence_ready"
    se = {s.step: s for s in res.step_evidence}
    assert se["counter_notice"].evidence_status == "evidence_ready" and not se["counter_notice"].available
    assert res.draft is not None and res.draft.post_check.passed and res.draft.withheld_reason is None
    assert any("[cert v2 §4.1]" in s.text for s in res.draft.sentences)
    assert any("[terms v3 §9.1]" in s.text for s in res.draft.sentences)
    assert not res.rejected_facts or all(r.kind == "dropped_tag" for r in res.rejected_facts)


def test_leo_gap_then_ready_with_email(llm):
    state, res = _run("leo", llm)
    assert res.verdict == "evidence_gap" and res.stage == "removed_with_strike"
    assert _rule(res, "R3").status == "fail" and _rule(res, "R4").status == "not_applicable"
    assert any(g.component == "CN2a" and "on or before 10 September 2025" in g.needed for g in res.gap_fixes)
    assert res.draft is None
    before = state["result"]
    email = load_folder(DATA / "leo_email")
    for d in email:
        state["documents"].append(d.model_dump())
    run_extraction(state, only_doc_ids=[d.id for d in email], llm=llm)
    res2 = run_case(state, llm=llm, today=date(2026, 9, 27))
    assert res2.verdict == "evidence_ready"
    r4 = _rule(res2, "R4")
    assert r4.status == "pass" and "2 September 2025" in r4.explanation
    diff = diff_results(before, res2, email)
    assert diff.verdict_before == "evidence_gap" and diff.verdict_after == "evidence_ready"
    assert any(c["rule_id"] == "R4" and c["after"] == "pass" for c in diff.changed_rule_results)
    assert "09_licensor_support_email.eml" in diff.summary and "R4" in diff.summary
    assert res2.routes[0].title.startswith("Send your evidence to Northline Rights") and res2.routes[0].evidence_status == "evidence_ready"
    assert res2.draft is not None and res2.draft.post_check.passed
    assert any("[email 2025-09-02]" in s.text for s in res2.draft.sentences)


def test_every_draft_sentence_has_a_verified_quote(llm):
    for name in ("maya",):
        _, res = _run(name, llm)
        for s in res.draft.sentences:
            node = res.chain[s.id]
            assert any(f.quote and f.doc_id for f in node.facts), f"{name} {s.id} has no chain fact with a quote"
    state, _ = _run("leo", llm)
    email = load_folder(DATA / "leo_email")
    for d in email:
        state["documents"].append(d.model_dump())
    run_extraction(state, only_doc_ids=[d.id for d in email], llm=llm)
    res2 = run_case(state, llm=llm, today=date(2026, 9, 27))
    for s in res2.draft.sentences:
        node = res2.chain[s.id]
        if "[stated by you]" in s.text or s.text.startswith(("4.", "5.")):
            continue  # CN3/CN4/CN5 come from the form and acknowledgements, not documents
        assert any(f.quote and f.doc_id for f in node.facts), f"leo+email {s.id} has no chain fact with a quote"


def test_notes_do_not_reach_rules(llm):
    _, a = _run("leo", llm)
    spec = DEMO_SETS["leo"]
    folders = spec["folders"]
    docs = [d for f in folders for d in load_folder(DATA / f)]
    state = new_state(docs, spec["step"], spec["stated"], AbstainFlags(), "")
    run_extraction(state, llm=llm)
    b = run_case(state, llm=llm, today=date(2026, 9, 27))
    assert a.verdict == b.verdict == "evidence_gap"
    assert [r.status for r in a.rule_results] == [r.status for r in b.rule_results]


def test_chain_quote_positions_match_documents(llm):
    _, res = _run("maya", llm)
    docs = {d.id: d for d in res.documents}
    for node in res.chain.values():
        for f in node.facts:
            if f.doc_id and f.quote:
                text = "\n".join(docs[f.doc_id].lines)
                assert text[f.char_start:f.char_end] == f.quote


def test_bernard_v3_blocks_monetised_dispute():
    llm = OfflineLLM(provider="gemini", model="gemini-3.8-flash", use_cache=True)
    _, res = _run("maya-v3", llm)
    assert res.verdict == "evidence_gap" and res.draft is None
    assert _rule(res, "R2").data["version_in_force"] == "v3"
    assert _rule(res, "R3").status == "fail"
    assert any(c.status == "not_supported" and "R3" in c.rule_ids for c in res.statement.components)
    assert any(s.clause_ref == "4.1" and "non-monetised video" in s.quote
               for f in res.facts if f.key.startswith("permitted_use") for s in f.sources)
