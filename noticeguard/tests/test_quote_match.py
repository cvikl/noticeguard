import pytest

from app.facts import build_fact_table, normalise_value
from app.ingest import make_document
from app.models import StatedFields
from app.quote_match import ExtractionFailure, canon, parse_tags, roundtrip_diff, verify_tagged

TEXT = """GLASSWORK AUDIO — LICENCE CERTIFICATE
Issued: 12 March 2025
Licence Terms version 2

4. Permitted and excluded uses
4.1 Standard licence permits use of the Work as background music in video content, including monetised video on social platforms, on channels operated by the Licensee.
4.3 The licence does not permit redistribution of the Work as a standalone audio file.
6.1 This certificate is governed by Licence Terms v2 as in force on the date of issue.
"""


def doc():
    return make_document("cert.txt", TEXT.encode(), "licence_certificate", "d1")


def test_roundtrip_identical_text_and_line_numbers():
    tagged = TEXT.replace("12 March 2025", "<issue_date>12 March 2025</issue_date>").replace(
        "4.1 Standard licence permits use of the Work as background music in video content, including monetised video on social platforms, on channels operated by the Licensee.",
        '4.1 <permitted_use clause="4.1">Standard licence permits use of the Work as background music in video content, including monetised video on social platforms, on channels operated by the Licensee.</permitted_use>')
    res = verify_tagged(doc(), tagged)
    by = {ex.type: (ex, sp) for ex, sp in res.spans}
    ex, sp = by["issue_date"]
    assert ex.value == "12 March 2025" and sp.line_start == 2 and sp.line_end == 2
    assert doc().text[sp.char_start:sp.char_end] == "12 March 2025"
    ex2, sp2 = by["permitted_use"]
    assert ex2.clause_ref == "4.1" and sp2.line_start == 6 and sp2.exact


def test_roundtrip_tolerates_whitespace_and_curly_quotes():
    d = make_document("t.txt", 'He said “your licence” — twice\nand  then left.'.encode(), "other", "d2")
    tagged = 'He said "your <licensee_name>licence</licensee_name>" - twice and then left.'
    res = verify_tagged(d, tagged)
    assert len(res.spans) == 1
    assert res.spans[0][1].matched_text == "licence"


def test_rewrite_rejected():
    with pytest.raises(ExtractionFailure) as e:
        verify_tagged(doc(), TEXT.replace("background music", "foreground music"))
    assert "background" in e.value.diff


def test_omission_rejected():
    with pytest.raises(ExtractionFailure):
        verify_tagged(doc(), TEXT.replace("4.3 The licence does not permit redistribution of the Work as a standalone audio file.\n", ""))


def test_insertion_rejected():
    with pytest.raises(ExtractionFailure):
        verify_tagged(doc(), TEXT + "Note: extracted by model.\n")


def test_nested_tags_rejected():
    tagged = TEXT.replace("12 March 2025", "<issue_date>12 <x>March</x> 2025</issue_date>")
    with pytest.raises(ExtractionFailure):
        verify_tagged(doc(), tagged)


def test_unclosed_tag_rejected():
    with pytest.raises(ExtractionFailure):
        verify_tagged(doc(), TEXT.replace("12 March 2025", "<issue_date>12 March 2025"))


def test_unknown_tag_dropped_not_fatal():
    tagged = TEXT.replace("12 March 2025", "<made_up>12 March 2025</made_up>")
    res = verify_tagged(doc(), tagged, allowed_tags={"issue_date"})
    assert res.spans == [] and res.dropped and "not in the tag set" in res.dropped[0][2]


def test_multiline_span():
    tagged = TEXT.replace("Issued: 12 March 2025\nLicence Terms version 2", "<x>Issued: 12 March 2025\nLicence Terms version 2</x>")
    res = verify_tagged(doc(), tagged)
    sp = res.spans[0][1]
    assert sp.line_start == 2 and sp.line_end == 3


def test_unparseable_date_becomes_conflicting():
    d = doc()
    tagged = TEXT.replace("12 March 2025", "<issue_date>12 March 2025</issue_date>").replace(
        "Licence Terms version 2", "<licence_version>Licence Terms version 2</licence_version>")
    res = verify_tagged(d, tagged)
    facts2 = build_fact_table([(d, e, s) for e, s in res.spans], StatedFields())
    # simulate a nonsense date span by editing the extraction value on a fresh parse
    ex, sp = verify_tagged(d, tagged).spans[0]
    ex.value = "the twelfth of Marchember"
    facts = build_fact_table([(d, ex, sp)], StatedFields())
    assert facts[0].status == "conflicting" and "unparseable date" in (facts[0].note or "")
    by = {f.key: f for f in facts2}
    assert by["issue_date"].value == "2025-03-12" and by["licence_version"].value == "v2"


def test_normalise_values():
    assert normalise_value("purchase_date", "Tue, 2 Sep 2025 10:14:00 +0100") == "2025-09-02"
    assert normalise_value("publish_date", "2025-08-30 18:05 UTC") == "2025-08-30"
    assert normalise_value("licence_version", "Licence Terms version 3") == "v3"
    assert normalise_value("monetised_on_publish", "Monetisation at publish: ON") is True
    assert normalise_value("monetised_on_publish", "Monetisation at publish: OFF") is False
    assert normalise_value("notice_kind", "The claimant rejected your appeal and submitted a copyright removal request. Your video has been removed.") == "removal"
    assert normalise_value("notice_kind", "The claimant has reviewed your dispute and reinstated their claim. You may appeal.") == "dispute_rejected"
    assert normalise_value("notice_kind", "A copyright owner has claimed content in your video through ClipStream Content Match.") == "claim"
    assert normalise_value("notice_kind", "This is not a copyright strike.") is None
    assert normalise_value("claim_effect", "Ad revenue for this video is being directed to the claimant.") == "monetised_to_claimant"
    assert normalise_value("strike_count", "copyright strike (1 of 3)") == 1


def test_canon_and_diff():
    assert canon(" a b  –  c ") == "a b - c"
    assert roundtrip_diff("a b", "a  b") is None
    assert roundtrip_diff("a b", "a c") is not None
