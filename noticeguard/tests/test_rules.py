from app.models import AbstainFlags, Fact, StatedFields
from tests.helpers import fact, leo_facts, leo_mappings, mapping, maya_facts, maya_mappings, rule, run, stated_full


# ---------------------------------------------------------------- R0 stage
def test_r0_stage_claim_allows_dispute_only():
    out = run(maya_facts(), maya_mappings(), "dispute")
    assert out.stage == "claim" and out.available_steps == ["dispute"] and rule(out, "R0").status == "pass"


def test_r0_wrong_step_is_needs_adviser():
    out = run(maya_facts(), maya_mappings(), "counter_notice")
    assert rule(out, "R0").status == "fail" and out.verdict == "needs_adviser"
    assert "next available step is a dispute" in out.verdict_explanation


def test_r0_removed_stage_allows_counter_notice():
    out = run(leo_facts(), leo_mappings(), "counter_notice", stated_full())
    assert out.stage == "removed_with_strike" and out.available_steps == ["counter_notice"]


def test_r0_no_notice():
    facts = [f for f in maya_facts() if f.key != "notice_kind"]
    out = run(facts, maya_mappings(), "dispute")
    assert out.stage == "unknown" and out.verdict == "needs_adviser"


# ---------------------------------------------------------------- R1 work identity
def test_r1_match_and_mismatch():
    assert rule(run(maya_facts(), maya_mappings(), "dispute"), "R1").status == "pass"
    out = run(maya_facts(matched_title="Glasslines"), maya_mappings(), "dispute")
    assert rule(out, "R1").status == "fail" and out.verdict == "needs_adviser"
    assert "different work" in rule(out, "R1").explanation


def test_r1_title_with_artist_suffix_matches():
    facts = [f if f.key != "matched_work_title" else fact("matched_work_title", "Glasslight — Lumen Vale") for f in maya_facts()]
    assert rule(run(facts, maya_mappings(), "dispute"), "R1").status == "pass"


# ---------------------------------------------------------------- R2 version in force
def test_r2_certificate_version_governs_with_clause():
    r2 = rule(run(maya_facts(), maya_mappings(), "dispute"), "R2")
    assert r2.status == "pass" and r2.data["version_in_force"] == "v2"
    assert "clause 9.1" in r2.explanation and "v2 applies" in r2.explanation
    assert "governing_terms_clause" in r2.facts_used and "licence_version" in r2.facts_used


def test_r2_no_governing_clause_is_unknown():
    out = run(maya_facts(with_governing=False), [m for m in maya_mappings() if m.question != "governing_terms_selects_purchase_version"], "dispute")
    assert rule(out, "R2").status == "unknown" and out.verdict == "needs_adviser"


def test_r2_ambiguous_governing_clause_is_unknown():
    out = run(maya_facts(), maya_mappings(governing=["yes", "unclear", "yes"]), "dispute")
    assert rule(out, "R2").status == "unknown" and out.verdict == "needs_adviser"


def test_r2_same_version_passes_without_clause():
    out = run(leo_facts(), leo_mappings(), "counter_notice", stated_full())
    assert rule(out, "R2").status == "pass" and rule(out, "R2").data["version_in_force"] == "v3"


def test_r2_infer_version_from_terms_effective_date():
    facts = [f for f in maya_facts() if f.key not in ("licence_version", "licence_version_on_receipt")]
    facts = [f if f.key != "purchase_date" else fact("purchase_date", "2025-07-01", "receipt") for f in facts]
    r2 = rule(run(facts, maya_mappings(), "dispute"), "R2")
    assert r2.status == "pass" and r2.data["version_in_force"] == "v3"


# ---------------------------------------------------------------- R3 permitted use
def test_r3_pass_with_agreeing_mapping():
    r3 = rule(run(maya_facts(), maya_mappings(), "dispute"), "R3")
    assert r3.status == "pass" and "clause 4.1" in r3.explanation and "v2" in r3.explanation


