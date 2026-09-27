"""FastAPI app: API routes + static single-page frontend."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import store
from .ingest import load_folder, make_document
from .llm import LLMUnavailable, get_llm
from .models import DOC_TYPES, AbstainFlags, Document, StatedFields
from .pipeline import diff_results, new_state, run_case, run_extraction

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
DATA = ROOT / "data" / "synthetic"

app = FastAPI(title="NoticeGuard", version="0.1.0", docs_url="/api/docs", redoc_url=None)

DEMO_SETS = {
    "maya": {"folders": ["maya"], "step": "dispute", "stated": StatedFields(name="Maya Ortiz", address="", phone="", monetised="yes", channel_name="Maya Draws")},
    "leo": {"folders": ["leo"], "step": "counter_notice", "stated": StatedFields(name="Leo Marsh", address="22 Harbourside Walk, Bristol BS1 5UH, United Kingdom", phone="+44 117 496 0812", monetised="yes", channel_name="Leo Marsh Music")},
}


def _parse_json(s: Optional[str], model, default):
    if not s:
        return default
    try:
        return model(**json.loads(s))
    except Exception as e:
        raise HTTPException(400, f"invalid JSON for {model.__name__}: {e}")


def _llm_error(e: Exception) -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": "llm_unavailable", "detail": str(e),
                                                  "hint": "Set GEMINI_API_KEY or ANTHROPIC_API_KEY (see .env.example). The demo cases work offline from the committed cache."})


@app.get("/api/health")
def health():
    llm = get_llm()
    return {"ok": True, "provider": llm.provider, "model": llm.model, "cache": llm.use_cache}


@app.get("/api/doc-types")
def doc_types():
    return DOC_TYPES


@app.post("/api/cases")
async def create_case(files: list[UploadFile] = File(...), doc_types: str = Form("[]"), stated: str = Form(""), step: str = Form("dispute"),
                      abstain_flags: str = Form(""), notes: str = Form("")):
    types = json.loads(doc_types) if doc_types else []
    docs: list[Document] = []
    for i, f in enumerate(files):
        data = await f.read()
        dt = types[i] if i < len(types) and types[i] in DOC_TYPES else "other"
        docs.append(make_document(f.filename or f"upload_{i}", data, dt))
    st = _parse_json(stated, StatedFields, StatedFields())
    ab = _parse_json(abstain_flags, AbstainFlags, AbstainFlags())
    state = new_state(docs, step, st, ab, notes)
    try:
        run_extraction(state)
        result = run_case(state)
    except LLMUnavailable as e:
        return _llm_error(e)
    store.save_case(state["case_id"], state)
    return {"case_id": state["case_id"], "result": result.model_dump()}


@app.get("/api/cases/{case_id}")
def get_case(case_id: str):
    state = store.load_case(case_id)
    if not state:
        raise HTTPException(404, "case not found")
    return state["result"]


@app.post("/api/cases/{case_id}/documents")
async def add_documents(case_id: str, files: list[UploadFile] = File(...), doc_types: str = Form("[]")):
    state = store.load_case(case_id)
    if not state:
        raise HTTPException(404, "case not found")
    types = json.loads(doc_types) if doc_types else []
    added: list[Document] = []
    existing = {d["id"] for d in state["documents"]}
    for i, f in enumerate(files):
        data = await f.read()
        dt = types[i] if i < len(types) and types[i] in DOC_TYPES else "other"
        d = make_document(f.filename or f"upload_{i}", data, dt)
        if d.id in existing:
            continue
        added.append(d)
        state["documents"].append(d.model_dump())
    before = state.get("result")
    try:
        run_extraction(state, only_doc_ids=[d.id for d in added])
        result = run_case(state)
    except LLMUnavailable as e:
        return _llm_error(e)
    diff = diff_results(before, result, added)
    store.save_case(case_id, state)
    return {"case_id": case_id, "result": result.model_dump(), "diff": diff.model_dump()}


@app.post("/api/cases/{case_id}/step")
def change_step(case_id: str, payload: dict):
    state = store.load_case(case_id)
    if not state:
        raise HTTPException(404, "case not found")
    if payload.get("step") in ("dispute", "appeal", "counter_notice"):
        state["step"] = payload["step"]
    if payload.get("stated") is not None:
        state["stated"] = StatedFields(**payload["stated"]).model_dump()
    if payload.get("abstain_flags") is not None:
        state["abstain"] = AbstainFlags(**payload["abstain_flags"]).model_dump()
    before = state.get("result")
    # rules only: mappings are reused unless the stated monetisation changed (which changes the actual-use tuple)
    try:
        result = run_case(state, rerun_mappings=payload.get("stated") is not None)
    except LLMUnavailable as e:
        return _llm_error(e)
    store.save_case(case_id, state)
    return {"case_id": case_id, "result": result.model_dump(), "diff": diff_results(before, result, []).model_dump()}


@app.get("/api/cases/{case_id}/draft")
def get_draft(case_id: str):
    state = store.load_case(case_id)
    if not state:
        raise HTTPException(404, "case not found")
    r = state["result"]
    return {"draft": r.get("draft"), "verdict": r["verdict"]}


@app.get("/api/demo/{name}")
def demo(name: str, step: Optional[str] = None):
    if name not in DEMO_SETS:
        raise HTTPException(404, "unknown demo; use maya or leo")
    spec = DEMO_SETS[name]
    docs = [d for f in spec["folders"] for d in load_folder(DATA / f)]
    state = new_state(docs, step or spec["step"], spec["stated"], AbstainFlags(), "")
    try:
        run_extraction(state)
        result = run_case(state)
    except LLMUnavailable as e:
        return _llm_error(e)
    store.save_case(state["case_id"], state)
    return {"case_id": state["case_id"], "result": result.model_dump()}


@app.get("/api/demo-files/{name}")
def demo_files(name: str):
    """Serve a demo document so the UI can 'upload' it live (used for Leo's email)."""
    folder = {"leo_email": DATA / "leo_email"}.get(name)
    if not folder:
        raise HTTPException(404)
    files = [p for p in sorted(folder.iterdir()) if p.is_file()]
    return [{"filename": p.name, "text": p.read_text(errors="replace")} for p in files]


@app.get("/api/benchmark/results")
def benchmark_results():
    p = ROOT / "bench" / "results" / "latest.json"
    if not p.exists():
        return JSONResponse(status_code=404, content={"error": "no benchmark results yet; run `make bench`"})
    return json.loads(p.read_text())


@app.get("/api/benchmark/raw/{case}/{system}/{prompt}/{run}")
def benchmark_raw(case: str, system: str, prompt: str, run: str):
    p = ROOT / "bench" / "results" / "raw" / case / system / prompt / f"{run}.txt"
    if not p.exists() or not p.resolve().is_relative_to((ROOT / "bench" / "results" / "raw").resolve()):
        raise HTTPException(404)
    return FileResponse(p, media_type="text/plain; charset=utf-8")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/benchmark.html")
def benchmark_page():
    return FileResponse(STATIC / "benchmark.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
