"""Hand-built fact tables and mapping runs for rule tests."""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

from app.models import AbstainFlags, Fact, MappingAnswer, MappingRun, Source, StatedFields
from app.rules.engine import RulesInput, run_rules

TODAY = date(2026, 9, 27)


def src(doc_type: str, quote: str, clause: Optional[str] = None, doc_id: Optional[str] = None) -> Source:
    return Source(doc_id=doc_id or f"doc_{doc_type}", doc_filename=f"{doc_type}.txt", doc_type=doc_type, quote=quote,
                  line_start=1, line_end=1, char_start=0, char_end=len(quote), clause_ref=clause)


def fact(key: str, value: Any, doc_type: str = "claim_notice", quote: str = "", clause: Optional[str] = None,
         status: str = "confirmed_by_document", doc_id: Optional[str] = None, group: Optional[str] = None) -> Fact:
    if status == "stated_by_you":
        return Fact(key=key, value=value, status="stated_by_you")
    return Fact(key=key, value=value, status=status, sources=[src(doc_type, quote or str(value), clause, doc_id)], group=group)


def mapping(question: str, fact_key: str, votes: list[str], doc_id: Optional[str] = None, clause: Optional[str] = None) -> MappingRun:
    result = "yes" if set(votes) == {"yes"} else "no" if set(votes) == {"no"} else "ambiguous"
    return MappingRun(id=f"map:{question}:{fact_key}@{doc_id}", question=question, fact_key=fact_key, clause_quote="q",
                      answers=[MappingAnswer(covers=v, reason="r") for v in votes], result=result, doc_id=doc_id, clause_ref=clause)


def maya_facts(claimant: str = "Northline Rights", admin: str = "Northline Rights", cert_version: str = "v2",
               terms_version: str = "v3", with_governing: bool = True, matched_title: str = "Glasslight") -> list[Fact]:
    f = [
        fact("platform_case_id", "CS-CLM-88213"), fact("claimant_name", claimant), fact("matched_work_title", matched_title),
        fact("matched_segment", "0:14–2:31"), fact("video_id", "vid_7Kq2x"), fact("video_title", "Studio Vlog #12"),
        fact("claim_date", "2025-09-20"), fact("notice_kind", "claim", quote="A copyright owner has claimed content in your video"),
        fact("claim_effect", "monetised_to_claimant"),
        fact("purchase_date", "2025-03-12", "receipt", "12 March 2025"), fact("order_id", "GA-2025-03112", "receipt"),
        fact("purchased_work_title", "Glasslight", "receipt"), fact("licence_tier", "Standard", "licence_certificate"),
        fact("licence_version", cert_version, "licence_certificate", f"Licence Terms version {cert_version[1:]}"),
        fact("licensed_work_title", "Glasslight", "licence_certificate"), fact("licensee_name", "Maya Ortiz", "licence_certificate"),
        fact("issue_date", "2025-03-12", "licence_certificate", "12 March 2025"),
        fact("licensor_name", "Glasswork Audio Ltd", "licence_certificate"),
        fact("permitted_use[cert:4.1]", "Standard licence permits ... monetised video on social platforms", "licence_certificate",
             "Standard licence permits use of the Work as background music in video content, including monetised video on social platforms, on channels operated by the Licensee.", "4.1", doc_id="doc_cert"),
        fact("excluded_use[cert:4.3]", "no standalone", "licence_certificate", "The licence does not permit redistribution of the Work as a standalone audio file.", "4.3", doc_id="doc_cert"),
        fact("terms_version", terms_version, "licensor_terms", "Version 3", doc_id="doc_terms"),
        fact("effective_date", "2025-06-01", "licensor_terms", "effective 1 June 2025", doc_id="doc_terms"),
        fact("permitted_use[terms:4.1]", "personal, non-commercial", "licensor_terms", "Standard licence permits use of the Work as background music in personal, non-commercial video content.", "4.1", doc_id="doc_terms"),
        fact("excluded_use[terms:4.1]", "Monetised use requires a Pro licence.", "licensor_terms", "Monetised use requires a Pro licence.", "4.1", doc_id="doc_terms"),
        fact("work_title", "Glasslight", "track_page"), fact("content_id_administrator_name", admin, "track_page",
             "Content matching and claims for this track are administered by Northline Rights on behalf of Glasswork Audio."),
        fact("platform_name", "ClipStream", "video_metadata"), fact("channel_name", "Maya Draws", "video_metadata"),
        fact("publish_date", "2025-08-30", "video_metadata"), fact("monetised_on_publish", True, "video_metadata", "Monetisation at publish: ON"),
        fact("monetisation_start_date", "2025-08-30", "video_metadata"), fact("duration", "11:48", "video_metadata"),
    ]
    # the certificate's own version must be discoverable via doc id for clause selection
    for x in f:
        if x.key == "licence_version":
            x.sources[0].doc_id = "doc_cert"
    if with_governing:
        f.append(fact("governing_terms_clause", "governed by the terms in force on the date of purchase", "licensor_terms",
                      "Your licence is governed by the terms in force on the date of purchase.", "9.1", doc_id="doc_terms"))
    return f


