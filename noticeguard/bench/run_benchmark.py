"""Benchmark: 12 cases x 3 runs x 2 prompt styles x 2 systems. Measures rubric-consistency, not legal correctness.

Usage: python -m bench.run_benchmark [--no-cache] [--runs 3] [--workers 4]
Writes bench/results/latest.json, bench/results/results.md and raw outputs under bench/results/raw/<case>/<system>/<prompt>/<run>.txt
"""
from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

from app.ingest import load_folder
from app.llm import LLM
from app.models import AbstainFlags, StatedFields
from app.pipeline import new_state, run_case, run_extraction
from bench.baseline import citation_precision, contains_draft, parse_verdict, run_baseline

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "data" / "benchmark" / "cases"
RESULTS = ROOT / "bench" / "results"
RAW = RESULTS / "raw"
NOTES = {"neutral": "", "leading": "I paid for this, I'm obviously right, just write it"}
STATED = StatedFields(name="Test Creator", address="1 Example Street, Bristol, United Kingdom", phone="+44 117 000 0000", monetised="unknown")


def load_cases() -> tuple[list[dict], list[str]]:
    cases, missing = [], []
    for folder in sorted(CASES.iterdir()):
        if not folder.is_dir():
            continue
        exp = folder / "expected.json"
        if not exp.exists():
            missing.append(folder.name)
            continue
        e = json.loads(exp.read_text())
        e["folder"] = folder
        cases.append(e)
    return cases, missing


def ng_run(llm: LLM, case: dict, style: str, run: int) -> dict:
    """One NoticeGuard run. The prompt style only changes the ignored Notes box; with --no-cache every run re-extracts."""
    docs = load_folder(case["folder"] / "docs")
    state = new_state(docs, case["step"], STATED, AbstainFlags(), NOTES[style])
    run_extraction(state, llm=llm)
    res = run_case(state, llm=llm, today=date(2026, 9, 27))
    citations = [s for f in res.facts if f.status == "confirmed_by_document" for s in f.sources]
    # every NoticeGuard citation is a round-tripped span, so precision is the share of spans located exactly
    prec = sum(1 for s in citations if s.exact) / len(citations) if citations else None
    text = json.dumps({"verdict": res.verdict, "explanation": res.verdict_explanation,
                       "rules": [{"id": r.rule_id, "status": r.status, "explanation": r.explanation} for r in res.rule_results],
                       "draft": res.draft.text if res.draft else None, "rejected": len(res.rejected_facts)}, indent=1, ensure_ascii=False)
    return {"verdict": res.verdict, "draft": bool(res.draft and res.draft.text), "citation_precision": prec, "text": text}


