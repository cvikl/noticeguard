"""Fact table construction: verified extractions + stated-by-you fields -> list[Fact] with conflict detection."""
from __future__ import annotations

import difflib
import re
from datetime import date
from typing import Any, Iterable, Optional

from .models import Document, Extraction, Fact, RejectedFact, Source, Span, StatedFields

# Fact types that are kept per notice document (one fact per document, same key allowed multiple times).
PER_DOCUMENT_KEYS = {"notice_kind", "claim_date", "claim_effect", "deadline_date", "strike_count", "strike_date",
                     "governing_terms_clause", "administrator_clause"}
# List-valued types: each extracted clause becomes its own fact, keyed with the doc type and clause ref.
LIST_KEYS = {"permitted_use", "excluded_use"}
# Keys compared across documents; a mismatch marks the fact as conflicting.
CONFLICT_KEYS = {"purchase_date", "licence_version", "publish_date", "licensed_work_title", "video_id"}
# Cross-document aliases folded into a conflict group (source key -> group key)
CONFLICT_ALIASES = {
    "purchased_work_title": "licensed_work_title",
    "licence_version_on_receipt": "licence_version",
}
DATE_KEYS = {"claim_date", "deadline_date", "strike_date", "purchase_date", "issue_date", "effective_date",
             "email_date", "publish_date", "monetisation_start_date", "removal_date"}
BOOL_KEYS = {"monetised_on_publish"}
VERSION_KEYS = {"licence_version", "licence_version_on_receipt", "terms_version"}
DOC_PRIORITY = ["licence_certificate", "receipt", "licensor_email", "track_page", "licensor_terms", "video_metadata",
                "claim_notice", "removal_notice", "strike_notice", "appeal_response", "dispute_response", "other"]

DATE_GROUP = {"purchase_date", "issue_date", "publish_date", "monetisation_start_date", "claim_date", "strike_date",
              "email_date", "effective_date", "deadline_date"}