def maya_mappings(cert_covers: list[str] = ("yes", "yes", "yes"), governing: list[str] = ("yes", "yes", "yes")) -> list[MappingRun]:
    return [
        mapping("permitted_use_covers_actual_use", "permitted_use[cert:4.1]", list(cert_covers), "doc_cert", "4.1"),
        mapping("excluded_use_applies_to_actual_use", "excluded_use[cert:4.3]", ["no", "no", "no"], "doc_cert", "4.3"),
        mapping("permitted_use_covers_actual_use", "permitted_use[terms:4.1]", ["no", "no", "no"], "doc_terms", "4.1"),
        mapping("excluded_use_applies_to_actual_use", "excluded_use[terms:4.1]", ["yes", "yes", "yes"], "doc_terms", "4.1"),
        mapping("governing_terms_selects_purchase_version", "governing_terms_clause", list(governing), "doc_terms", "9.1"),
    ]


def leo_facts(with_email: bool = False, email_date: str = "2025-09-02", tier: str = "Standard") -> list[Fact]:
    f = [
        fact("platform_case_id", "CS-CLM-91077"), fact("claimant_name", "Northline Rights"), fact("matched_work_title", "Glasslight"),
        fact("matched_segment", "0:00–4:12"), fact("video_id", "vid_3Pm9d"), fact("video_title", "Late-night synth session"),
        fact("claim_date", "2025-09-12"), fact("notice_kind", "claim", quote="claimed content"),
        fact("claim_date", "2025-09-16", "dispute_response"), fact("notice_kind", "dispute_rejected", "dispute_response", "reinstated their claim"),
        fact("claim_date", "2025-09-22", "removal_notice"), fact("notice_kind", "removal", "removal_notice", "Your video has been removed."),
        fact("claim_effect", "removed", "removal_notice"), fact("strike_count", 1, "removal_notice", "1 of 3"),
        fact("claimant_contact", "claims@northlinerights.example", "removal_notice"),
        fact("purchase_date", "2025-08-19", "receipt", "19 August 2025"), fact("order_id", "GA-2025-08231", "receipt"),
        fact("purchased_work_title", "Glasslight", "receipt"), fact("licence_tier", tier, "licence_certificate"),
        fact("licence_version", "v3", "licence_certificate", "Licence Terms version 3", doc_id="doc_cert"),
        fact("licensed_work_title", "Glasslight", "licence_certificate"), fact("licensee_name", "Leo Marsh", "licence_certificate"),
        fact("issue_date", "2025-08-19", "licence_certificate"), fact("licensor_name", "Glasswork Audio Ltd", "licence_certificate"),
        fact("permitted_use[cert:4.1]", "personal, non-commercial", "licence_certificate",
             "Standard licence permits use of the Work as background music in personal, non-commercial video content.", "4.1", doc_id="doc_cert"),
        fact("excluded_use[cert:4.1]", "Monetised use requires a Pro licence.", "licence_certificate", "Monetised use requires a Pro licence.", "4.1", doc_id="doc_cert"),
        fact("terms_version", "v3", "licensor_terms", "Version 3", doc_id="doc_terms"),
        fact("governing_terms_clause", "in force on the date of purchase", "licensor_terms", "Your licence is governed by the terms in force on the date of purchase.", "9.1", doc_id="doc_terms"),
        fact("work_title", "Glasslight", "track_page"), fact("content_id_administrator_name", "Northline Rights", "track_page"),
        fact("platform_name", "ClipStream", "video_metadata"), fact("channel_name", "Leo Marsh Music", "video_metadata"),
        fact("publish_date", "2025-09-10", "video_metadata"), fact("monetised_on_publish", True, "video_metadata", "ON"),
        fact("monetisation_start_date", "2025-09-10", "video_metadata"), fact("duration", "42:15", "video_metadata"),
    ]
    if with_email:
        f += [
            fact("email_date", email_date, "licensor_email", "Tue, 2 Sep 2025 10:14:00 +0100", doc_id="doc_email"),
            fact("sender_address", "support@glasswork.audio", "licensor_email", doc_id="doc_email"),
            fact("grant_statement", "cleared to use Glasslight in monetised ClipStream videos", "licensor_email",
                 "We've extended your licence: you're cleared to use Glasslight in monetised ClipStream videos on your channel Leo Marsh Music.", doc_id="doc_email"),
            fact("granted_work_title", "Glasslight", "licensor_email", doc_id="doc_email"),
        ]
    return f


def leo_mappings(with_email: bool = False, grant: list[str] = ("yes", "yes", "yes"), cert_permits: list[str] = ("no", "no", "no")) -> list[MappingRun]:
    m = [
        mapping("permitted_use_covers_actual_use", "permitted_use[cert:4.1]", list(cert_permits), "doc_cert", "4.1"),
        mapping("excluded_use_applies_to_actual_use", "excluded_use[cert:4.1]", ["no", "no", "no"] if list(cert_permits) == ["yes", "yes", "yes"] else ["yes", "yes", "yes"], "doc_cert", "4.1"),
    ]
    if with_email:
        m.append(mapping("grant_covers_actual_use", "grant_statement", list(grant), "doc_email"))
    return m


def stated_full() -> StatedFields:
    return StatedFields(name="Leo Marsh", address="1 Example Road, Bristol", phone="+44 117 000 0000", monetised="unknown")


def run(facts, mappings, step, stated=None, abstain=None):
    return run_rules(RulesInput(facts=facts, mappings=mappings, step=step, stated=stated or StatedFields(), abstain=abstain or AbstainFlags(), today=TODAY))


def rule(out, rid):
    return next(r for r in out.rule_results if r.rule_id == rid)
