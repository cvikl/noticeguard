"""SQLite persistence of cases. One JSON blob per case; no accounts, no auth."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("NOTICEGUARD_DB", ROOT / "data" / "cases.db"))
_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.execute("CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, created REAL, updated REAL, state TEXT)")
    return c


def save_case(case_id: str, state: dict[str, Any]) -> None:
    with _lock:
        c = _conn()
        now = time.time()
        c.execute("INSERT INTO cases(id, created, updated, state) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET updated=excluded.updated, state=excluded.state",
                  (case_id, now, now, json.dumps(state, ensure_ascii=False)))
        c.commit()
        c.close()


def load_case(case_id: str) -> Optional[dict[str, Any]]:
    with _lock:
        c = _conn()
        row = c.execute("SELECT state FROM cases WHERE id=?", (case_id,)).fetchone()
        c.close()
    return json.loads(row[0]) if row else None


def list_cases(limit: int = 50) -> list[dict[str, Any]]:
    with _lock:
        c = _conn()
        rows = c.execute("SELECT id, created, updated FROM cases ORDER BY updated DESC LIMIT ?", (limit,)).fetchall()
        c.close()
    return [{"id": r[0], "created": r[1], "updated": r[2]} for r in rows]
