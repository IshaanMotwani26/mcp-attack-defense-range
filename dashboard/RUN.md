# Running the Range dashboard

The dashboard turns the shipped signature scanner into a live console: pick a
target MCP server, run a scan, and watch each tool resolve to a verdict in real
time. Runs are saved to a local SQLite history.

It reuses the real detection engine — `scanner/rules.py` and
`scanner/pinning.py` are untouched. The scanner path needs **no** Anthropic API
key (it only reads tool descriptions), so the dashboard runs offline.

## One-time setup

Backend deps (from the repo root):

```bash
uv sync
```

Frontend deps:

```bash
cd dashboard
npm install
```

## Run it (two terminals)

**Terminal 1 — backend** (repo root):

```bash
uv run uvicorn api.server:app --reload --port 8000
```

**Terminal 2 — dashboard** (in `dashboard/`):

```bash
npm run dev
```

Open the URL Vite prints (default http://localhost:5173). The dev server
proxies `/api` and the scan WebSocket to the backend on :8000, so you only ever
load one origin.

## What to try

- Scan **Poisoned math server** → `add_v1` lights up MALICIOUS; `add_v2` and
  `add_v3` come back clean — the benign-worded and split-payload variants the
  scanner is documented to miss. That gap is the honest part of the story.
- Scan **Benign math server** → clean baseline.
- Scan **Rug-pull email server** twice, then mutate a tool description and scan
  again → the pin drifts and the run is flagged as a rug pull. Use
  **Reset rug-pull baseline** to re-pin from scratch.

## What this is (and isn't) yet

This is the scanner (description-layer) vertical slice, end to end: trigger →
live stream → verdict → persisted history. Not yet wired into the dashboard:
the runtime proxy (toxic-flow, data-layer) and a full agent run, both of which
need the Anthropic API key. Those are the next slices.