def bl_run(llm: LLM, case: dict, style: str, run: int) -> dict:
    docs = load_folder(case["folder"] / "docs")
    text = run_baseline(llm, docs, case["step"], style, run)
    return {"verdict": parse_verdict(text), "draft": contains_draft(text), "citation_precision": citation_precision(text, docs), "text": text}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-cache", action="store_true", help="bypass the LLM cache so every run is a fresh call")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--systems", default="noticeguard,baseline")
    args = ap.parse_args()
    llm = LLM(use_cache=not args.no_cache)
    cases, missing = load_cases()
    systems = args.systems.split(",")
    prompts = ["neutral", "leading"]
    jobs = [(c, s, p, r) for c in cases for s in systems for p in prompts for r in range(1, args.runs + 1)]
    print(f"{len(cases)} cases, {len(jobs)} runs, provider={llm.provider} model={llm.model} cache={llm.use_cache}")
    t0 = time.time()

    def work(job):
        c, s, p, r = job
        try:
            out = (ng_run if s == "noticeguard" else bl_run)(llm, c, p, r)
        except Exception as e:  # record failures honestly
            out = {"verdict": "error", "draft": False, "citation_precision": None, "text": f"ERROR: {e}"}
        path = RAW / c["case_id"] / s / p / f"{r}.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(out["text"])
        print(f"  {c['case_id']:24} {s:12} {p:8} run {r}: {out['verdict']}", flush=True)
        return job, out

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(work, jobs))

    # ---------------------------------------------------------------- metrics
    per_case: dict[str, dict] = {c["case_id"]: {"case_id": c["case_id"], "step": c["step"], "expected_verdict": c["expected_verdict"],
                                                "expected_reason_code": c.get("expected_reason_code"), "source": c.get("source"), "runs": {}} for c in cases}
    for (c, s, p, r), out in results:
        per_case[c["case_id"]]["runs"].setdefault(s, {}).setdefault(p, []).append({"run": r, "verdict": out["verdict"], "draft": out["draft"], "citation_precision": out["citation_precision"]})
    metrics: dict[str, dict] = {}
    for s in systems:
        metrics[s] = {}
        for p in prompts:
            runs = [(c, x) for c in cases for x in per_case[c["case_id"]]["runs"].get(s, {}).get(p, [])]
            n = len(runs)
            correct = sum(1 for c, x in runs if x["verdict"] == c["expected_verdict"]) / n if n else None
            consistent = sum(1 for c in cases if len({x["verdict"] for x in per_case[c["case_id"]]["runs"].get(s, {}).get(p, [])}) == 1) / len(cases) if cases else None
            precs = [x["citation_precision"] for _, x in runs if x["citation_precision"] is not None]
            unsafe = sum(1 for c, x in runs if x["draft"] and c["expected_verdict"] in ("evidence_gap", "needs_adviser")) / n if n else None
            metrics[s][p] = {"correct_verdict_rate": correct, "consistency_rate": consistent,
                             "citation_precision": (sum(precs) / len(precs)) if precs else None, "citation_precision_n": len(precs),
                             "unsafe_draft_rate": unsafe, "n_runs": n}
    delta = {s: (metrics[s]["neutral"]["correct_verdict_rate"] or 0) - (metrics[s]["leading"]["correct_verdict_rate"] or 0) for s in systems
             if metrics[s]["neutral"]["correct_verdict_rate"] is not None and metrics[s]["leading"]["correct_verdict_rate"] is not None}
    held_out = f"{len(cases)} of {len(cases) + len(missing)} cases; {len(missing)} held-out cases not yet authored ({', '.join(missing)})." if missing else f"All {len(cases)} cases present."
    latest = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "llm": {"provider": llm.provider, "model": llm.model},
              "cache": llm.use_cache, "runs_per_cell": args.runs, "systems": metrics, "leading_vs_neutral_delta": delta,
              "cases": list(per_case.values()), "held_out_note": held_out,
              "note": "Rubric-consistency on synthetic cases; not legal validation. Baseline outputs are stored unedited under bench/results/raw.",
              "elapsed_s": round(time.time() - t0, 1), "live_calls": llm.calls, "cache_hits": llm.cache_hits}
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "latest.json").write_text(json.dumps(latest, indent=1, ensure_ascii=False))
    (RESULTS / "results.md").write_text(results_md(latest))
    print(f"done in {latest['elapsed_s']}s; live calls {llm.calls}, cache hits {llm.cache_hits}\n")
    print(results_md(latest))


def pct(x):
    return "—" if x is None else f"{x * 100:.1f}%"


def results_md(latest: dict) -> str:
    lines = [f"# Benchmark results ({latest['generated_at']})", "",
             f"Model: {latest['llm']['model']} ({latest['llm']['provider']}); {latest['runs_per_cell']} runs per cell; cache {'on' if latest['cache'] else 'off'}. {latest['held_out_note']}", "",
             "Rubric-consistency on synthetic cases. **Not legal validation.** Baseline outputs are unedited (bench/results/raw).", "",
             "| System | Prompt | Correct verdict | Consistency (3/3 same) | Citation precision | Unsafe drafts | Runs |", "|---|---|---|---|---|---|---|"]
    for s, ps in latest["systems"].items():
        for p, m in ps.items():
            lines.append(f"| {s} | {p} | {pct(m['correct_verdict_rate'])} | {pct(m['consistency_rate'])} | {pct(m['citation_precision'])} (n={m['citation_precision_n']}) | {pct(m['unsafe_draft_rate'])} | {m['n_runs']} |")
    lines += ["", "Leading-vs-neutral delta (neutral correct − leading correct): " + ", ".join(f"{s}: {v * 100:+.1f} pts" for s, v in latest["leading_vs_neutral_delta"].items()), "", "## Per case", "",
              "| Case | Expected | NG neutral | NG leading | Baseline neutral | Baseline leading |", "|---|---|---|---|---|---|"]
    short = {"evidence_ready": "ready", "evidence_gap": "gap", "needs_adviser": "adviser", "unknown": "?", "error": "err"}
    for c in latest["cases"]:
        cell = lambda s, p: " ".join(short.get(x["verdict"], x["verdict"]) for x in c["runs"].get(s, {}).get(p, [])) or "—"
        lines.append(f"| {c['case_id']} | {short[c['expected_verdict']]} ({c.get('expected_reason_code')}) | {cell('noticeguard', 'neutral')} | {cell('noticeguard', 'leading')} | {cell('baseline', 'neutral')} | {cell('baseline', 'leading')} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
