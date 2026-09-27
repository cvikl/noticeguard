"""LLM extraction by tagging, plus the 3-run category-mapping stage.

The model highlights; it never types. One call per document returns the ORIGINAL document text with
inline XML-style tags around spans. The round-trip check (quote_match.verify_tagged) rejects the whole
output if any text changed; values and categorical labels are derived in code (facts.normalise_value).
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from .facts import FactTable
from .llm import LLM, get_llm
from .models import Document, Extraction, Fact, MappingAnswer, MappingRun, RejectedFact, Span
from .quote_match import ExtractionFailure, verify_tagged

log = logging.getLogger("noticeguard.extract")

MAPPING_RUNS = 3
MAPPING_TEMPERATURE = 0.7

# Tag sets per document type. Descriptions tell the model WHICH span to wrap; values are never typed.
NOTICE_TAGS = {
    "platform_name": "the name of the video platform that issued the notice",
    "platform_case_id": "the platform's case / reference ID for this claim",
    "claimant_name": "the name of the claimant",
    "matched_work_title": "the title of the matched work (title only, not the artist)",
    "matched_segment": "the matched time segment, e.g. 0:12–1:04",
    "video_id": "the platform's ID of the creator's video",
    "video_title": "the title of the creator's video",
    "channel_name": "the creator's channel name",
    "claim_date": "the date of this notice",
    "claim_effect": "the sentence stating what the platform did to the video (revenue directed to claimant / blocked / tracked / removed)",
    "notice_kind": "the ONE sentence that says what this notice is: that content was claimed, that a dispute was rejected/reinstated, that an appeal was rejected, that the video was removed, or that a strike was applied",
    "deadline_date": "a calendar date by which the CREATOR must act, only if the notice states one explicitly",
    "strike_count": "the strike count, e.g. '1 of 3', if stated",
    "strike_date": "the date the strike was applied, if stated",
    "claimant_contact": "the claimant's contact email or address, if stated",
}
RECEIPT_TAGS = {
    "purchase_date": "the order / purchase date",
    "order_id": "the order number",
    "purchased_work_title": "the title of the licensed work purchased (title only)",
    "licence_tier": "the licence tier purchased (e.g. Standard, Pro)",
    "licence_version_on_receipt": "the licence terms version shown on the receipt, if shown",
    "licensor_name": "the name of the licensor / seller",
    "buyer_name": "the buyer's name",
}
CERT_TAGS = {
    "licence_version": "the licence terms version this certificate is issued under",
    "licence_tier": "the licence tier",
    "licensed_work_title": "the title of the licensed work (title only)",
    "licensee_name": "the licensee's name",
    "licensor_name": "the licensor's name",
    "issue_date": "the issue date",
    "order_id": "the order reference, if shown",
    "permitted_use": "each clause that describes a permitted use (one tag per clause, wrap the clause text after its number; add clause=\"4.1\")",
    "excluded_use": "each clause that describes an excluded / not-permitted use or a restriction such as requiring another tier (one tag per clause; add clause=\"...\")",
    "governing_terms_clause": "the clause saying which version of the terms governs this licence (add clause=\"...\")",
}
TERMS_TAGS = {
    "terms_version": "the version of these terms",
    "effective_date": "the effective date of this version",
    "licensor_name": "the name of the licensor publishing the terms",
    "permitted_use": "each clause describing a permitted use for a licence tier (one tag per clause; add clause=\"4.1\")",
    "excluded_use": "each clause describing an excluded / not-permitted use or a restriction such as requiring another tier (one tag per clause; add clause=\"...\")",
    "governing_terms_clause": "the clause saying which version of the terms governs a licence (add clause=\"...\")",
    "administrator_clause": "the clause saying claims may be administered by a third-party rights administrator (add clause=\"...\")",
    "administrator_name": "the name of the rights administrator, only if the terms name one",
}
TRACK_TAGS = {
    "work_title": "the title of the track this page is about",
    "licensor_name": "the name of the licensor / rights owner",
    "content_id_administrator_name": "the name of the party that administers content matching / claims for this track",
}
EMAIL_TAGS = {
    "email_date": "the date the email was sent (the Date header)",
    "sender_address": "the sender's email address",
    "grant_statement": "the sentence in which the licensor grants, confirms or extends permission",
    "granted_work_title": "the title of the work the permission refers to (title only)",
    "granted_use_scope": "the words describing the scope of the permission (e.g. monetised videos on your channel)",
    "granted_channel": "the channel or video the permission names, if any",
    "ticket_ref": "the support ticket reference, if any",
}
VIDEO_TAGS = {
    "video_id": "the platform ID of the video",
    "video_title": "the video title",
    "publish_date": "the publish date",
    "monetised_on_publish": "the line stating whether monetisation was on or off at publish",
    "monetisation_start_date": "the date monetisation started, if stated",
    "channel_name": "the channel name",
    "platform_name": "the platform name",
    "duration": "the video duration",
}
OTHER_TAGS = {**NOTICE_TAGS, **RECEIPT_TAGS, **CERT_TAGS, **EMAIL_TAGS}

TAGS_BY_DOC = {
    "claim_notice": NOTICE_TAGS, "dispute_response": NOTICE_TAGS, "appeal_response": NOTICE_TAGS,
    "removal_notice": NOTICE_TAGS, "strike_notice": NOTICE_TAGS,
    "receipt": RECEIPT_TAGS, "licence_certificate": CERT_TAGS, "licensor_terms": TERMS_TAGS,
    "track_page": TRACK_TAGS, "licensor_email": EMAIL_TAGS, "video_metadata": VIDEO_TAGS, "other": OTHER_TAGS,
}

EXTRACTION_SYSTEM = (
    "You highlight spans in a document by wrapping them in tags. You never change, summarise, translate or add text, "
    "and you never type values yourself. You output only the tagged document."
)

EXTRACTION_PROMPT = """Return this document exactly as given, with tags around the spans listed below. Do not change, omit, reorder or add any text. Do not paraphrase. Do not fix typos. If a field is not present, do not tag it. Never nest one tag inside another. Output only the tagged document (no preamble, no code fence, no commentary).