def test_r3_uses_version_in_force_not_current_terms():
    # terms v3 excluded clause says yes, but v2 governs -> v2 clause decides
    out = run(maya_facts(), maya_mappings(), "dispute")
    assert rule(out, "R3").data["covered_by"] == "permitted_use[cert:4.1]"


def test_r3_ambiguous_mapping_is_unknown():
    out = run(maya_facts(), maya_mappings(cert_covers=["yes", "no", "yes"]), "dispute")
    assert rule(out, "R3").status == "unknown" and out.verdict == "needs_adviser"


def test_r3_excluded_use_fails():
    out = run(leo_facts(), leo_mappings(), "counter_notice", stated_full())
    assert rule(out, "R3").status == "fail" and "Monetised use requires a Pro licence" in rule(out, "R3").explanation


def test_r3_monetised_unknown_is_gap():
    facts = [f for f in maya_facts() if f.key not in ("monetised_on_publish",)]
    out = run(facts, maya_mappings(), "dispute", StatedFields(monetised="unknown"))
    assert rule(out, "R3").status == "fail" and out.verdict == "evidence_gap"
    assert any(f.key == "monetised_on_publish" and f.status == "missing" for f in out.facts)


def test_r3_stated_monetised_used_when_no_metadata():
    facts = [f for f in maya_facts() if f.key != "monetised_on_publish"]
    out = run(facts, maya_mappings(), "dispute", StatedFields(monetised="yes"))
    assert rule(out, "R3").status == "pass" and "stated_monetised" in rule(out, "R3").facts_used


# ---------------------------------------------------------------- R4 grant email
def test_r4_not_applicable_without_email():
    assert rule(run(leo_facts(), leo_mappings(), "counter_notice", stated_full()), "R4").status == "not_applicable"


def test_r4_email_before_publish_overrides_r3():
    out = run(leo_facts(with_email=True), leo_mappings(with_email=True), "counter_notice", stated_full())
    r4 = rule(out, "R4")
    assert r4.status == "pass" and "2 September 2025" in r4.explanation and "10 September 2025" in r4.explanation
    assert out.verdict == "evidence_ready"


def test_r4_email_after_publish_fails():
    out = run(leo_facts(with_email=True, email_date="2025-09-15"), leo_mappings(with_email=True), "counter_notice", stated_full())
    r4 = rule(out, "R4")
    assert r4.status == "fail" and "after you published" in r4.explanation
    assert out.verdict == "evidence_gap"
    assert any("on or before 10 September 2025" in g.needed for g in out.gap_fixes)


def test_r4_ambiguous_grant_is_unknown():
    out = run(leo_facts(with_email=True), leo_mappings(with_email=True, grant=["yes", "unclear", "yes"]), "counter_notice", stated_full())
    assert rule(out, "R4").status == "unknown" and out.verdict == "needs_adviser"


def test_r4_uses_monetisation_start_when_published_unmonetised():
    facts = leo_facts(with_email=True, email_date="2025-09-12")
    facts = [f if f.key != "monetised_on_publish" else fact("monetised_on_publish", False, "video_metadata") for f in facts]
    facts = [f if f.key != "monetisation_start_date" else fact("monetisation_start_date", "2025-09-15", "video_metadata") for f in facts]
    out = run(facts, leo_mappings(with_email=True), "counter_notice", stated_full())
    assert rule(out, "R4").status == "pass" and "started monetisation" in rule(out, "R4").explanation


# ---------------------------------------------------------------- R5 claimant chain
def test_r5_via_track_page_administrator():
    r5 = rule(run(maya_facts(), maya_mappings(), "dispute"), "R5")
    assert r5.status == "pass" and r5.data["classification"] == "licensed_use_conflict" and "administered by Northline Rights" in r5.explanation


def test_r5_unrelated_claimant_is_adviser():
    out = run(maya_facts(claimant="Copperfield Media"), maya_mappings(), "dispute")
    assert rule(out, "R5").status == "unknown" and out.verdict == "needs_adviser"
    assert "ownership question" in out.verdict_explanation


