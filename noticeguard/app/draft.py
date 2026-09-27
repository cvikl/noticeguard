"""Draft generator (template-only by default) with a post-check that rejects any unsupported detail.

A draft is produced only when the verdict is evidence_ready. Every slot is filled from the confirmed fact table or
the stated-by-you fields, and every sentence ends with a citation marker such as [cert v2 §4.1].
"""
from __future__ import annotations

import os
import re
from typing import Any, Optional

from .facts import FactTable, parse_date
from .models import Draft, DraftSentence, PostCheck, StatedFields
from .rules.engine import CN_STATEMENT, RulesOutput

HEADER = ("DRAFT — prepared for your review. NoticeGuard has checked that your documents support the factual statements "
          "below. It has not verified their authenticity and is not legal advice.")

# words that appear in the templates themselves (never treated as unsupported proper nouns)
TEMPLATE_WORDS = set("""
I The This On Your Licence Certificate Terms Standard Pro Clause Please Counter Notice Statement Identification Name Address
Telephone Signature Consent Federal District Court United States DRAFT NoticeGuard It Material Removed Video Case Matched Work
Segment Published Under Order Sworn Jurisdiction Service Process Draft Creator Physical Electronic Good Faith Ad
""".split())


def _fmt(iso: Any) -> str:
    d = parse_date(iso)
    return d.strftime("%-d %B %Y") if d else str(iso)


def _short(q: str, n: int = 160) -> str:
    q = re.sub(r"\s+", " ", q).strip().rstrip(".")
    if len(q) <= n:
        return q
    cut = q[: n - 1]
    cut = cut[: cut.rfind(" ")] if " " in cut else cut
    return cut.rstrip(",;:") + "…"


def _clause_cite(t: FactTable, key: str, label: str, version: Optional[str]) -> str:
    f = t.get(key)
    ref = f.sources[0].clause_ref if f and f.sources and f.sources[0].clause_ref else None
    v = f" {version}" if version else ""
    return f"[{label}{v}{' §' + ref if ref else ''}]"


