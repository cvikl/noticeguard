"""Process-stage detection from notice facts (R0)."""
from __future__ import annotations

from typing import Optional

from ..facts import FactTable, parse_date

STAGE_ORDER = ["claim", "dispute", "appeal", "removed_with_strike"]
KIND_TO_STAGE = {"claim": "claim", "dispute_rejected": "dispute", "appeal_rejected": "removed_with_strike",
                 "removal": "removed_with_strike", "strike": "removed_with_strike"}
AVAILABLE = {"claim": ["dispute"], "dispute": ["appeal"], "appeal": [], "removed_with_strike": ["counter_notice"], "unknown": []}
NEXT_STEP_LABEL = {"dispute": "a dispute", "appeal": "an appeal", "counter_notice": "a counter-notice"}


def detect_stage(table: FactTable) -> tuple[str, list[str], list[str], Optional[str]]:
    """Return (stage, available_steps, fact_keys_used, latest_notice_doc_id)."""
    kinds = [f for f in table.all("notice_kind") if f.status == "confirmed_by_document"]
    if not kinds:
        return "unknown", [], [], None
    best_stage, best_rank, best_doc = "unknown", -1, None
    for f in kinds:
        stage = KIND_TO_STAGE.get(str(f.value), None)
        if stage is None:
            continue
        rank = STAGE_ORDER.index(stage)
        if rank > best_rank:
            best_stage, best_rank, best_doc = stage, rank, f.sources[0].doc_id if f.sources else None
    return best_stage, list(AVAILABLE.get(best_stage, [])), ["notice_kind"], best_doc


def stage_label(stage: str) -> str:
    return {"claim": "Claim", "dispute": "Dispute rejected", "appeal": "Appeal", "removed_with_strike": "Removed with strike",
            "unknown": "Unknown"}.get(stage, stage)