def test_r5_claimant_is_licensor():
    out = run(maya_facts(claimant="Glasswork Audio"), maya_mappings(), "dispute")
    assert rule(out, "R5").status == "pass" and rule(out, "R5").data["classification"] == "licensor_direct"


# ---------------------------------------------------------------- R6
def test_r6_segment_inside_duration():
    assert rule(run(maya_facts(), maya_mappings(), "dispute"), "R6").status == "pass"


# ---------------------------------------------------------------- R7/R8 verdict and precedence
def test_r8_maya_ready_for_dispute():
    out = run(maya_facts(), maya_mappings(), "dispute")
    assert out.verdict == "evidence_ready"
    assert [c.status for c in out.statement.components] == ["supported", "supported", "supported"]


def test_r8_leo_gap_then_ready():
    gap = run(leo_facts(), leo_mappings(), "counter_notice", stated_full())
    assert gap.verdict == "evidence_gap"
    assert any(g.component == "CN2a" and "on or before 10 September 2025" in g.needed for g in gap.gap_fixes)
    ready = run(leo_facts(with_email=True), leo_mappings(with_email=True), "counter_notice", stated_full())
    assert ready.verdict == "evidence_ready"


def test_r8_precedence_adviser_beats_gap():
    # Leo without email (gap) plus an unrelated claimant (adviser) -> adviser
    facts = [f if f.key != "claimant_name" else fact("claimant_name", "Copperfield Media") for f in leo_facts()]
    assert run(facts, leo_mappings(), "counter_notice", stated_full()).verdict == "needs_adviser"


def test_r8_cn3_missing_is_gap():
    out = run(leo_facts(with_email=True), leo_mappings(with_email=True), "counter_notice", StatedFields())
    assert out.verdict == "evidence_gap"
    assert any(c.id == "CN3" and c.status == "not_supported" for c in out.statement.components)
    assert any(g.component == "CN3" for g in out.gap_fixes)


def test_r8_conflicting_fact_is_adviser():
    facts = maya_facts()
    facts.append(Fact(key="purchase_date", value="2025-04-01", status="conflicting", note="Documents disagree on purchase date"))
    facts = [f if f.key != "purchase_date" or f.status == "conflicting" else f for f in facts]
    for f in facts:
        if f.key == "purchase_date":
            f.status = "conflicting"
            f.note = "Documents disagree on purchase date"
    assert run(facts, maya_mappings(), "dispute").verdict == "needs_adviser"


# ---------------------------------------------------------------- R9 routes
def test_r9_routes_claim_stage_order():
    out = run(maya_facts(), maya_mappings(), "dispute")
    assert [r.rank for r in out.routes] == [1, 2]
    assert "release the claim" in out.routes[0].title and out.routes[0].step is None
    assert out.routes[1].step == "dispute" and out.routes[1].evidence_status == "evidence_ready" and out.routes[1].is_chosen_step


def test_r9_routes_removed_stage():
    out = run(leo_facts(with_email=True), leo_mappings(with_email=True), "counter_notice", stated_full())
    assert "retract the removal request" in out.routes[0].title and out.routes[0].evidence_status == "evidence_ready"
    assert out.routes[1].step == "counter_notice"


def test_step_evidence_shows_counter_notice_supported_for_maya():
    out = run(maya_facts(), maya_mappings(), "dispute", stated_full())
    se = {s.step: s for s in out.step_evidence}
    assert se["dispute"].available and se["dispute"].evidence_status == "evidence_ready"
    assert not se["counter_notice"].available and se["counter_notice"].evidence_status == "evidence_ready"


# ---------------------------------------------------------------- R10 abstain
def test_r10_fair_use_flag():
    out = run(maya_facts(), maya_mappings(), "dispute", abstain=AbstainFlags(fair_use=True))
    assert out.verdict == "needs_adviser" and "fair use" in out.verdict_explanation


def test_r10_ownership_flag():
    out = run(maya_facts(), maya_mappings(), "dispute", abstain=AbstainFlags(ownership=True))
    assert out.verdict == "needs_adviser"