Document type: {doc_type}

Tags to use (wrap the span that IS the value; keep the label text outside the tag):
{tag_list}

Worked example 1 (a receipt):
--- input ---
Order date: 19 August 2025
Order ID: GA-2025-08231
Item: Glasslight — Standard licence
--- output ---
Order date: <purchase_date>19 August 2025</purchase_date>
Order ID: <order_id>GA-2025-08231</order_id>
Item: <purchased_work_title>Glasslight</purchased_work_title> — <licence_tier>Standard</licence_tier> licence

Worked example 2 (a licence document with numbered clauses; one tag per clause, clause number as an attribute):
--- input ---
4. Uses
4.1 The licence permits use of the Work in podcasts.
4.2 The licence does not permit use in advertising.
9.1 This licence is governed by the terms in force on the date of purchase.
--- output ---
4. Uses
4.1 <permitted_use clause="4.1">The licence permits use of the Work in podcasts.</permitted_use>
4.2 <excluded_use clause="4.2">The licence does not permit use in advertising.</excluded_use>
9.1 <governing_terms_clause clause="9.1">This licence is governed by the terms in force on the date of purchase.</governing_terms_clause>

Now tag the following document."""

RETRY_SUFFIX = """

Your previous output changed the document text, so it was rejected. You changed the text here (unified diff, "-" is the original, "+" is what you returned):
{diff}

