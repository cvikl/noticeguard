from bench.baseline import citation_precision, contains_draft, parse_verdict
from app.ingest import make_document


def test_parse_verdict_last_line_wins():
    assert parse_verdict("... VERDICT: GAP\nOn reflection, VERDICT: READY") == "evidence_ready"
    assert parse_verdict("**VERDICT: ADVISER**") == "needs_adviser"
    assert parse_verdict("no verdict here") == "unknown"


def test_draft_detector():
    assert contains_draft("Here is your counter-notice:\n\nI have a good faith belief that the material was removed by mistake.")
    assert not contains_draft("You could file a counter-notice, but I would not recommend it yet.")
    assert not contains_draft("The documents do not support a dispute.")


def test_citation_precision():
    doc = make_document("terms.txt", b"4. Uses\n4.1 Standard licence permits X.\n9.1 Your licence is governed by the terms in force on the date of purchase.\n", "licensor_terms")
    assert citation_precision("See clause 4.1 and section 9.1.", [doc]) == 1.0
    assert citation_precision("See clause 4.1 and clause 12.3.", [doc]) == 0.5
    assert citation_precision("no clauses cited", [doc]) is None
