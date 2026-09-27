"""Document -> Quote -> Fact -> Rule -> Status chain for every clickable sentence, plus the claim summary."""
from __future__ import annotations

from typing import Any, Optional

from .facts import FactTable, parse_date
from .models import ChainFact, ChainNode, Draft, Fact, MappingRun, RuleResult
from .rules.engine import RULE_LOGIC_TEXT, RulesOutput


def chain_facts(table: FactTable, keys: list[str]) -> list[ChainFact]:
    out: list[ChainFact] = []
    seen: set[str] = set()
    for k in keys:
        for f in table.all(k) if not k.endswith("[") else table.starting_with(k):
            ident = f"{f.key}|{f.status}|{f.value}"
            if ident in seen:
                continue
            seen.add(ident)
            out.extend(fact_to_chain(f))
    return out


def fact_to_chain(f: Fact) -> list[ChainFact]:
    if not f.sources:
        return [ChainFact(fact_key=f.key, value=f.value, status=f.status)]
    return [ChainFact(fact_key=f.key, value=f.value, status=f.status, quote=s.quote, doc_id=s.doc_id, doc_filename=s.doc_filename,
                      line_start=s.line_start, line_end=s.line_end, char_start=s.char_start, char_end=s.char_end,
                      clause_ref=s.clause_ref, context=s.context, doc_type=s.doc_type) for s in f.sources]


def _rule_map(rules: list[RuleResult]) -> dict[str, RuleResult]:
    return {r.rule_id: r for r in rules}


def build_chain(out: RulesOutput, draft: Optional[Draft], mappings: list[MappingRun], claim_summary: list[dict[str, Any]]) -> dict[str, ChainNode]:
    table = FactTable(out.facts)
    rmap = _rule_map(out.rule_results)
    mmap = {m.id: m for m in mappings}
    chain: dict[str, ChainNode] = {}

    def node(sid: str, text: str, rule_ids: list[str], fact_keys: list[str], status: Optional[str] = None) -> ChainNode:
        primary = rmap.get(rule_ids[0]) if rule_ids else None
        mids = [mid for rid in rule_ids if rid in rmap for mid in rmap[rid].mapping_ids]
        keys = list(fact_keys)
        for rid in rule_ids:
            if rid in rmap:
                keys += rmap[rid].facts_used
        n = ChainNode(sentence_id=sid, text=text, rule_id=primary.rule_id if primary else None, rule_name=primary.rule_name if primary else None,
                      rule_status=primary.status if primary else None, rule_logic=RULE_LOGIC_TEXT.get(primary.rule_id) if primary else None,
                      facts=chain_facts(table, list(dict.fromkeys(keys))), mapping_runs=[mmap[m] for m in dict.fromkeys(mids) if m in mmap],
                      status=status)
        chain[sid] = n
        return n

    node("verdict", out.verdict_explanation, ["R8", "R10", "R7"], [], out.verdict)
    for s in claim_summary:
        node(s["id"], s["text"], ["R0"], s.get("fact_keys", []), out.stage)
    for comp in out.statement.components:
        node(comp.sentence_id, comp.label + " — " + comp.explanation, comp.rule_ids, comp.fact_keys, comp.status)
    for r in out.rule_results:
        node(f"rule:{r.rule_id}", r.explanation, [r.rule_id], r.facts_used, r.status)
    for rt in out.routes:
        node(rt.sentence_id, f"{rt.title}. {rt.description}", ["R9", "R5"], ["content_id_administrator_name", "administrator_name", "claimant_name", "licensor_name"], rt.evidence_status)
    for g in out.gap_fixes:
        comp = next((c for c in out.statement.components if c.id == g.component), None)
        node(g.sentence_id, g.needed + " " + g.how_to_get, comp.rule_ids if comp else [], comp.fact_keys if comp else [], "evidence_gap")
    for d in out.deadlines:
        node(d.sentence_id, f"{d.label}: {d.date}", ["R0"], ["deadline_date"], None)
    if draft:
        for s in draft.sentences:
            node(s.id, s.text, s.rule_ids, s.fact_keys, "confirmed_by_document")
    for f in out.facts:
        sid = f"fact:{f.key}"
        if sid not in chain:
            rids = [r.rule_id for r in out.rule_results if f.key in r.facts_used][:1]
            chain[sid] = ChainNode(sentence_id=sid, text=f"{f.key}: {f.value}", rule_id=rids[0] if rids else None,
                                   rule_name=rmap[rids[0]].rule_name if rids else None, rule_status=rmap[rids[0]].status if rids else None,
                                   rule_logic=RULE_LOGIC_TEXT.get(rids[0]) if rids else None, facts=fact_to_chain(f),
                                   mapping_runs=[m for m in mappings if m.fact_key == f.key], status=f.status)
    return chain