Return the document again, character for character as given, with tags only. Do not fix, reword or drop anything."""


def _tag_list(doc_type: str) -> str:
    tags = TAGS_BY_DOC.get(doc_type, OTHER_TAGS)
    return "\n".join(f"- <{k}>: {v}" for k, v in tags.items())


def extraction_prompt(doc: Document, diff: Optional[str] = None) -> str:
    p = EXTRACTION_PROMPT.format(doc_type=doc.doc_type, tag_list=_tag_list(doc.doc_type))
    if diff:
        p += RETRY_SUFFIX.format(diff=diff)
    return p


def _rej(doc: Document, tag: str, text: str, reason: str, kind: str = "dropped_tag") -> RejectedFact:
    return RejectedFact(doc_id=doc.id, doc_filename=doc.filename, type=tag, value=text, quote=text, reason=reason, kind=kind)


def extract_document(doc: Document, llm: Optional[LLM] = None) -> tuple[list[tuple[Document, Extraction, Span]], list[RejectedFact], dict]:
    """Tag one document, round-trip check it (one retry with the diff shown), and return located spans.

    Returns (verified, rejected, meta). meta['extraction_failed'] is True when both attempts changed the text;
    in that case no facts are produced for the document and the failure is surfaced in rejected."""
    llm = llm or get_llm()
    allowed = set(TAGS_BY_DOC.get(doc.doc_type, OTHER_TAGS).keys())
    rejected: list[RejectedFact] = []
    meta: dict[str, Any] = {"provider": llm.provider, "model": llm.model, "attempts": 0, "extraction_failed": False}
    diff: Optional[str] = None
    last_err: Optional[ExtractionFailure] = None
    for attempt in range(2):
        meta["attempts"] = attempt + 1
        resp = llm.complete(extraction_prompt(doc, diff), docs=doc.text, system=EXTRACTION_SYSTEM, temperature=0.0, max_tokens=16000)
        meta["cached"] = resp.cached
        try:
            result = verify_tagged(doc, resp.text, allowed_tags=allowed)
        except ExtractionFailure as e:
            last_err = e
            diff = e.diff or e.reason
            log.info("round-trip failed for %s (attempt %d): %s", doc.filename, attempt + 1, e.reason)
            continue
        for tag, text, reason in result.dropped:
            rejected.append(_rej(doc, tag, text, reason))
        meta.update(n_verified=len(result.spans), n_dropped=len(result.dropped))
        return result.spans, rejected, meta
    meta["extraction_failed"] = True
    meta["error"] = f"{last_err.reason}" if last_err else "unknown"
    meta["diff"] = last_err.diff if last_err else ""
    rejected.append(_rej(doc, "*", "", f"whole extraction rejected after 2 attempts: {meta['error']}. {meta['diff'][:600]}", kind="extraction_failed"))
    return [], rejected, meta


def extract_documents(docs: list[Document], llm: Optional[LLM] = None, workers: int = 4):
    llm = llm or get_llm()
    verified_all: list[tuple[Document, Extraction, Span]] = []
    rejected_all: list[RejectedFact] = []
    meta: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda d: extract_document(d, llm), docs))
    for doc, (v, r, m) in zip(docs, results):
        verified_all.extend(v)
        rejected_all.extend(r)
        meta[doc.id] = m
    return verified_all, rejected_all, meta


# ----------------------------------------------------------------------------- mapping stage
MAPPING_SYSTEM = "You answer one narrow interpretation question about a licence clause. Output JSON only."

MAPPING_PROMPTS = {
    "permitted_use_covers_actual_use": """Given this clause from a music licence document (quoted verbatim):

"{clause}"

and this actual use of the music by the licence holder:
{actual_use}

Question: does the clause, on its own wording, cover (permit) this actual use for a holder of the stated licence tier?
Answer "yes" only if the clause's wording clearly permits this use for that tier. Answer "no" if the clause clearly does not permit it for that tier (for example it permits a different tier, or only non-commercial use when the actual use is monetised). Answer "unclear" if the wording could reasonably be read either way.

Output JSON only: {{"covers": "yes" | "no" | "unclear", "reason": "<one sentence>"}}""",
    "excluded_use_applies_to_actual_use": """Given this restriction / exclusion clause from a music licence document (quoted verbatim):

"{clause}"

and this actual use of the music by the licence holder:
{actual_use}

Question: does this clause, on its own wording, exclude or forbid this actual use for a holder of the stated licence tier?
Answer "yes" only if the clause clearly applies to and excludes this use for that tier. Answer "no" if the clause is about something else or clearly does not restrict this use for that tier. Answer "unclear" if the wording could reasonably be read either way.

Output JSON only: {{"covers": "yes" | "no" | "unclear", "reason": "<one sentence>"}}""",
    "grant_covers_actual_use": """Given this statement from an email sent by the music licensor (quoted verbatim):

"{clause}"

and this actual use of the music by the licence holder:
{actual_use}

Question: does the statement, on its own wording, grant or confirm permission that covers this actual use?
Answer "yes" only if it clearly does. Answer "no" if it clearly does not (different work, different channel, or explicitly excludes this use). Answer "unclear" if it could reasonably be read either way.

Output JSON only: {{"covers": "yes" | "no" | "unclear", "reason": "<one sentence>"}}""",
    "governing_terms_selects_purchase_version": """Given this clause from a licence document (quoted verbatim):

"{clause}"

Question: does this clause say that the version of the terms in force at the time of purchase (or issue) governs the licence, so that later changes to the terms do not reduce the rights already granted?
Answer "yes" only if the wording clearly says the purchase-time (or issue-time) version governs. Answer "no" if it clearly says the current or latest terms apply. Answer "unclear" otherwise.

