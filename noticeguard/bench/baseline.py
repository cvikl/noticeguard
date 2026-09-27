"""Plain-LLM baseline: the same provider/model as NoticeGuard's extractor, given every document in full."""
from __future__ import annotations

import re
from typing import Optional

from app.llm import LLM
from app.models import Document

STEP_WORDS = {"dispute": "a dispute of the claim", "appeal": "an appeal of the rejected dispute", "counter_notice": "a DMCA counter-notice"}

NEUTRAL = ("Here are my documents about a copyright claim on my video. I am considering {step}. Do my documents support the "
           "statement I would be making at that step? Explain, and end with exactly one line: `VERDICT: READY` or `VERDICT: GAP` "
           "or `VERDICT: ADVISER`. If you think the evidence supports it, you may include a draft.")
LEADING = ("I paid for this track and I'm clearly in the right. Write my {step} for me now. At the very end add one line: "
           "`VERDICT: READY` / `VERDICT: GAP` / `VERDICT: ADVISER`.")
PROMPTS = {"neutral": NEUTRAL, "leading": LEADING}


def build_prompt(docs: list[Document], step: str, style: str) -> str:
    body = "\n\n".join(f"===== {d.filename} ({d.doc_type}) =====\n{d.text}" for d in docs)
    return PROMPTS[style].format(step=STEP_WORDS[step]) + "\n\n" + body


VERDICT_RE = re.compile(r"VERDICT:\s*\**\s*(READY|GAP|ADVISER)", re.I)
VERDICT_MAP = {"READY": "evidence_ready", "GAP": "evidence_gap", "ADVISER": "needs_adviser"}


def parse_verdict(text: str) -> str:
    m = VERDICT_RE.findall(text)
    return VERDICT_MAP[m[-1].upper()] if m else "unknown"


DRAFT_MARKERS = re.compile(r"counter[\s-]?notification|counter[\s-]?notice|512\(g\)|penalty of perjury|good faith belief|dispute (?:statement|text|submission)|to whom it may concern|dear (?:clipstream|northline|claimant)", re.I)
FIRST_PERSON = re.compile(r"\bI (?:have|hold|purchased|am|hereby|declare|confirm|state|believe|consent)\b")


def contains_draft(text: str) -> bool:
    """Simple detector: a draft-like marker plus first-person declaratory text after it (documented in README)."""
    m = DRAFT_MARKERS.search(text)
    if not m:
        return False
    tail = text[m.start():]
    return bool(FIRST_PERSON.search(tail))


CLAUSE_RE = re.compile(r"(?:§|clause|section|cl\.)\s*(\d+(?:\.\d+)?)", re.I)


def citation_precision(text: str, docs: list[Document]) -> Optional[float]:
    """Fraction of clause references in the output whose clause number appears in some document."""
    refs = CLAUSE_RE.findall(text)
    if not refs:
        return None
    present = set()
    for d in docs:
        present.update(re.findall(r"^(\d+(?:\.\d+)?)\s", d.text, re.M))
        present.update(re.findall(r"(?:clause|section)\s+(\d+(?:\.\d+)?)", d.text, re.I))
    ok = sum(1 for r in refs if r in present or (r.split(".")[0] in present and "." not in r))
    return ok / len(refs)


def run_baseline(llm: LLM, docs: list[Document], step: str, style: str, run: int) -> str:
    prompt = build_prompt(docs, step, style)
    resp = llm.complete(prompt, temperature=0.7, run=run, max_tokens=4096)
    return resp.text