def parse_date(value: Any) -> Optional[date]:
    """Parse a date span in code. dayfirst=True for UK/EU-formatted documents; ISO always wins."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    # keep only the part of the span that looks like a date (labels such as "Order date:" confuse the parser)
    m = re.search(r"(?:\b[A-Za-z]{3},?\s+)?\b(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9}\.?,?\s+\d{4}|[A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", s)
    candidate = m.group(1) if m else s
    try:
        from dateutil import parser as dparser

        return dparser.parse(candidate, dayfirst=True, fuzzy=False, default=None).date()  # type: ignore[arg-type]
    except Exception:
        try:
            from dateutil import parser as dparser

            return dparser.parse(candidate, dayfirst=True, fuzzy=True).date()
        except Exception:
            return None


CATEGORICAL_KEYS = {"notice_kind", "claim_effect", "strike_count"}


def derive_notice_kind(span: str) -> Optional[str]:
    """Label derived in code from keywords in the evidencing sentence. Never emitted by the model."""
    t = span.lower()
    t_no_neg = re.sub(r"\bnot\s+(a\s+)?copyright\s+strike\b|\bno\s+strike\b|\bis\s+not\s+a\s+strike\b", " ", t)
    if re.search(r"\bremov(ed|al)\b|\btaken down\b", t):
        return "removal"
    if re.search(r"\bstrike\b", t_no_neg):
        return "strike"
    if re.search(r"\bappeal\b", t) and re.search(r"\breject|\bdenied|\bupheld|\bunsuccessful", t):
        return "appeal_rejected"
    if re.search(r"\bdispute\b", t) and re.search(r"\breinstat|\breject|\bupheld|\bdenied|\bunsuccessful", t):
        return "dispute_rejected"
    if re.search(r"\bclaim(ed|s)?\b", t):
        return "claim"
    return None


def derive_claim_effect(span: str) -> Optional[str]:
    t = span.lower()
    if re.search(r"\bremov(ed|al)\b|\btaken down\b", t):
        return "removed"
    if re.search(r"\brevenue\b|\bmonetis|\bads?\b", t) and re.search(r"\bclaimant\b|\bdirected\b|\bredirected\b", t):
        return "monetised_to_claimant"
    if re.search(r"\bblocked\b|\bunavailable\b|\bmuted\b", t):
        return "blocked"
    if re.search(r"\btrack(ed|ing)\b|\bstatistics\b|\bno action\b", t):
        return "tracked"
    return None

def norm_version(value: Any) -> Optional[str]:
    if value is None:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", str(value))
    return f"v{m.group(1)}" if m else None


def norm_bool(value: Any) -> Optional[bool]:
    """Derive true/false from an evidencing span, in code (e.g. 'Monetisation at publish: ON')."""
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if re.search(r"\b(off|no|disabled|false|not monetised|unmonetised)\b", s):
        return False
    if re.search(r"\b(on|yes|enabled|true|monetised|monetized)\b", s):
        return True
    return None


def norm_title(s: Any) -> str:
    t = str(s or "").lower().strip().strip('"\'“”‘’')
    t = re.split(r"\s+[—–-]\s+|\s+by\s+|\s*\(", t)[0]
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def titles_match(a: Any, b: Any) -> bool:
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    return difflib.SequenceMatcher(None, na, nb).ratio() >= 0.9


def norm_name(s: Any) -> str:
    t = str(s or "").lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = re.sub(r"\b(ltd|limited|inc|llc|plc|gmbh|co|company|corp|corporation)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def names_match(a: Any, b: Any) -> bool:
    na, nb = norm_name(a), norm_name(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    return difflib.SequenceMatcher(None, na, nb).ratio() >= 0.9


UNPARSEABLE = object()


def normalise_value(key: str, value: Any) -> Any:
    """Turn a tagged span into a rule input. Returns None when a label cannot be derived; the caller decides."""
    if key in DATE_KEYS:
        d = parse_date(value)
        return d.isoformat() if d else None
    if key in VERSION_KEYS:
        return norm_version(value)
    if key in BOOL_KEYS:
        return norm_bool(value)
    if key == "notice_kind":
        return derive_notice_kind(str(value))
    if key == "claim_effect":
        return derive_claim_effect(str(value))
    if key == "strike_count":
        m = re.search(r"\d+", str(value))
        return int(m.group(0)) if m else None
    if key in ("order_id", "platform_case_id", "video_id", "ticket_ref"):
        m = re.search(r"[A-Za-z0-9][A-Za-z0-9_\-]{2,}", str(value).split(":")[-1])
        return m.group(0) if m else str(value).strip()
    if key == "sender_address":
        m = re.search(r"[\w.+-]+@[\w.-]+", str(value))
        return m.group(0) if m else str(value).strip()
    if isinstance(value, str):
        v = value.strip().strip(":").strip()
        # strip a leading "Label:" if the model tagged the whole line
        if key not in LIST_KEYS and key not in ("governing_terms_clause", "administrator_clause", "grant_statement", "deadline_date"):
            v = re.sub(r"^[A-Za-z ]{2,30}:\s*", "", v) if ":" in v[:32] else v
        return v
    return value


def values_equal(key: str, a: Any, b: Any) -> bool:
    if key in DATE_KEYS:
        return parse_date(a) == parse_date(b) and parse_date(a) is not None
    if key in VERSION_KEYS:
        return norm_version(a) == norm_version(b)
    if key in ("licensed_work_title", "matched_work_title", "purchased_work_title", "granted_work_title", "work_title"):
        return titles_match(a, b)
    if key in BOOL_KEYS:
        return norm_bool(a) == norm_bool(b)
    return str(a).strip().lower() == str(b).strip().lower()


def _context(doc: Document, span: Span) -> str:
    """The sentence(s) of the document line(s) that contain the span, for explanations and hover text."""
    text = " ".join(doc.lines[span.line_start - 1 : span.line_end]).strip()
    if len(text) <= 320:
        return text
    # trim to the sentence containing the span
    local = span.matched_text
    i = text.find(local)
    if i == -1:
        return text[:317] + "..."
    start = max(text.rfind(". ", 0, i) + 2, 0)
    end = text.find(". ", i + len(local))
    end = len(text) if end == -1 else end + 1
    out = text[start:end].strip()
    return out if len(out) <= 320 else out[:317] + "..."


def _source(doc: Document, ex: Extraction, span: Span) -> Source:
    return Source(doc_id=doc.id, doc_filename=doc.filename, doc_type=doc.doc_type, quote=span.matched_text,
                  line_start=span.line_start, line_end=span.line_end, char_start=span.char_start, char_end=span.char_end,
                  clause_ref=ex.clause_ref, exact=span.exact, context=_context(doc, span))


def build_fact_table(verified: list[tuple[Document, Extraction, Span]], stated: StatedFields) -> list[Fact]:
    """Merge verified extractions into facts. Deterministic: order by doc priority, then doc id, then extraction order."""
    def prio(item):
        doc, ex, _ = item
        p = DOC_PRIORITY.index(doc.doc_type) if doc.doc_type in DOC_PRIORITY else len(DOC_PRIORITY)
        return (p, doc.filename, doc.id)

    ordered = sorted(enumerate(verified), key=lambda t: (prio(t[1]), t[0]))
    facts: dict[str, Fact] = {}
    per_doc: list[Fact] = []
    list_counter: dict[str, int] = {}
    group_values: dict[str, list[tuple[Any, Source, str]]] = {}  # conflict group -> (value, source, original key)

    for _, (doc, ex, span) in ordered:
        key = ex.type
        value = normalise_value(key, ex.value)
        src = _source(doc, ex, span)
        if value is None:
            reason = "unparseable date" if key in DATE_KEYS else "could not derive a label from the tagged text"
            facts[f"{key}?{doc.id}"] = Fact(key=key, value=ex.value, status="conflicting", sources=[src],
                                            note=f"{reason}: {ex.value!r}", group="dates" if key in DATE_GROUP else None)
            continue
        if key in LIST_KEYS:
            n = list_counter.get(doc.id + key, 0) + 1
            list_counter[doc.id + key] = n
            ref = (ex.clause_ref or str(n)).replace(" ", "")
            fkey = f"{key}[{_doc_short(doc)}:{ref}]"
            if fkey in facts:
                fkey = f"{key}[{_doc_short(doc)}:{ref}#{n}]"
            facts[fkey] = Fact(key=fkey, value=value, status="confirmed_by_document", sources=[src], group="clauses")
            continue
        if key in PER_DOCUMENT_KEYS:
            per_doc.append(Fact(key=key, value=value, status="confirmed_by_document", sources=[src],
                                group="dates" if key in DATE_GROUP else None))
            continue
        group = CONFLICT_ALIASES.get(key, key)
        if group in CONFLICT_KEYS:
            group_values.setdefault(group, []).append((value, src, key))
        if key in facts:
            f = facts[key]
            if values_equal(key, f.value, value):
                f.sources.append(src)
            else:
                f.alternatives.append({"value": value, "doc_id": doc.id, "doc_filename": doc.filename, "quote": src.quote})
            continue
        facts[key] = Fact(key=key, value=value, status="confirmed_by_document", sources=[src],
                          group="dates" if key in DATE_GROUP else None)

    # conflict detection across documents for grouped keys
    for group, items in group_values.items():
        base_value, base_src, _ = items[0]
        conflicting = [it for it in items[1:] if not values_equal(group, base_value, it[0])]
        if conflicting:
            for _, src, key in items:
                if key in facts:
                    facts[key].status = "conflicting"
                    facts[key].note = f"Documents disagree on {group.replace('_', ' ')}: " + "; ".join(
                        f"{it[1].doc_filename} says {it[0]!r}" for it in items)
                    facts[key].alternatives = [{"value": it[0], "doc_id": it[1].doc_id, "doc_filename": it[1].doc_filename, "quote": it[1].quote} for it in items]

    return list(facts.values()) + per_doc + stated_facts(stated)


def stated_facts(stated: StatedFields) -> list[Fact]:
    """Structured stated-by-you fields as facts. Never from free text."""
    out: list[Fact] = []
    stated_map = {
        "stated_name": stated.name.strip(), "stated_address": stated.address.strip(), "stated_phone": stated.phone.strip(),
        "stated_channel_name": stated.channel_name.strip(),
    }
    for k, v in stated_map.items():
        if v:
            out.append(Fact(key=k, value=v, status="stated_by_you", group="about_you"))
    if stated.monetised in ("yes", "no"):
        out.append(Fact(key="stated_monetised", value=(stated.monetised == "yes"), status="stated_by_you", group="about_you"))
    return out


def _doc_short(doc: Document) -> str:
    return {"licence_certificate": "cert", "licensor_terms": "terms", "licensor_email": "email", "receipt": "receipt",
            "track_page": "track", "video_metadata": "video", "claim_notice": "claim", "removal_notice": "removal",
            "strike_notice": "strike", "appeal_response": "appeal", "dispute_response": "dispute"}.get(doc.doc_type, doc.doc_type)


class FactTable:
    """Read-only helper over a list of facts."""

    def __init__(self, facts: Iterable[Fact]):
        self.facts: list[Fact] = list(facts)
        self._by_key: dict[str, list[Fact]] = {}
        for f in self.facts:
            self._by_key.setdefault(f.key, []).append(f)

    def get(self, key: str) -> Optional[Fact]:
        items = self._by_key.get(key) or []
        for f in items:
            if f.status in ("confirmed_by_document", "stated_by_you"):
                return f
        return items[0] if items else None

    def value(self, key: str, default: Any = None) -> Any:
        f = self.get(key)
        return f.value if f and f.status in ("confirmed_by_document", "stated_by_you") else default

    def all(self, key: str) -> list[Fact]:
        return list(self._by_key.get(key) or [])

    def starting_with(self, prefix: str) -> list[Fact]:
        return [f for f in self.facts if f.key.startswith(prefix)]

    def by_doc(self, doc_id: str) -> list[Fact]:
        return [f for f in self.facts if any(s.doc_id == doc_id for s in f.sources)]

    def conflicting(self) -> list[Fact]:
        return [f for f in self.facts if f.status == "conflicting"]

    def has(self, key: str) -> bool:
        return self.get(key) is not None and self.get(key).status in ("confirmed_by_document", "stated_by_you")

    def doc_version(self, doc_id: str) -> Optional[str]:
        """Licence/terms version stated by the document with this id."""
        for key in ("licence_version", "terms_version", "licence_version_on_receipt"):
            for f in self.all(key):
                if any(s.doc_id == doc_id for s in f.sources):
                    return norm_version(f.value)
                for alt in f.alternatives:
                    if alt.get("doc_id") == doc_id:
                        return norm_version(alt.get("value"))
        return None