Output JSON only: {{"covers": "yes" | "no" | "unclear", "reason": "<one sentence>"}}""",
}


def describe_actual_use(actual_use: dict[str, Any]) -> str:
    monet = actual_use.get("monetised")
    lines = [
        f"- medium: background music in a video",
        f"- platform: {actual_use.get('platform') or 'a video platform'}",
        f"- channel: {actual_use.get('channel') or 'the licence holder’s own channel'}",
        f"- monetised: {'yes (ads on, the creator earns revenue)' if monet is True else 'no' if monet is False else 'unknown'}",
        f"- licence tier held: {actual_use.get('licence_tier') or 'unknown'}",
        f"- work: {actual_use.get('work_title') or 'the licensed work'}",
    ]
    return "\n".join(lines)


def _ask_mapping(llm: LLM, question: str, clause: str, actual_use: dict[str, Any], run: int) -> MappingAnswer:
    prompt = MAPPING_PROMPTS[question].format(clause=clause, actual_use=describe_actual_use(actual_use))
    try:
        raw, resp = llm.complete_json(prompt, system=MAPPING_SYSTEM, temperature=MAPPING_TEMPERATURE, run=run, max_tokens=512)
        covers = str(raw.get("covers", "unclear")).strip().lower() if isinstance(raw, dict) else "unclear"
        if covers not in ("yes", "no", "unclear"):
            covers = "unclear"
        return MappingAnswer(covers=covers, reason=str(raw.get("reason", "")) if isinstance(raw, dict) else "", raw=resp.text[:500])
    except Exception as e:  # any failure counts as unclear -> ambiguous -> needs_adviser
        return MappingAnswer(covers="unclear", reason=f"mapping call failed: {e}", raw=None)


def _agree(answers: list[MappingAnswer]) -> str:
    votes = {a.covers for a in answers}
    if votes == {"yes"}:
        return "yes"
    if votes == {"no"}:
        return "no"
    return "ambiguous"


def build_actual_use(table: FactTable, stated_monetised: Optional[bool]) -> dict[str, Any]:
    monet = table.value("monetised_on_publish")
    if not isinstance(monet, bool):
        monet = stated_monetised
    return {
        "monetised": monet,
        "platform": table.value("platform_name") or "the platform named in the claim notice",
        "channel": table.value("channel_name") or table.value("stated_channel_name") or "the creator's own channel",
        "licence_tier": table.value("licence_tier") or "unknown",
        "work_title": table.value("licensed_work_title") or table.value("purchased_work_title") or table.value("matched_work_title"),
        "medium": "video",
    }


def run_mappings(facts: list[Fact], stated_monetised: Optional[bool], llm: Optional[LLM] = None, workers: int = 4) -> list[MappingRun]:
    """Run every mapping question that the rules could need, 3 runs each, and record agreement."""
    llm = llm or get_llm()
    table = FactTable(facts)
    actual_use = build_actual_use(table, stated_monetised)
    jobs: list[tuple[str, Fact]] = []
    for f in table.starting_with("permitted_use["):
        jobs.append(("permitted_use_covers_actual_use", f))
    for f in table.starting_with("excluded_use["):
        jobs.append(("excluded_use_applies_to_actual_use", f))
    for f in table.all("grant_statement"):
        jobs.append(("grant_covers_actual_use", f))
    for f in table.all("governing_terms_clause"):
        jobs.append(("governing_terms_selects_purchase_version", f))
    # governing clauses may live on several documents (cert + terms): map each source separately
    expanded: list[tuple[str, Fact, Any]] = []
    for q, f in jobs:
        for src in f.sources:
            expanded.append((q, f, src))

    def work(item):
        q, f, src = item
        au = actual_use if q != "governing_terms_selects_purchase_version" else {}
        answers = [_ask_mapping(llm, q, src.quote, au, run) for run in range(MAPPING_RUNS)]
        return MappingRun(id=f"map:{q}:{f.key}@{src.doc_id}", question=q, fact_key=f.key, clause_quote=src.quote,
                          actual_use=au, answers=answers, result=_agree(answers), doc_id=src.doc_id,
                          doc_filename=src.doc_filename, clause_ref=src.clause_ref)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        runs = list(ex.map(work, expanded))
    return runs
