"""Round-trip verification of tagged extraction output.

The model returns the original document with inline XML-style tags around spans. We:
  1. parse the tags with a tolerant regex (nesting depth 1 only),
  2. strip the tags and compare the result with the original document after whitespace/quote/dash
     normalisation; ANY difference rejects the whole output,
  3. map every tagged span back to exact line numbers and character offsets in the original text.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from typing import Optional

from .models import Document, Extraction, Span

_CHAR_MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "–": "-", "—": "-", "‒": "-", "−": "-", "‐": "-", "‑": "-",
    " ": " ",
}
_TRANS = str.maketrans(_CHAR_MAP)

TAG_RE = re.compile(r"<(/?)([A-Za-z_][A-Za-z0-9_]*)((?:\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*\"[^\"]*\")*)\s*/?>")
ATTR_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\"([^\"]*)\"")


def canon(s: str) -> str:
    """Normalise quotes/dashes and collapse all whitespace to single spaces. Case-sensitive."""
    return re.sub(r"\s+", " ", s.translate(_TRANS)).strip()


def _build_index(text: str) -> tuple[str, list[int]]:
    """Canonical text plus a map canonical_index -> original_index."""
    out: list[str] = []
    idx: list[int] = []
    prev_space = True
    for i, ch in enumerate(text):
        ch2 = _CHAR_MAP.get(ch, ch)
        if ch2.isspace():
            if prev_space:
                continue
            out.append(" ")
            idx.append(i)
            prev_space = True
        else:
            out.append(ch2)
            idx.append(i)
            prev_space = False
    while out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


@dataclass
class ExtractionFailure(Exception):
    reason: str
    diff: str = ""

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.reason}\n{self.diff}".strip()


@dataclass
class TaggedSpan:
    tag: str
    text: str
    attrs: dict[str, str]
    start: int  # offsets in the stripped text
    end: int


@dataclass
class TaggedResult:
    spans: list[tuple[Extraction, Span]] = field(default_factory=list)
    dropped: list[tuple[str, str, str]] = field(default_factory=list)  # (tag, text, reason)
    stripped: str = ""


def parse_tags(tagged: str) -> tuple[str, list[TaggedSpan]]:
    """Strip tags, returning the plain text and the spans (positions in the plain text).
    Raises ExtractionFailure on nesting deeper than 1, mismatched or unclosed tags."""
    out: list[str] = []
    spans: list[TaggedSpan] = []
    pos = 0
    open_tag: Optional[tuple[str, dict[str, str], int]] = None
    for m in TAG_RE.finditer(tagged):
        out.append(tagged[pos : m.start()])
        pos = m.end()
        closing, name, attr_str = m.group(1) == "/", m.group(2), m.group(3) or ""
        if m.group(0).endswith("/>"):
            continue  # self-closing tag carries no span; ignore
        cur_len = sum(len(s) for s in out)
        if not closing:
            if open_tag is not None:
                raise ExtractionFailure(f"nested tag <{name}> inside <{open_tag[0]}> (only depth 1 is allowed)")
            open_tag = (name, dict(ATTR_RE.findall(attr_str)), cur_len)
        else:
            if open_tag is None or open_tag[0] != name:
                raise ExtractionFailure(f"closing tag </{name}> without a matching opening tag")
            start = open_tag[2]
            spans.append(TaggedSpan(tag=name, text="".join(out)[start:cur_len], attrs=open_tag[1], start=start, end=cur_len))
            open_tag = None
    out.append(tagged[pos:])
    if open_tag is not None:
        raise ExtractionFailure(f"tag <{open_tag[0]}> was never closed")
    return "".join(out), spans


def roundtrip_diff(original: str, stripped: str) -> Optional[str]:
    """None when the stripped output equals the original (after normalisation); otherwise a short diff."""
    a, b = canon(original), canon(stripped)
    if a == b:
        return None
    a_lines = [canon(l) for l in original.split("\n") if canon(l)]
    b_lines = [canon(l) for l in stripped.split("\n") if canon(l)]
    diff = list(difflib.unified_diff(a_lines, b_lines, fromfile="original", tofile="your output", lineterm="", n=0))
    if len(diff) > 40:
        diff = diff[:40] + ["... (truncated)"]
    return "\n".join(diff) or "texts differ in whitespace-insensitive content"


def verify_tagged(doc: Document, tagged: str, allowed_tags: Optional[set[str]] = None) -> TaggedResult:
    """Parse, round-trip-check and locate every tagged span. Raises ExtractionFailure if the model changed the text."""
    tagged = tagged.strip()
    fence = re.search(r"```(?:xml|text)?\s*(.*?)```\s*$", tagged, re.S)
    if fence and tagged.startswith("```"):
        tagged = fence.group(1)
    stripped, spans = parse_tags(tagged)
    diff = roundtrip_diff(doc.text, stripped)
    if diff is not None:
        raise ExtractionFailure("the output text does not match the document", diff)

    orig_canon, orig_idx = _build_index(doc.text)
    strip_canon, strip_idx = _build_index(stripped)
    assert orig_canon == strip_canon
    # inverse map: stripped position -> canonical index (first canonical char at or after that position)
    inv: dict[int, int] = {}
    for j, s in enumerate(strip_idx):
        inv.setdefault(s, j)
    result = TaggedResult(stripped=stripped)
    for sp in spans:
        text = sp.text
        if not canon(text):
            result.dropped.append((sp.tag, text, "empty span"))
            continue
        if allowed_tags is not None and sp.tag not in allowed_tags:
            result.dropped.append((sp.tag, text, f"tag <{sp.tag}> is not in the tag set for a {doc.doc_type}"))
            continue
        # trim to non-space content inside the span
        s = sp.start
        while s < sp.end and stripped[s].isspace():
            s += 1
        e = sp.end
        while e > s and stripped[e - 1].isspace():
            e -= 1
        cs = inv.get(s)
        ce = inv.get(e - 1)
        if cs is None or ce is None:
            result.dropped.append((sp.tag, text, "could not locate span"))
            continue
        start, end = orig_idx[cs], orig_idx[ce] + 1
        matched = doc.text[start:end]
        span = Span(line_start=doc.text.count("\n", 0, start) + 1, line_end=doc.text.count("\n", 0, max(start, end - 1)) + 1,
                    char_start=start, char_end=end, matched_text=matched, exact=True)
        clause = sp.attrs.get("clause") or sp.attrs.get("clause_ref")
        result.spans.append((Extraction(type=sp.tag, value=matched, quote=matched, clause_ref=clause), span))
    return result