def build_draft(out: RulesOutput, stated: StatedFields, llm: Any = None) -> Optional[Draft]:
    if out.verdict != "evidence_ready":
        return None
    t = FactTable(out.facts)
    rr = {r.rule_id: r for r in out.rule_results}
    sentences: list[DraftSentence] = []

    def add(text: str, cites: list[str], keys: list[str], rules: list[str]):
        sid = f"draft:{len(sentences) + 1}"
        sentences.append(DraftSentence(id=sid, text=f"{text} {' '.join(cites)}".strip(), citations=cites, fact_keys=keys, rule_ids=rules))

    work = t.value("licensed_work_title") or t.value("matched_work_title")
    tier = t.value("licence_tier")
    licensor = t.value("licensor_name")
    purchase = t.value("purchase_date") or t.value("issue_date")
    order = t.value("order_id")
    version = rr["R2"].data.get("version_in_force")
    current_v = rr["R2"].data.get("current_version")
    claimant = t.value("claimant_name")
    publish = t.value("publish_date")
    case_id = t.value("platform_case_id")
    platform = t.value("platform_name") or "the platform"
    r3, r4 = rr["R3"], rr["R4"]
    covered_key = r3.data.get("covered_by")
    covered = t.get(covered_key) if covered_key else None
    receipt_cite = f"[receipt #{order}]" if order else "[receipt]"
    cert_cite = _clause_cite(t, covered_key, "cert", version) if covered else f"[cert {version}]" if version else "[cert]"
    gov_terms = [f for f in t.all("governing_terms_clause") if f.sources and f.sources[0].doc_type == "licensor_terms"]
    gov_cert = [f for f in t.all("governing_terms_clause") if f.sources and f.sources[0].doc_type == "licence_certificate"]
    gov = (gov_terms or gov_cert or [None])[0]
    gov_cite = f"[terms {current_v} §{gov.sources[0].clause_ref}]" if gov and gov.sources[0].doc_type == "licensor_terms" and gov.sources[0].clause_ref else (
        f"[cert {version} §{gov.sources[0].clause_ref}]" if gov and gov.sources[0].clause_ref else "[terms]")
    grant = t.get("grant_statement")
    email_date = t.value("email_date")
    email_cite = f"[email {email_date}]" if email_date else "[email]"
    admin_key = "content_id_administrator_name" if t.has("content_id_administrator_name") else "administrator_name"
    track_cite = "[track page]" if t.has("content_id_administrator_name") else "[terms]"

    kind = out.chosen_step
    if kind in ("dispute", "appeal"):
        add(f"I hold a valid licence for the sound recording “{work}” and this claim conflicts with that licence.", [cert_cite], ["licensed_work_title", "licence_version"], ["R1", "R3"])
        add(f"I purchased a {tier} licence for “{work}” from {licensor} on {_fmt(purchase)}" + (f", order {order}" if order else "") + ".", [receipt_cite],
            ["licence_tier", "purchased_work_title", "licensor_name", "purchase_date", "order_id"], ["R2"])
        if covered is not None:
            add(f"The Licence Certificate issued with that purchase is under Licence Terms {version}; clause {covered.sources[0].clause_ref or ''} permits “{_short(covered.quote)}”.".replace("clause  ", "clause "),
                [cert_cite], ["licence_version", covered_key], ["R2", "R3"])
        if current_v and version and current_v != version and gov is not None:
            add(f"The current terms ({current_v}) do not reduce this: clause {gov.sources[0].clause_ref or ''} states “{_short(gov.quote)}”.".replace("clause  ", "clause "),
                [gov_cite], ["terms_version", "governing_terms_clause"], ["R2"])
        if r4.status == "pass" and grant is not None:
            add(f"On {_fmt(email_date)} {licensor} confirmed in writing: “{_short(grant.quote)}”.", [email_cite], ["email_date", "grant_statement"], ["R4"])
        if publish:
            add(f"The video was published on {_fmt(publish)}, while the licence was in force.", ["[video export]"], ["publish_date", "monetised_on_publish"], ["R2"])
        if rr["R5"].status == "pass" and t.has(admin_key):
            add(f"{licensor}'s own track page states that {claimant} administers content matching for this track on its behalf, so this is a licensed use inside the licence chain; I ask that the claim be released.",
                [track_cite], ["claimant_name", admin_key, "licensor_name"], ["R5"])
        else:
            add("I ask that the claim be released.", [], [], ["R5"])
    else:
        vid, title, seg = t.value("video_id"), t.value("video_title"), t.value("matched_segment")
        removal = next((cd.value for cd in t.all("claim_date") if cd.sources and cd.sources[0].doc_type in ("removal_notice", "appeal_response")), None)
        add(f"1. Identification of the material removed: the video “{title}” ({vid}) on {platform}" + (f", case {case_id}" if case_id else "") +
            (f", removed on {_fmt(removal)}" if removal else "") + f"; the matched work is “{work}”" + (f", segment {seg}" if seg else "") + ".",
            ["[removal notice]"], ["video_title", "video_id", "platform_name", "platform_case_id", "claim_date", "matched_work_title", "matched_segment"], ["R0", "R1"])
        add(f"2. {CN_STATEMENT}", [], [], ["R7", "R8"])
        add(f"I purchased a {tier} licence for “{work}” from {licensor} on {_fmt(purchase)}" + (f", order {order}" if order else "") + ".", [receipt_cite],
            ["licence_tier", "purchased_work_title", "licensor_name", "purchase_date", "order_id"], ["R2"])
        if r4.status == "pass" and grant is not None:
            add(f"On {_fmt(email_date)} {licensor} confirmed in writing: “{_short(grant.quote)}”.", [email_cite], ["email_date", "grant_statement"], ["R4"])
        elif covered is not None:
            add(f"The Licence Certificate is under Licence Terms {version}; clause {covered.sources[0].clause_ref or ''} permits “{_short(covered.quote)}”.".replace("clause  ", "clause "),
                [cert_cite], ["licence_version", covered_key], ["R2", "R3"])
        if publish:
            add(f"The video was published on {_fmt(publish)}, after that permission was in place.", ["[video export]"], ["publish_date"], ["R2", "R4"])
        if rr["R5"].status == "pass" and t.has(admin_key):
            add(f"{licensor}'s track page states that {claimant} administers content matching for this track on its behalf; the removal therefore rests on a mistake about my licence.",
                [track_cite], ["claimant_name", admin_key, "licensor_name"], ["R5"])
        add(f"3. Name: {stated.name}; address: {stated.address}; telephone: {stated.phone}.", ["[stated by you]"], ["stated_name", "stated_address", "stated_phone"], ["R7"])
        add("4. I consent to the jurisdiction of the Federal District Court for the judicial district in which my address is located, or, if my address is outside the United States, "
            f"any judicial district in which {platform} may be found, and I will accept service of process from the claimant or an agent of the claimant. [creator to confirm]", [], ["platform_name"], ["R7"])
        add("5. Signature: [signature]", [], [], ["R7"])

    text = "\n".join(s.text for s in sentences)
    pc = post_check(text, t, stated)
    draft = Draft(kind=kind, header=HEADER, sentences=sentences, text=text, post_check=pc)
    if not pc.passed:
        draft.withheld_reason = "Draft withheld: it contained an unsupported detail: " + ", ".join(pc.unsupported_tokens)
        draft.text = ""
        draft.sentences = []
        return draft
    if llm is not None and os.environ.get("NOTICEGUARD_SMOOTH_DRAFT", "0") in ("1", "true"):
        draft = smooth_with_llm(draft, t, stated, llm)
    return draft


DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2} (?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4}\b")
ID_RE = re.compile(r"\b[A-Z]{2,}-\d{4}-\d+\b|\b[A-Z]{2,}-[A-Z]{2,}-\d+\b|\b[a-z]{2,4}_[A-Za-z0-9]{4,}\b")
CLAUSE_RE = re.compile(r"(?:§|clause )\s?(\d+(?:\.\d+)?)")
PROPER_RE = re.compile(r"(?<![.!?:]\s)(?<!^)\b([A-Z][a-zA-Z]{2,})\b")


def _words(s: str) -> set[str]:
    out = set(re.findall(r"[A-Za-z][A-Za-z'’]*", s or ""))
    out.update(re.findall(r"[A-Za-z][A-Za-z'’-]*", s or ""))
    return out


def _allowed_words(t: FactTable, stated: StatedFields) -> set[str]:
    words: set[str] = set(TEMPLATE_WORDS)
    for f in t.facts:
        if f.status not in ("confirmed_by_document", "stated_by_you"):
            continue
        for s in [str(f.value)] + [src.quote for src in f.sources] + [src.context for src in f.sources]:
            words |= _words(s)
    for s in (stated.name, stated.address, stated.phone, stated.channel_name):
        words |= _words(s)
    return words


def post_check(text: str, t: FactTable, stated: StatedFields) -> PostCheck:
    """Every date, ID-like token, clause reference and proper noun in the draft must be in the confirmed facts or stated fields."""
    checked: list[str] = []
    bad: list[str] = []
    values = [str(f.value) for f in t.facts if f.status in ("confirmed_by_document", "stated_by_you")]
    quotes = [s.quote for f in t.facts if f.status == "confirmed_by_document" for s in f.sources]
    clauses = {s.clause_ref for f in t.facts for s in f.sources if s.clause_ref}
    haystack = "\n".join(values + quotes + [stated.name, stated.address, stated.phone])
    iso_dates = {v for v in values if parse_date(v) and re.match(r"^\d{4}-\d{2}-\d{2}$", v)}
    for m in DATE_RE.findall(text):
        checked.append(m)
        d = parse_date(m)
        if not d or d.isoformat() not in iso_dates:
            bad.append(m)
    for m in ID_RE.findall(text):
        checked.append(m)
        if m not in haystack:
            bad.append(m)
    for m in CLAUSE_RE.findall(text):
        checked.append("§" + m)
        if m not in clauses:
            bad.append("§" + m)
    allowed = _allowed_words(t, stated)
    for line in text.split("\n"):
        body = re.sub(r"\[[^\]]*\]", "", line)  # citation markers are not prose
        body = ID_RE.sub(" ", DATE_RE.sub(" ", body))  # IDs and dates were checked above
        for m in PROPER_RE.findall(body):
            if m in allowed or m.lower() in ("the", "this", "on", "i"):
                continue
            checked.append(m)
            bad.append(m)
    bad = list(dict.fromkeys(bad))
    return PostCheck(passed=not bad, checked_tokens=list(dict.fromkeys(checked)), unsupported_tokens=bad)


def smooth_with_llm(draft: Draft, t: FactTable, stated: StatedFields, llm: Any) -> Draft:
    """Optional prose smoothing. The smoothed text must pass the same post-check or the template is kept."""
    prompt = ("Rewrite the following draft so it reads smoothly as one letter. Keep every fact, date, ID, clause number and the bracketed "
              "citation markers exactly as they are, one sentence per line, same number of lines. Do not add any new fact.\n\n" + draft.text)
    try:
        resp = llm.complete(prompt, temperature=0.0, max_tokens=2000)
        lines = [l for l in resp.text.strip().split("\n") if l.strip()]
        if len(lines) != len(draft.sentences):
            return draft
        pc = post_check("\n".join(lines), t, stated)
        if not pc.passed:
            return draft
        for s, l in zip(draft.sentences, lines):
            s.text = l.strip()
        draft.text = "\n".join(lines)
        draft.post_check = pc
        draft.smoothed = True
    except Exception:
        return draft
    return draft
