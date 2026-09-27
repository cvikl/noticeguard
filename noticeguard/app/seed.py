"""Populate the committed LLM cache for the demo document sets (Maya, Leo, Leo + email) and print the verdicts."""
from __future__ import annotations

import sys
from pathlib import Path

from .ingest import load_folder
from .llm import get_llm
from .main import DATA, DEMO_SETS
from .models import AbstainFlags
from .pipeline import new_state, run_case, run_extraction


def main() -> int:
    llm = get_llm()
    print(f"provider={llm.provider} model={llm.model} cache={llm.use_cache}")
    ok = True
    for name, spec in DEMO_SETS.items():
        docs = [d for f in spec["folders"] for d in load_folder(DATA / f)]
        state = new_state(docs, spec["step"], spec["stated"], AbstainFlags(), "")
        run_extraction(state, llm=llm)
        res = run_case(state, llm=llm)
        print(f"{name:10} stage={res.stage:20} verdict={res.verdict}")
        if name == "leo":
            email = load_folder(DATA / "leo_email")
            for d in email:
                state["documents"].append(d.model_dump())
            run_extraction(state, only_doc_ids=[d.id for d in email], llm=llm)
            res2 = run_case(state, llm=llm)
            print(f"{'leo+email':10} stage={res2.stage:20} verdict={res2.verdict}")
    print(f"live calls={llm.calls} cache hits={llm.cache_hits}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
