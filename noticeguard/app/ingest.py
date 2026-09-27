"""File -> normalised Document with line offsets. Supports .txt .md .pdf .eml."""
from __future__ import annotations

import email
import email.policy
import hashlib
import io
import re
from pathlib import Path
from typing import Optional

from .models import Document

NBSP = " "


def normalise_text(text: str) -> str:
    """Unify line endings, collapse runs of spaces/tabs, keep line breaks, strip trailing spaces."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace(NBSP, " ")
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t\f\v]+", " ", line).strip()
        lines.append(line)
    # collapse 3+ blank lines to a single blank line
    out = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return out.strip("\n") + "\n"


def _pdf_to_text(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join((p.extract_text() or "") for p in reader.pages)


def _eml_to_text(data: bytes) -> str:
    msg = email.message_from_bytes(data, policy=email.policy.default)
    headers = []
    for h in ("From", "To", "Date", "Subject", "Message-ID"):
        if msg.get(h):
            headers.append(f"{h}: {msg.get(h)}")
    body = ""
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is not None:
        body = part.get_content()
        if part.get_content_type() == "text/html":
            body = re.sub(r"<[^>]+>", " ", body)
    else:  # pragma: no cover
        body = msg.get_payload(decode=True).decode("utf-8", "replace") if msg.get_payload(decode=True) else ""
    return "\n".join(headers) + "\n\n" + body


def bytes_to_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _pdf_to_text(data)
    if ext == ".eml":
        return _eml_to_text(data)
    return data.decode("utf-8", "replace")


def make_document(filename: str, data: bytes, doc_type: str, doc_id: Optional[str] = None) -> Document:
    raw = bytes_to_text(filename, data)
    text = normalise_text(raw)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return Document(
        id=doc_id or f"doc_{sha[:10]}",
        filename=Path(filename).name,
        doc_type=doc_type,
        text=text,
        lines=text.split("\n"),
        sha256=sha,
    )


def load_document(path: Path, doc_type: str, doc_id: Optional[str] = None) -> Document:
    return make_document(path.name, path.read_bytes(), doc_type, doc_id)


# Guess a doc_type from a filename for the demo loaders
_FILENAME_HINTS = [
    (r"removal|removed", "removal_notice"), (r"strike", "strike_notice"), (r"appeal", "appeal_response"),
    (r"dispute", "dispute_response"), (r"claim", "claim_notice"), (r"receipt|order", "receipt"),
    (r"certificate", "licence_certificate"), (r"terms", "licensor_terms"), (r"track_page|track-page", "track_page"),
    (r"email|\.eml$", "licensor_email"), (r"metadata|studio", "video_metadata"),
]


def guess_doc_type(filename: str) -> str:
    name = filename.lower()
    for pat, dt in _FILENAME_HINTS:
        if re.search(pat, name):
            return dt
    return "other"


def load_folder(folder: Path) -> list[Document]:
    docs = []
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() in (".txt", ".md", ".pdf", ".eml") and not p.name.startswith("."):
            docs.append(load_document(p, guess_doc_type(p.name)))
    return docs
