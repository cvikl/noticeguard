"""Pydantic models shared across the NoticeGuard pipeline."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

DocType = Literal[
    "claim_notice", "dispute_response", "appeal_response", "removal_notice", "strike_notice",
    "receipt", "licence_certificate", "licensor_terms", "track_page", "licensor_email",
    "video_metadata", "other",
]
DOC_TYPES: list[str] = list(DocType.__args__)  # type: ignore[attr-defined]

Step = Literal["dispute", "appeal", "counter_notice"]
STEPS: list[str] = ["dispute", "appeal", "counter_notice"]
Stage = Literal["claim", "dispute", "appeal", "removed_with_strike", "unknown"]
Verdict = Literal["evidence_ready", "evidence_gap", "needs_adviser"]
FactStatus = Literal["confirmed_by_document", "stated_by_you", "missing", "conflicting"]
RuleStatus = Literal["pass", "fail", "unknown", "not_applicable"]
ComponentStatus = Literal["supported", "not_supported", "unknown"]


class Document(BaseModel):
    id: str
    filename: str
    doc_type: str
    text: str
    lines: list[str]
    sha256: str


class Span(BaseModel):
    line_start: int  # 1-based
    line_end: int
    char_start: int  # offset into normalised text
    char_end: int
    matched_text: str
    exact: bool = True


class Extraction(BaseModel):
    """Raw fact as produced by the LLM for one document (before quote check)."""
    type: str
    value: Any = None
    quote: str = ""
    clause_ref: Optional[str] = None
    confidence_note: Optional[str] = None


class RejectedFact(BaseModel):
    doc_id: str
    doc_filename: str
    type: str
    value: Any = None
    quote: str = ""
    reason: str
    kind: str = "dropped_tag"  # dropped_tag | extraction_failed | unparseable


class Source(BaseModel):
    doc_id: str
    doc_filename: str
    doc_type: str
    quote: str
    line_start: int
    line_end: int
    char_start: int = 0
    char_end: int = 0
    clause_ref: Optional[str] = None
    exact: bool = True


class Fact(BaseModel):
    key: str
    value: Any = None
    status: FactStatus
    sources: list[Source] = Field(default_factory=list)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)  # for conflicting facts
    note: Optional[str] = None
    group: Optional[str] = None  # display grouping (e.g. "dates")

    @property
    def quote(self) -> str:
        return self.sources[0].quote if self.sources else ""

    @property
    def doc_id(self) -> Optional[str]:
        return self.sources[0].doc_id if self.sources else None


class MappingAnswer(BaseModel):
    covers: Literal["yes", "no", "unclear"]
    reason: str = ""
    raw: Optional[str] = None


class MappingRun(BaseModel):
    id: str
    question: str  # permitted_use_covers_actual_use | grant_covers_actual_use | governing_terms_selects_purchase_version
    fact_key: str
    clause_quote: str
    actual_use: dict[str, Any] = Field(default_factory=dict)
    answers: list[MappingAnswer] = Field(default_factory=list)
    result: Literal["yes", "no", "ambiguous"]
    doc_id: Optional[str] = None
    doc_filename: Optional[str] = None
    clause_ref: Optional[str] = None


class RuleResult(BaseModel):
    rule_id: str
    rule_name: str
    status: RuleStatus
    facts_used: list[str] = Field(default_factory=list)
    mapping_ids: list[str] = Field(default_factory=list)
    explanation: str
    data: dict[str, Any] = Field(default_factory=dict)


class StatementComponent(BaseModel):
    id: str
    label: str
    status: ComponentStatus
    rule_ids: list[str] = Field(default_factory=list)
    fact_keys: list[str] = Field(default_factory=list)
    sentence_id: str
    explanation: str = ""


class Statement(BaseModel):
    step: str
    text: str
    components: list[StatementComponent]
    consequence: Optional[str] = None


class Route(BaseModel):
    id: str
    rank: int
    title: str
    description: str
    step: Optional[str] = None  # the formal step this route corresponds to, if any
    evidence_status: str  # evidence_ready | evidence_gap | needs_adviser
    sentence_id: str
    is_chosen_step: bool = False


class GapFix(BaseModel):
    component: str
    needed: str
    example_document_types: list[str] = Field(default_factory=list)
    how_to_get: str
    sentence_id: str


class DraftSentence(BaseModel):
    id: str
    text: str
    citations: list[str] = Field(default_factory=list)
    fact_keys: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)


class PostCheck(BaseModel):
    passed: bool
    checked_tokens: list[str] = Field(default_factory=list)
    unsupported_tokens: list[str] = Field(default_factory=list)


class Draft(BaseModel):
    kind: str  # dispute | appeal | counter_notice
    header: str
    sentences: list[DraftSentence]
    text: str
    post_check: PostCheck
    withheld_reason: Optional[str] = None
    smoothed: bool = False


class ChainFact(BaseModel):
    fact_key: str
    value: Any = None
    status: str
    quote: str = ""
    doc_id: Optional[str] = None
    doc_filename: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    clause_ref: Optional[str] = None


class ChainNode(BaseModel):
    sentence_id: str
    text: str
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    rule_status: Optional[str] = None
    rule_logic: Optional[str] = None
    facts: list[ChainFact] = Field(default_factory=list)
    mapping_runs: list[MappingRun] = Field(default_factory=list)
    status: Optional[str] = None


class Deadline(BaseModel):
    label: str
    date: str
    days_remaining: int
    source_fact_key: str
    sentence_id: str


class StatedFields(BaseModel):
    name: str = ""
    address: str = ""
    phone: str = ""
    monetised: Literal["yes", "no", "unknown"] = "unknown"
    channel_name: str = ""


class AbstainFlags(BaseModel):
    fair_use: bool = False
    ownership: bool = False


class DocumentSummary(BaseModel):
    id: str
    filename: str
    doc_type: str
    lines: list[str]
    sha256: str
    extraction_failed: bool = False
    extraction_error: Optional[str] = None
    n_facts: int = 0


class StepEvidence(BaseModel):
    step: str
    available: bool
    evidence_status: str


class CaseResult(BaseModel):
    case_id: str
    rules_version: str
    stage: str
    available_steps: list[str]
    chosen_step: str
    verdict: Verdict
    verdict_explanation: str
    verdict_sentence_id: str = "verdict"
    claim_summary: list[dict[str, Any]] = Field(default_factory=list)  # sentences with ids
    statement: Statement
    facts: list[Fact]
    rejected_facts: list[RejectedFact]
    rule_results: list[RuleResult]
    routes: list[Route]
    gap_fixes: list[GapFix]
    draft: Optional[Draft] = None
    chain: dict[str, ChainNode]
    deadlines: list[Deadline]
    mapping_runs: list[MappingRun] = Field(default_factory=list)
    step_evidence: list[StepEvidence] = Field(default_factory=list)
    stated: StatedFields = Field(default_factory=StatedFields)
    abstain_flags: AbstainFlags = Field(default_factory=AbstainFlags)
    documents: list[DocumentSummary] = Field(default_factory=list)
    notes_ignored: bool = True
    llm: dict[str, Any] = Field(default_factory=dict)


class CaseDiff(BaseModel):
    verdict_before: str
    verdict_after: str
    changed_facts: list[dict[str, Any]] = Field(default_factory=list)
    changed_rule_results: list[dict[str, Any]] = Field(default_factory=list)
    added_documents: list[str] = Field(default_factory=list)
    summary: str = ""