def _fmt(iso: Any) -> str:
    d = parse_date(iso)
    return d.strftime("%-d %B %Y") if d else str(iso)


EFFECT_WORDS = {"monetised_to_claimant": "ad revenue from the video is being directed to the claimant",
                "blocked": "the video was blocked", "tracked": "the video is being tracked", "removed": "the video was removed"}


def build_claim_summary(facts: list[Fact], stage: str) -> list[dict[str, Any]]:
    t = FactTable(facts)
    out: list[dict[str, Any]] = []
    n = 0

    def add(text: str, keys: list[str]):
        nonlocal n
        n += 1
        out.append({"id": f"claim:{n}", "text": text, "fact_keys": keys})

    claimant = t.value("claimant_name")
    work = t.value("matched_work_title")
    title = t.value("video_title")
    vid = t.value("video_id")
    platform = t.value("platform_name") or "the platform"
    if not claimant and not work:
        add("No claim notice was found among the documents.", ["notice_kind"])
        return out
    # first claim notice date = earliest claim_date on a 'claim' notice
    notices = []
    for k in t.all("notice_kind"):
        if k.status != "confirmed_by_document" or not k.sources:
            continue
        doc_id = k.sources[0].doc_id
        d = next((cd.value for cd in t.all("claim_date") if cd.sources and cd.sources[0].doc_id == doc_id), None)
        eff = next((ce.value for ce in t.all("claim_effect") if ce.sources and ce.sources[0].doc_id == doc_id), None)
        notices.append((parse_date(d) or parse_date("1900-01-01"), k.value, d, eff, doc_id))
    notices.sort(key=lambda x: x[0])
    first = next((x for x in notices if x[1] == "claim"), notices[0] if notices else None)
    when = f" on {_fmt(first[2])}" if first and first[2] else ""
    add(f"{claimant or 'A claimant'} claimed “{work or 'a work'}” in your video" + (f" “{title}”" if title else "") + (f" ({vid})" if vid else "") + f" on {platform}{when}.",
        ["claimant_name", "matched_work_title", "video_title", "video_id", "platform_name", "claim_date"])
    seg = t.value("matched_segment")
    if seg:
        add(f"The matched segment is {seg}.", ["matched_segment"])
    if first and first[3]:
        add(f"The platform's action: {EFFECT_WORDS.get(first[3], first[3])}.", ["claim_effect"])
    for x in notices:
        if x[1] == "dispute_rejected":
            add(f"On {_fmt(x[2])} the claimant rejected your dispute and reinstated its claim." if x[2] else "The claimant rejected your dispute and reinstated its claim.", ["notice_kind", "claim_date"])
        elif x[1] in ("removal", "appeal_rejected", "strike"):
            sc = t.value("strike_count")
            add((f"On {_fmt(x[2])} " if x[2] else "") + "the claimant submitted a copyright removal request; the video was removed and the channel received a copyright strike" + (f" ({sc} of 3)" if sc else "") + ".",
                ["notice_kind", "claim_date", "strike_count", "strike_date"])
    return out
