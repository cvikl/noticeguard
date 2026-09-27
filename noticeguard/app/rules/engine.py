"""Deterministic rules engine. Pure functions over (facts, mappings, step, stated fields, abstain flags).

No free text ever reaches this module. No LLM call happens here. Same inputs -> same output.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Optional

import yaml

from ..facts import FactTable, names_match, parse_date, stated_facts, titles_match
from ..models import (AbstainFlags, Deadline, Fact, GapFix, MappingRun, Route, RuleResult, StatedFields, Statement,
                      StatementComponent, StepEvidence)
from .routes import select_routes
from .stages import NEXT_STEP_LABEL, detect_stage

RULES_PATH = Path(__file__).with_name("rules.yaml")
_RULES_DOC = yaml.safe_load(RULES_PATH.read_text())
RULES_VERSION: str = str(_RULES_DOC["version"])
RULE_DEFS: list[dict[str, Any]] = _RULES_DOC["rules"]
RULE_NAMES = {r["id"]: r["name"] for r in RULE_DEFS}
RULE_LOGIC_TEXT = {r["id"]: r["explanation_template"] for r in RULE_DEFS}

STEP_LABELS = {"dispute": "dispute", "appeal": "appeal", "counter_notice": "counter-notice"}

DISPUTE_STATEMENT = ("I have a licence or permission from the copyright owner or their authorised representative "
                     "to use this content in this video.")
CN_STATEMENT = ("I have a good faith belief that the material was removed or disabled as a result of mistake or "
                "misidentification of the material to be removed or disabled.")
CN_CONSEQUENCE = ("This is a sworn statement under penalty of perjury. You consent to the jurisdiction of a US federal court. "
                  "The claimant then has 10 US business days to show they've filed a lawsuit before the video is restored. "
                  "Knowingly false statements can create liability under 17 U.S.C. §512(f).")
APPEAL_CONSEQUENCE = ("If the claimant rejects an appeal it must submit a copyright removal request to keep the claim. "
                      "That removes the video and places a copyright strike on the channel; three strikes within 90 days can terminate it.")
DISPUTE_CONSEQUENCE = ("The claimant has 30 days to respond. At any point while the dispute is open the claimant may instead submit a "
                       "copyright removal request, which removes the video and places a copyright strike on the channel.")


@dataclass
class RulesInput:
    facts: list[Fact]
    mappings: list[MappingRun]
    step: str
    stated: StatedFields = field(default_factory=StatedFields)
    abstain: AbstainFlags = field(default_factory=AbstainFlags)
    today: Optional[date] = None


@dataclass
class RulesOutput:
    rules_version: str
    stage: str
    available_steps: list[str]
    chosen_step: str
    verdict: str
    verdict_explanation: str
    statement: Statement
    rule_results: list[RuleResult]
    routes: list[Route]
    gap_fixes: list[GapFix]
    step_evidence: list[StepEvidence]
    deadlines: list[Deadline]
    facts: list[Fact]  # input facts plus `missing` placeholders for required facts
    actual_use: dict[str, Any]


# ----------------------------------------------------------------------------- helpers
def _fmt_date(iso: Any) -> str:
    d = parse_date(iso)
    return d.strftime("%-d %B %Y") if d else str(iso)


def _clause(fact_or_src) -> str:
    src = fact_or_src.sources[0] if isinstance(fact_or_src, Fact) and fact_or_src.sources else fact_or_src
    if src is None:
        return ""
    return f" clause {src.clause_ref}" if getattr(src, "clause_ref", None) else ""


def _doc_label(f: Optional[Fact]) -> str:
    if not f or not f.sources:
        return "a document"
    s = f.sources[0]
    return {"licence_certificate": "your licence certificate", "receipt": "your receipt", "licensor_terms": "the licensor's current terms",
            "track_page": "the licensor's track page", "licensor_email": f"the licensor's email", "video_metadata": "your video export",
            "claim_notice": "the claim notice", "removal_notice": "the removal notice", "appeal_response": "the appeal response",
            "dispute_response": "the dispute response", "strike_notice": "the strike notice"}.get(s.doc_type, s.doc_filename)


class _Ctx:
    def __init__(self, inp: RulesInput):
        self.inp = inp
        # structured stated-by-you fields are rule inputs in their own right; add them if the table lacks them
        present = {f.key for f in inp.facts}
        self.extra_stated = [f for f in stated_facts(inp.stated) if f.key not in present]
        self.table = FactTable(list(inp.facts) + self.extra_stated)
        self.maps = inp.mappings
        self.results: dict[str, RuleResult] = {}
        self.missing: list[Fact] = []
        self.today = inp.today or date.today()
        monet = self.table.value("monetised_on_publish")
        if not isinstance(monet, bool):
            monet = self.table.value("stated_monetised")
        if not isinstance(monet, bool) and inp.stated.monetised in ("yes", "no"):
            monet = inp.stated.monetised == "yes"
        self.actual_use = {
            "monetised": monet if isinstance(monet, bool) else None,
            "platform": self.table.value("platform_name"),
            "channel": self.table.value("channel_name") or self.table.value("stated_channel_name"),
            "licence_tier": self.table.value("licence_tier"),
        }

    def mapping(self, question: str, fact_key: str, doc_id: Optional[str] = None) -> Optional[MappingRun]:
        for m in self.maps:
            if m.question == question and m.fact_key == fact_key and (doc_id is None or m.doc_id == doc_id):
                return m
        return None

    def mark_missing(self, key: str, note: str, group: Optional[str] = None) -> None:
        if not any(f.key == key for f in self.missing) and not self.table.has(key):
            self.missing.append(Fact(key=key, value=None, status="missing", note=note, group=group))

    def fact_version(self, f: Fact) -> Optional[str]:
        return self.table.doc_version(f.sources[0].doc_id) if f.sources else None


def _res(rule_id: str, status: str, explanation: str, facts: list[str] = (), mappings: list[str] = (), **data) -> RuleResult:
    return RuleResult(rule_id=rule_id, rule_name=RULE_NAMES[rule_id], status=status, facts_used=list(dict.fromkeys(facts)),
                      mapping_ids=list(mappings), explanation=explanation, data=data)


# ----------------------------------------------------------------------------- rules
def rule_stage(c: _Ctx) -> RuleResult:
    stage, available, used, latest_doc = detect_stage(c.table)
    c.stage, c.available, c.latest_notice_doc = stage, available, latest_doc
    step = c.inp.step
    if stage == "unknown":
        c.mark_missing("notice_kind", "No claim, dispute, appeal or removal notice was found.")
        return _res("R0", "fail", "No platform notice was found among your documents, so the current stage cannot be determined. Upload the claim notice.",
                    used, stage=stage, available_steps=available, missing=["notice_kind"])
    if step in available:
        return _res("R0", "pass", f"Your notices show the process is at the {_stage_words(stage)} stage, where a {STEP_LABELS[step]} is the available step.",
                    used, stage=stage, available_steps=available)
    nxt = NEXT_STEP_LABEL.get(available[0], "none") if available else "none"
    return _res("R0", "fail", f"A {STEP_LABELS[step]} is not available at your current stage ({_stage_words(stage)}); "
                + (f"the next available step is {nxt}." if available else "no in-platform step is available at this stage."),
                used, stage=stage, available_steps=available, step_unavailable=True)


def _stage_words(stage: str) -> str:
    return {"claim": "claim", "dispute": "rejected dispute", "appeal": "appeal", "removed_with_strike": "removed with strike"}.get(stage, stage)


def rule_work_identity(c: _Ctx) -> RuleResult:
    t = c.table
    matched = t.get("matched_work_title")
    if not matched or matched.status != "confirmed_by_document":
        c.mark_missing("matched_work_title", "The claim notice should name the matched work.")
        return _res("R1", "fail", "None of the notices names the matched work, so it cannot be compared with your licence.", ["matched_work_title"], missing=["matched_work_title"])
    candidates = [k for k in ("licensed_work_title", "purchased_work_title", "granted_work_title") if t.has(k)]
    if not candidates:
        c.mark_missing("licensed_work_title", "A licence certificate, receipt or licensor email should name the licensed work.")
        return _res("R1", "fail", f"The claim is for “{matched.value}” but no licence document names the work it covers.",
                    ["matched_work_title", "licensed_work_title"], missing=["licensed_work_title"])
    for k in candidates:
        if t.get(k).status == "conflicting":
            return _res("R1", "unknown", f"Your documents disagree about the licensed work title ({t.get(k).note}).", ["matched_work_title", k])
    mism = [k for k in candidates if not titles_match(matched.value, t.value(k))]
    if mism:
        k = mism[0]
        return _res("R1", "fail", f"The claim is for “{matched.value}” but {_doc_label(t.get(k))} covers “{t.value(k)}”: the claim is for a different work than your licence covers.",
                    ["matched_work_title", k], title_mismatch=True)
    return _res("R1", "pass", f"The claim names “{matched.value}”, which is the work named in {_doc_label(t.get(candidates[0]))}.",
                ["matched_work_title"] + candidates)


def rule_version_in_force(c: _Ctx) -> RuleResult:
    t = c.table
    used: list[str] = []
    purchase = t.value("purchase_date") or t.value("issue_date")
    if purchase:
        used.append("purchase_date" if t.has("purchase_date") else "issue_date")
    cert_v = t.value("licence_version")
    receipt_v = t.value("licence_version_on_receipt")
    for k in ("licence_version", "licence_version_on_receipt", "purchase_date"):
        f = t.get(k)
        if f and f.status == "conflicting":
            return _res("R2", "unknown", f"Your documents disagree: {f.note}", [k])
    version = cert_v or receipt_v
    if cert_v:
        used.append("licence_version")
    elif receipt_v:
        used.append("licence_version_on_receipt")
    current_v = t.value("terms_version")
    eff = t.value("effective_date")
    if not version:
        if current_v and eff and purchase and parse_date(purchase) >= parse_date(eff):
            used += ["terms_version", "effective_date"]
            c.version_in_force = current_v
            return _res("R2", "pass", f"No version is printed on your certificate or receipt, but you purchased on {_fmt_date(purchase)}, after the current terms ({current_v}) took effect on {_fmt_date(eff)}, so {current_v} applies.", used, version_in_force=current_v)
        c.mark_missing("licence_version", "The licence certificate or receipt should state the licence terms version.")
        return _res("R2", "fail", "None of your documents states which licence terms version your purchase is under.", used + ["licence_version"], missing=["licence_version"])
    c.version_in_force = version
    if current_v and current_v != version:
        used.append("terms_version")
        gov = [m for m in c.maps if m.question == "governing_terms_selects_purchase_version"]
        yes = [m for m in gov if m.result == "yes"]
        amb = [m for m in gov if m.result == "ambiguous"]
        if yes:
            yes.sort(key=lambda m: 0 if _doc_type_of(t, m.doc_id) == "licensor_terms" else 1)
            cites = " and ".join(f"{_doc_label_by_doc(t, m.doc_id)}{' clause ' + m.clause_ref if m.clause_ref else ''}" for m in yes)
            verb = "say" if len(yes) > 1 else "says"
            return _res("R2", "pass", f"Your certificate is Licence Terms {version} (purchased {_fmt_date(purchase) if purchase else 'on the date shown'}). The current terms are {current_v}, but {cites} {verb} the terms in force on the date of purchase govern, so {version} applies.",
                        used + ["governing_terms_clause"], [m.id for m in yes], version_in_force=version, current_version=current_v)
        if amb:
            return _res("R2", "unknown", f"Your certificate is {version} but the current terms are {current_v}, and the governing-terms wording is ambiguous about which version applies; a person should read it.",
                        used + ["governing_terms_clause"], [m.id for m in amb], version_in_force=None, current_version=current_v)
        if gov:  # all no
            c.version_in_force = current_v
            return _res("R2", "pass", f"Your certificate is {version} but the governing-terms clause says the current terms ({current_v}) apply, so {current_v} is checked.",
                        used + ["governing_terms_clause"], [m.id for m in gov], version_in_force=current_v, current_version=current_v)
        c.mark_missing("governing_terms_clause", "A clause saying which terms version governs (usually in the current terms or on the certificate).")
        return _res("R2", "unknown", f"Your certificate is Licence Terms {version} but the current terms are {current_v}, and no clause in your documents says which version governs. A person should check the licensor's terms.",
                    used + ["governing_terms_clause"], version_in_force=None, current_version=current_v)
    return _res("R2", "pass", f"Your licence is under Licence Terms {version}" + (f" and the current terms are the same version" if current_v else "") + (f" (purchased {_fmt_date(purchase)})." if purchase else "."),
                used + (["terms_version"] if current_v else []), version_in_force=version, current_version=current_v)


def _doc_type_of(t: FactTable, doc_id: Optional[str]) -> Optional[str]:
    for f in t.facts:
        for s in f.sources:
            if s.doc_id == doc_id:
                return s.doc_type
    return None


def _doc_label_by_doc(t: FactTable, doc_id: Optional[str]) -> str:
    for f in t.facts:
        for s in f.sources:
            if s.doc_id == doc_id:
                return {"licence_certificate": "your certificate", "licensor_terms": f"terms {t.value('terms_version') or ''}".strip()}.get(s.doc_type, s.doc_filename)
    return "a document"


def rule_permitted_use(c: _Ctx) -> RuleResult:
    t = c.table
    version = getattr(c, "version_in_force", None)
    r2 = c.results.get("R2")
    if r2 and r2.status == "unknown":
        return _res("R3", "unknown", "The licence version in force is unresolved (see R2), so the permitted-use wording cannot be chosen.", [])
    if not version:
        return _res("R3", "fail", "No licence version could be determined (see R2), so no permitted-use wording can be checked.", [], missing=["licence_version"])
    monet = c.actual_use["monetised"]
    if monet is None:
        c.mark_missing("monetised_on_publish", "Whether the video was monetised when published (video export or the form).", "dates")
        return _res("R3", "fail", "We don't know whether the video was monetised when published. Upload the video export or answer the question in the form.",
                    ["monetised_on_publish"], missing=["monetised_on_publish"])
    tier = t.value("licence_tier")
    permitted = [f for f in t.starting_with("permitted_use[") if c.fact_version(f) == version]
    excluded = [f for f in t.starting_with("excluded_use[") if c.fact_version(f) == version]
    if not permitted and not excluded:
        c.mark_missing(f"permitted_use[{version}]", f"The permitted-use wording of Licence Terms {version} (certificate or archived terms).", "clauses")
        return _res("R3", "fail", f"Licence Terms {version} governs, but none of your documents contains the {version} permitted-use wording. Upload the certificate or the archived {version} terms.",
                    [], missing=[f"permitted_use[{version}]"], version=version)
    use_words = ("monetised" if monet else "non-monetised") + " video on " + (c.actual_use["platform"] or "the platform")
    used = [f.key for f in permitted + excluded] + (["monetised_on_publish"] if t.has("monetised_on_publish") else ["stated_monetised"]) + (["licence_tier"] if tier else [])
    mids: list[str] = []
    excl_hit, excl_amb, perm_hit, perm_amb = [], [], [], []
    for f in excluded:
        m = c.mapping("excluded_use_applies_to_actual_use", f.key)
        if m is None:
            continue
        mids.append(m.id)
        (excl_hit if m.result == "yes" else excl_amb if m.result == "ambiguous" else []).append((f, m))
    for f in permitted:
        m = c.mapping("permitted_use_covers_actual_use", f.key)
        if m is None:
            continue
        mids.append(m.id)
        (perm_hit if m.result == "yes" else perm_amb if m.result == "ambiguous" else []).append((f, m))
    if excl_hit:
        f, m = excl_hit[0]
        return _res("R3", "fail", f"{_doc_label(f).capitalize()}{_clause(f)} ({version}) says “{_short(f.quote)}”, which excludes your {use_words} for a {tier or 'this'} licence (3 of 3 mapping runs agreed).",
                    used, mids, version=version, excluded_by=f.key, actual_use=c.actual_use)
    if excl_amb or perm_amb:
        f, m = (excl_amb + perm_amb)[0]
        return _res("R3", "unknown", f"Permitted-use wording is ambiguous for your actual use; a person should read {_doc_label(f)}{_clause(f)} ({version}): “{_short(f.quote)}”. The three mapping runs did not agree.",
                    used, mids, version=version, ambiguous=f.key, actual_use=c.actual_use)
    if perm_hit:
        f, m = perm_hit[0]
        return _res("R3", "pass", f"{_doc_label(f).capitalize()}{_clause(f)} ({version}) permits “{_short(f.quote)}”, which covers your {use_words} under a {tier or 'this'} licence (3 of 3 mapping runs agreed).",
                    used, mids, version=version, covered_by=f.key, actual_use=c.actual_use)
    f = (permitted or excluded)[0]
    return _res("R3", "fail", f"No permitted-use clause of Licence Terms {version} covers your {use_words} for a {tier or 'this'} licence; {_doc_label(f)}{_clause(f)} says “{_short(f.quote)}” (3 of 3 mapping runs agreed).",
                used, mids, version=version, not_covered=True, actual_use=c.actual_use)


def _short(q: str, n: int = 140) -> str:
    q = re.sub(r"\s+", " ", q).strip()
    return q if len(q) <= n else q[: n - 1].rstrip() + "…"


def rule_grant_email(c: _Ctx) -> RuleResult:
    t = c.table
    grant = t.get("grant_statement")
    r3 = c.results.get("R3")
    if not grant or grant.status != "confirmed_by_document":
        return _res("R4", "not_applicable", "No dated permission from the licensor (email) is among your documents.", [])
    if r3 and r3.status == "pass":
        return _res("R4", "not_applicable", "The licence terms already cover the use (R3), so the licensor's email is not needed.", ["grant_statement"])
    used = ["grant_statement", "email_date", "publish_date"]
    email_date = t.value("email_date")
    publish = t.value("publish_date")
    if not email_date:
        c.mark_missing("email_date", "The date of the licensor's email.", "dates")
        return _res("R4", "fail", "The licensor's email carries no readable date, so it cannot be placed before or after publication.", used, missing=["email_date"])
    if not publish:
        c.mark_missing("publish_date", "The publish date of the video (video export).", "dates")
        return _res("R4", "fail", "The video's publish date is missing, so the email cannot be compared with it. Upload the video export.", used, missing=["publish_date"])
    monet_on_publish = t.value("monetised_on_publish")
    mstart = t.value("monetisation_start_date")
    reference, ref_label = publish, "published"
    if monet_on_publish is False and mstart:
        reference, ref_label = mstart, "started monetisation"
        used.append("monetisation_start_date")
    matched = t.value("matched_work_title")
    gtitle = t.value("granted_work_title")
    m = c.mapping("grant_covers_actual_use", grant.key)
    mids = [m.id] if m else []
    if gtitle:
        used.append("granted_work_title")
    if parse_date(email_date) > parse_date(reference):
        return _res("R4", "fail", f"The licensor's permission is dated {_fmt_date(email_date)}, after you {ref_label} on {_fmt_date(reference)}; it may help going forward but does not show the use was licensed when the claim arose.",
                    used, mids, email_after_publish=True, reference_date=reference)
    if gtitle and matched and not titles_match(gtitle, matched):
        return _res("R4", "fail", f"The licensor's email refers to “{gtitle}”, not the matched work “{matched}”.", used, mids)
    if m is None or m.result == "ambiguous":
        return _res("R4", "unknown", f"The licensor's email of {_fmt_date(email_date)} is dated before publication, but its wording is ambiguous about whether it covers your use; a person should read it.", used, mids)
    if m.result == "no":
        return _res("R4", "fail", f"The licensor's email of {_fmt_date(email_date)} does not cover your actual use (3 of 3 mapping runs agreed).", used, mids)
    return _res("R4", "pass", f"The licensor's email of {_fmt_date(email_date)} says “{_short(grant.quote)}” and is dated before you {ref_label} on {_fmt_date(reference)}, so the use was permitted when the claim arose (3 of 3 mapping runs agreed).",
                used, mids, grant_used=True, reference_date=reference)


def rule_claimant_chain(c: _Ctx) -> RuleResult:
    t = c.table
    claimant = t.value("claimant_name")
    if not claimant:
        c.mark_missing("claimant_name", "The claim notice should name the claimant.")
        return _res("R5", "fail", "No notice names the claimant.", ["claimant_name"], missing=["claimant_name"])
    licensor = t.value("licensor_name")
    admin = t.value("content_id_administrator_name") or t.value("administrator_name")
    admin_key = "content_id_administrator_name" if t.has("content_id_administrator_name") else "administrator_name"
    if licensor and names_match(claimant, licensor):
        return _res("R5", "pass", f"The claimant, {claimant}, is your licensor, so this is a licensed-use conflict inside the licence chain.", ["claimant_name", "licensor_name"], classification="licensor_direct")
    if admin and names_match(claimant, admin):
        af = t.get(admin_key)
        return _res("R5", "pass", f"{_doc_label(af).capitalize()} says “{_short(af.quote)}”, so the claimant {claimant} is the licensor's administrator: a licensed-use conflict inside the licence chain.",
                    ["claimant_name", admin_key], classification="licensed_use_conflict")
    if not licensor and not admin:
        c.mark_missing("content_id_administrator_name", f"The licensor's track page or terms naming {claimant} as its administrator.")
    return _res("R5", "unknown", f"We can't connect the claimant, {claimant}, to your licensor{(' ' + licensor) if licensor else ''}: no document names it as the licensor's administrator. This may be an ownership question.",
                ["claimant_name"] + (["licensor_name"] if licensor else []) + ([admin_key] if admin else []), unrelated_claimant=True)


def _to_seconds(s: str) -> Optional[int]:
    m = re.match(r"^\s*(\d+):(\d{2})(?::(\d{2}))?\s*$", s or "")
    if not m:
        return None
    parts = [int(p) for p in m.groups() if p is not None]
    return parts[0] * 3600 + parts[1] * 60 + parts[2] if len(parts) == 3 else parts[0] * 60 + parts[1]


def rule_segment(c: _Ctx) -> RuleResult:
    t = c.table
    seg, dur = t.value("matched_segment"), t.value("duration")
    if not seg or not dur:
        return _res("R6", "not_applicable", "Segment check skipped: matched segment or video duration not available.", [])
    parts = re.split(r"\s*[–—-]\s*", str(seg))
    end = _to_seconds(parts[-1]) if len(parts) >= 2 else None
    d = _to_seconds(str(dur))
    if end is None or d is None:
        return _res("R6", "not_applicable", "Segment check skipped: could not read the times.", ["matched_segment", "duration"])
    if end <= d:
        return _res("R6", "pass", f"The matched segment {seg} falls inside the video duration {dur}.", ["matched_segment", "duration"])
    return _res("R6", "unknown", f"The matched segment {seg} ends after the video duration {dur}; the match may refer to a different upload. This check never blocks.", ["matched_segment", "duration"])


# ----------------------------------------------------------------------------- R7 components
def _comp(c: _Ctx, cid: str, label: str, status: str, rules: list[str], facts: list[str], explanation: str) -> StatementComponent:
    return StatementComponent(id=cid, label=label, status=status, rule_ids=rules, fact_keys=facts, sentence_id=f"component:{cid}", explanation=explanation)


def _licence_component_status(c: _Ctx) -> tuple[str, list[str], str]:
    r1, r3, r4 = c.results["R1"], c.results["R3"], c.results["R4"]
    if r1.status == "fail":
        return "unknown", ["R1"], r1.explanation
    if r3.status == "pass":
        return "supported", ["R3", "R1"], r3.explanation
    if r4.status == "pass":
        return "supported", ["R4", "R3", "R1"], r4.explanation
    if r3.status == "unknown" or r4.status == "unknown" or r1.status == "unknown":
        rr = r4 if r4.status == "unknown" else r3 if r3.status == "unknown" else r1
        return "unknown", [rr.rule_id], rr.explanation
    expl = r3.explanation + (" " + r4.explanation if r4.status == "fail" else "")
    return "not_supported", ["R3", "R4"], expl


def _in_force_status(c: _Ctx) -> tuple[str, list[str], str]:
    t, r2, r4 = c.table, c.results["R2"], c.results["R4"]
    if r4.status == "pass":
        return "supported", ["R4", "R2"], r4.explanation
    if r2.status == "unknown":
        return "unknown", ["R2"], r2.explanation
    if r2.status == "fail":
        return "not_supported", ["R2"], r2.explanation
    purchase = t.value("purchase_date") or t.value("issue_date")
    publish = t.value("publish_date")
    if not publish:
        c.mark_missing("publish_date", "The publish date of the video (video export).", "dates")
        return "not_supported", ["R2"], "The video's publish date is missing, so we cannot show the licence was in force when you published. Upload the video export."
    if not purchase:
        c.mark_missing("purchase_date", "The purchase date (receipt or certificate).", "dates")
        return "not_supported", ["R2"], "No purchase or issue date was found, so we cannot show the licence was in force when you published."
    if parse_date(purchase) <= parse_date(publish):
        return "supported", ["R2"], f"{r2.explanation} You purchased on {_fmt_date(purchase)} and published on {_fmt_date(publish)}, so the licence was in force when you published."
    return "not_supported", ["R2"], f"You purchased on {_fmt_date(purchase)}, after publishing on {_fmt_date(publish)}, so the licence was not in force when you published."


def _chain_status(c: _Ctx) -> tuple[str, list[str], str]:
    r5 = c.results["R5"]
    return {"pass": "supported", "fail": "not_supported"}.get(r5.status, "unknown"), ["R5"], r5.explanation


def _work_status(c: _Ctx) -> tuple[str, list[str], str]:
    r1 = c.results["R1"]
    return {"pass": "supported", "fail": "not_supported" if r1.data.get("missing") else "unknown"}.get(r1.status, "unknown"), ["R1"], r1.explanation


def build_components(c: _Ctx, step: str) -> list[StatementComponent]:
    t = c.table
    lic = _licence_component_status(c)
    inf = _in_force_status(c)
    chain = _chain_status(c)
    lic_facts = [k for k in ("permitted_use", "grant_statement", "email_date", "licence_tier") if t.has(k)] + [f.key for f in t.starting_with("permitted_use[")][:3]
    if step in ("dispute", "appeal"):
        return [
            _comp(c, "S-D1", "I hold a licence or permission that covers this use of the content in this video", lic[0], lic[1], c.results["R3"].facts_used + c.results["R4"].facts_used, lic[2]),
            _comp(c, "S-D2", "The licence was in force when the video was published", inf[0], inf[1], c.results["R2"].facts_used + ["publish_date"], inf[2]),
            _comp(c, "S-D3", "The claimant is the copyright owner or their authorised representative for this content", chain[0], chain[1], c.results["R5"].facts_used, chain[2]),
        ]
    work = _work_status(c)
    cn1_ok = t.has("video_id") and (t.has("video_title") or t.has("platform_case_id"))
    if not cn1_ok:
        c.mark_missing("video_id", "The removal notice or video export identifying the removed video.")
    cn3_missing = [k for k, lbl in (("stated_name", "name"), ("stated_address", "postal address"), ("stated_phone", "phone number")) if not t.has(k)]
    for k in cn3_missing:
        c.mark_missing(k, "Required by the counter-notice format; fill it in the form.", "about_you")
    return [
        _comp(c, "CN1", "Identification of the material removed and where it appeared before removal", "supported" if cn1_ok else "not_supported", ["R0"],
              [k for k in ("video_id", "video_title", "platform_case_id", "matched_work_title", "matched_segment") if t.has(k)],
              "The removal notice identifies the video and the matched work." if cn1_ok else "No document identifies the removed video (video ID plus title or case ID)."),
        _comp(c, "CN2a", "(a) I hold a licence or permission for this work", lic[0], lic[1], c.results["R3"].facts_used + c.results["R4"].facts_used, lic[2]),
        _comp(c, "CN2b", "(b) from the owner or their representative", chain[0], chain[1], c.results["R5"].facts_used, chain[2]),
        _comp(c, "CN2c", "(c) that was in force when I published", inf[0], inf[1], c.results["R2"].facts_used + ["publish_date"], inf[2]),
        _comp(c, "CN2d", "(d) for the same work that was matched", work[0], work[1], c.results["R1"].facts_used, work[2]),
        _comp(c, "CN3", "My name, postal address and telephone number", "supported" if not cn3_missing else "not_supported", [],
              ["stated_name", "stated_address", "stated_phone"],
              "Provided in the form (stated by you)." if not cn3_missing else "Missing from the form: " + ", ".join({"stated_name": "name", "stated_address": "postal address", "stated_phone": "phone number"}[k] for k in cn3_missing) + "."),
    ]


def components_status(c: _Ctx, comps: list[StatementComponent], adviser_triggers: list[str]) -> str:
    if adviser_triggers or any(x.status == "unknown" for x in comps):
        return "needs_adviser"
    if any(x.status == "not_supported" for x in comps):
        return "evidence_gap"
    return "evidence_ready"


def rule_abstain(c: _Ctx) -> RuleResult:
    triggers: list[str] = []
    used: list[str] = []
    if c.inp.abstain.fair_use:
        triggers.append("you are relying on fair use, commentary or parody, which NoticeGuard does not assess")
    if c.inp.abstain.ownership:
        triggers.append("you say you created the work yourself and the claimant is wrong about ownership; ownership questions need a person")
    for f in c.table.conflicting():
        triggers.append(f"your documents conflict on {f.key.replace('_', ' ')}: {f.note or ''}".rstrip(": "))
        used.append(f.key)
    r1 = c.results.get("R1")
    if r1 and r1.status == "fail" and r1.data.get("title_mismatch"):
        triggers.append("the claim is for a different work than your licence covers")
    r5 = c.results.get("R5")
    if r5 and r5.status == "unknown":
        triggers.append("the claimant cannot be connected to your licensor (possible ownership question)")
    r0 = c.results.get("R0")
    if r0 and r0.status == "fail":
        triggers.append(r0.explanation.rstrip("."))
    amb = [r for r in c.results.values() if r.status == "unknown" and r.rule_id in ("R2", "R3", "R4")]
    for r in amb:
        triggers.append(f"{r.rule_name}: {r.explanation.rstrip('.')}")
    c.adviser_triggers = triggers
    if triggers:
        return _res("R10", "fail", "Needs an adviser because " + "; ".join(triggers) + ".", used, triggers=triggers)
    return _res("R10", "pass", "No abstain trigger fired: no fair-use or ownership flag, no conflicting facts, no ambiguous mapping.", used, triggers=[])


# ----------------------------------------------------------------------------- gap fixes
def build_gap_fixes(c: _Ctx, comps: list[StatementComponent]) -> list[GapFix]:
    t = c.table
    fixes: list[GapFix] = []
    r2, r3, r4, r5 = c.results["R2"], c.results["R3"], c.results["R4"], c.results["R5"]
    publish = t.value("publish_date")
    claimant = t.value("claimant_name") or "the claimant"
    n = 0

    def add(component: str, needed: str, types: list[str], how: str):
        nonlocal n
        n += 1
        fixes.append(GapFix(component=component, needed=needed, example_document_types=types, how_to_get=how, sentence_id=f"gap:{n}"))

    for comp in comps:
        if comp.status == "supported":
            continue
        cid = comp.id
        if cid in ("S-D1", "CN2a") and comp.status == "not_supported":
            if r3.data.get("missing") == ["monetised_on_publish"]:
                add(cid, "Whether the video was monetised when it was published.", ["video_metadata"],
                    "Export the video details from the platform's studio page, or answer the monetisation question in the form.")
            elif r3.data.get("missing"):
                add(cid, f"The permitted-use wording of Licence Terms {r3.data.get('version') or r2.data.get('version_in_force') or ''}.".replace("  ", " "), ["licence_certificate", "licensor_terms"],
                    "Find the certificate attached to your purchase email, or the archived terms of that version on the licensor's site.")
            elif r4.status == "fail" and r4.data.get("email_after_publish"):
                add(cid, f"A grant dated on or before {_fmt_date(r4.data.get('reference_date') or publish)}.", ["licensor_email", "licence_certificate"],
                    "Check your inbox for an earlier reply from the licensor. Alternatively: remove or replace the track, or ask the claimant to retract.")
            else:
                add(cid, f"Any document from the licensor, dated on or before {_fmt_date(publish) if publish else 'your publish date'}, that grants monetised use of this track on your channel.",
                    ["licensor_email", "licence_certificate"],
                    "Check your inbox for support replies from the licensor before the publish date; check your account page for an upgraded (Pro) licence.")
        elif cid in ("S-D2", "CN2c") and comp.status == "not_supported":
            if not t.has("publish_date"):
                add(cid, "The publish date of the video.", ["video_metadata"], "Export the video details from the platform's studio page.")
            elif not (t.has("purchase_date") or t.has("issue_date")):
                add(cid, "The purchase or issue date of your licence.", ["receipt", "licence_certificate"], "Find the order confirmation email or the certificate.")
            elif r2.data.get("missing"):
                add(cid, "The licence terms version your purchase is under.", ["licence_certificate", "receipt"], "The certificate attached to your purchase email states the version.")
            else:
                add(cid, f"A licence or grant dated on or before {_fmt_date(publish)}.", ["licensor_email", "licence_certificate"], "Alternatively: remove or replace the track, or ask the claimant to retract.")
        elif cid in ("S-D3", "CN2b") and comp.status != "supported":
            add(cid, f"The licensor's track page or terms naming {claimant} as its administrator, or an email from the licensor confirming {claimant} administers this track.",
                ["track_page", "licensor_terms", "licensor_email"], "Open the track's page on the licensor's site, or email the licensor's support with the claim reference.")
        elif cid == "CN1" and comp.status == "not_supported":
            add(cid, "The removal notice identifying the removed video.", ["removal_notice", "video_metadata"], "Find the platform's removal email or the video export.")
        elif cid == "CN3" and comp.status == "not_supported":
            add(cid, "Fill in your name, postal address and phone number in the form (these are required by the counter-notice format).", [], "Use the About you form; nothing is filed by NoticeGuard.")
        elif cid == "CN2d" and comp.status == "not_supported":
            add(cid, "A licence document naming the work that was matched.", ["licence_certificate", "receipt"], "Find the certificate or receipt for the track named in the claim.")
    return fixes


# ----------------------------------------------------------------------------- verdict text
def verdict_explanation(c: _Ctx, verdict: str, comps: list[StatementComponent], step: str, routes: list[Route]) -> str:
    step_word = STEP_LABELS[step]
    if verdict == "needs_adviser":
        return ("Your documents raise a question NoticeGuard does not decide: " + "; ".join(c.adviser_triggers) +
                ". A person (for example a university IP clinic or a digital-rights adviser) should look at this before you take any step. Nothing here says you are wrong; it says the paperwork alone does not settle it.")
    if verdict == "evidence_gap":
        failed = [x for x in comps if x.status == "not_supported"]
        return (f"Your documents do not yet support every part of the statement you would make in a {step_word}. Not supported: " +
                "; ".join(f"“{x.label}”" for x in failed) + ". " + " ".join(x.explanation for x in failed[:2]) +
                " The list below says exactly which document would close the gap.")
    parts = [x.explanation for x in comps if x.status == "supported"][:3]
    return (f"Every component of the statement you would make in a {step_word} is confirmed by your documents. " + " ".join(parts) +
            " Confirmed by document means the documents are consistent with each other; NoticeGuard has not checked that they are authentic.")


# ----------------------------------------------------------------------------- deadlines
def build_deadlines(c: _Ctx) -> list[Deadline]:
    out: list[Deadline] = []
    for i, f in enumerate(c.table.all("deadline_date")):
        if f.status != "confirmed_by_document" or not f.sources:
            continue
        if getattr(c, "latest_notice_doc", None) and f.sources[0].doc_id != c.latest_notice_doc:
            continue  # only deadlines stated by the latest-stage notice are current
        d = parse_date(f.value)
        if not d:
            continue
        out.append(Deadline(label=f"Deadline stated in {f.sources[0].doc_filename}", date=d.isoformat(), days_remaining=(d - c.today).days,
                            source_fact_key="deadline_date", sentence_id=f"deadline:{i + 1}"))
    return out


# ----------------------------------------------------------------------------- main entry
def run_rules(inp: RulesInput) -> RulesOutput:
    c = _Ctx(inp)
    step = inp.step if inp.step in ("dispute", "appeal", "counter_notice") else "dispute"
    for rid, fn in (("R0", rule_stage), ("R1", rule_work_identity), ("R2", rule_version_in_force), ("R3", rule_permitted_use),
                    ("R4", rule_grant_email), ("R5", rule_claimant_chain), ("R6", rule_segment)):
        c.results[rid] = fn(c)
    r10 = rule_abstain(c)
    comps = build_components(c, step)
    c.results["R7"] = _res("R7", "pass" if all(x.status == "supported" for x in comps) else "fail",
                           "; ".join(f"{x.id} {x.status.replace('_', ' ')}" for x in comps), [k for x in comps for k in x.fact_keys])
    verdict = components_status(c, comps, c.adviser_triggers)
    c.results["R8"] = _res("R8", "pass", f"Verdict: {verdict.replace('_', ' ')} for a {STEP_LABELS[step]}.", [], verdict=verdict)

    # step evidence for every step (ignores stage availability; used by the status strip)
    step_ev: list[StepEvidence] = []
    per_step_comps: dict[str, list[StatementComponent]] = {}
    for s in ("dispute", "appeal", "counter_notice"):
        cs = comps if s == step else build_components(c, s)
        per_step_comps[s] = cs
        step_ev.append(StepEvidence(step=s, available=(s in c.available), evidence_status=components_status(c, cs, [t for t in c.adviser_triggers if "not available at your current stage" not in t])))

    r5_pass = c.results["R5"].status == "pass"
    non_stage_triggers = [t for t in c.adviser_triggers if "not available at your current stage" not in t]

    def status_for(comp_ids: list[str]) -> str:
        pool = per_step_comps["counter_notice"] + per_step_comps["dispute"]
        sel = [x for x in pool if x.id in comp_ids]
        return components_status(c, sel, non_stage_triggers)

    routes = select_routes(c.stage, c.available, r5_pass, c.table.value("claimant_name") or "", c.table.value("licensor_name") or "",
                           status_for, ["S-D1", "S-D2", "S-D3"], ["CN2a", "CN2b", "CN2c", "CN2d"], ["CN1", "CN2a", "CN2b", "CN2c", "CN2d", "CN3"], step)
    c.results["R9"] = _res("R9", "pass", "Routes listed lowest-risk first: " + "; ".join(f"{r.rank}. {r.title} ({r.evidence_status.replace('_', ' ')})" for r in routes), [])
    c.results["R10"] = r10
    gap_fixes = build_gap_fixes(c, comps) if verdict in ("evidence_gap", "needs_adviser") else []
    statement = Statement(step=step, text=DISPUTE_STATEMENT if step != "counter_notice" else CN_STATEMENT, components=comps,
                          consequence={"dispute": DISPUTE_CONSEQUENCE, "appeal": APPEAL_CONSEQUENCE, "counter_notice": CN_CONSEQUENCE}[step])
    ordered = [c.results[r["id"]] for r in RULE_DEFS]
    return RulesOutput(rules_version=RULES_VERSION, stage=c.stage, available_steps=c.available, chosen_step=step, verdict=verdict,
                       verdict_explanation=verdict_explanation(c, verdict, comps, step, routes), statement=statement, rule_results=ordered,
                       routes=routes, gap_fixes=gap_fixes, step_evidence=step_ev, deadlines=build_deadlines(c),
                       facts=list(inp.facts) + c.extra_stated + c.missing, actual_use=c.actual_use)
