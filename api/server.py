"""
MCP Attack & Defense Range -- dashboard backend.

Exposes the shipped signature scanner as a live service:

  GET  /api/scenarios        -- attack servers available to scan
  GET  /api/runs             -- scan history (most recent first)
  GET  /api/runs/{id}        -- one run, with per-tool findings
  POST /api/pins/reset       -- clear the rug-pull baseline
  WS   /ws/scan/{scenario}   -- run a scan, stream events live, persist result

The scan itself is the real detection engine (scanner.rules + scanner.pinning),
wrapped for streaming in api.scan_stream. No detection logic lives here.
"""

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import db
from api.scan_stream import stream_scan

app = FastAPI(title="MCP Attack & Defense Range")

# Vite dev server runs on 5173; allow it to reach the API + socket in dev.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVERS_DIR = Path("servers")

# Human-facing catalog. Anything in servers/ not listed here still shows up,
# labelled generically -- but the known attacks get proper framing.
SCENARIOS = {
    "benign_math.py": {
        "label": "Benign math server",
        "attack_class": "control",
        "blurb": "A clean server with no hidden instructions. The baseline "
                 "everything else is measured against.",
    },
    "poisoned_math.py": {
        "label": "Poisoned math server",
        "attack_class": "tool-poisoning",
        "blurb": "Hidden directives buried in tool descriptions try to make the "
                 "agent read a private key and exfiltrate it. Includes the "
                 "benign-worded and split-payload variants the scanner is "
                 "documented to miss.",
    },
    "poisoned_variants.py": {
        "label": "Poisoning variants",
        "attack_class": "tool-poisoning",
        "blurb": "A spread of description-layer payloads with different framings "
                 "-- authority reframes, fake config blocks, concealment "
                 "language -- for probing rule coverage.",
    },
    "rugpull_email.py": {
        "label": "Rug-pull email server",
        "attack_class": "rug-pull",
        "blurb": "Ships a clean tool, then mutates its definition after approval. "
                 "Caught by fingerprint drift against the pinned baseline, not by "
                 "wording.",
    },
    "toxic_flow_github.py": {
        "label": "Toxic-flow GitHub server",
        "attack_class": "toxic-flow",
        "blurb": "Injection arrives inside the DATA a tool returns, not its "
                 "description -- so the static scanner can't see it. This is the "
                 "runtime guard's job; here it shows as a clean description scan.",
    },
}


@app.on_event("startup")
def _startup():
    db.init_db()


@app.get("/api/scenarios")
def scenarios():
    out = []
    for path in sorted(SERVERS_DIR.glob("*.py")):
        meta = SCENARIOS.get(path.name, {
            "label": path.stem.replace("_", " ").title(),
            "attack_class": "unknown",
            "blurb": "Uncatalogued server.",
        })
        out.append({"id": path.name, "server": str(path), **meta})
    return {"scenarios": out}


@app.get("/api/runs")
def runs():
    return {"runs": db.list_runs()}


@app.get("/api/runs/{run_id}")
def run_detail(run_id: int):
    run = db.get_run(run_id)
    if run is None:
        return {"error": "not found"}
    return run


@app.post("/api/pins/reset")
def reset_pins():
    db.reset_pins()
    return {"ok": True}


@app.websocket("/ws/scan/{scenario}")
async def ws_scan(websocket: WebSocket, scenario: str):
    await websocket.accept()

    server_path = SERVERS_DIR / scenario
    if not server_path.exists() or server_path.suffix != ".py":
        await websocket.send_json({"event": "error", "message": "unknown scenario"})
        await websocket.close()
        return

    meta = SCENARIOS.get(scenario, {"label": scenario, "attack_class": "unknown"})
    started_at = db.now_iso()

    await websocket.send_json({
        "event": "start",
        "scenario": scenario,
        "label": meta["label"],
        "attack_class": meta["attack_class"],
        "started_at": started_at,
    })

    final = None
    try:
        async for evt in stream_scan(str(server_path)):
            await websocket.send_json(evt)
            if evt["event"] == "verdict":
                final = evt
    except WebSocketDisconnect:
        return

    # Persist once the scan resolves, then tell the client its run id.
    if final is not None:
        run_id = db.save_run(
            scenario=meta["label"],
            server=str(server_path),
            started_at=started_at,
            overall=final["overall"],
            tools=final["tools"],
        )
        try:
            await websocket.send_json({"event": "saved", "run_id": run_id})
        except RuntimeError:
            pass

    await websocket.close()


# ---- serve the built dashboard (production) -------------------------------
# In production we ship one service: FastAPI serves the compiled React app on
# the same origin as the API and WebSocket, so there's no CORS or cross-origin
# socket to configure. This mount is LAST, so every /api and /ws route above
# takes precedence; it only catches everything else (index.html, assets).
# Guarded by existence so local dev — where the UI is served by the Vite dev
# server and dashboard/dist doesn't exist — still runs API-only.
_DIST = Path("dashboard/dist")
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="dashboard")
