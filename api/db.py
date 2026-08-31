"""
Persistence for the range dashboard.

Two things live here, in one SQLite file:

  * runs   -- every scan we perform, with its verdict and per-tool findings,
              so the dashboard can show a history / audit trail.
  * pins   -- the SHA-256 fingerprint each tool was last seen with, so a
              later scan can detect a tool that silently mutated (rug pull).

Keeping pins in the same store as runs means rug-pull detection survives
restarts and is visible alongside the history that produced it.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("api/range.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                scenario    TEXT    NOT NULL,
                server      TEXT    NOT NULL,
                started_at  TEXT    NOT NULL,
                overall     TEXT    NOT NULL,
                tool_count  INTEGER NOT NULL,
                flagged     INTEGER NOT NULL,
                rug_pull    INTEGER NOT NULL,
                tools_json  TEXT    NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pins (
                tool_name  TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ---- runs -----------------------------------------------------------------

def save_run(scenario, server, started_at, overall, tools):
    flagged = sum(1 for t in tools if t["verdict"] != "clean")
    rug_pull = 1 if any(t.get("pin", "").startswith("CHANGED") for t in tools) else 0
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO runs
              (scenario, server, started_at, overall, tool_count, flagged, rug_pull, tools_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (scenario, server, started_at, overall, len(tools), flagged, rug_pull,
             json.dumps(tools)),
        )
        return cur.lastrowid


def list_runs(limit=50):
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, scenario, server, started_at, overall, tool_count, flagged, rug_pull
            FROM runs ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_run(run_id):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        run = dict(row)
        run["tools"] = json.loads(run.pop("tools_json"))
        return run


# ---- pins (rug-pull detection) -------------------------------------------

def get_pin(tool_name):
    with _connect() as conn:
        row = conn.execute(
            "SELECT fingerprint FROM pins WHERE tool_name = ?", (tool_name,)
        ).fetchone()
        return row["fingerprint"] if row else None


def set_pin(tool_name, fingerprint):
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO pins (tool_name, fingerprint, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(tool_name) DO UPDATE SET
              fingerprint = excluded.fingerprint,
              updated_at  = excluded.updated_at
            """,
            (tool_name, fingerprint, now_iso()),
        )


def reset_pins():
    """Clear all pins — used by the dashboard's 'reset baseline' control."""
    with _connect() as conn:
        conn.execute("DELETE FROM pins")
