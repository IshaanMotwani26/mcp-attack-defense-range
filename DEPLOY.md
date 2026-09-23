# Deploying the Range to a live URL

The whole thing ships as **one service**: a multi-stage Docker image builds the
React dashboard and hands it to FastAPI, which serves the UI, the API, and the
scan WebSocket on a single origin. No separate frontend host, no CORS, no
cross-origin socket.

Verified before shipping: the frontend build, the Python-3.14 dependency
install, same-origin serving of app + API, and the live scan all run green.

## Deploy on Render (free)

1. Push these files to GitHub (Dockerfile, .dockerignore, and the two changed
   `api/` files) — see the commit block below.
2. Go to <https://dashboard.render.com> → **New** → **Web Service**.
3. Connect your GitHub and pick the `mcp-attack-defense-range` repo.
4. Render detects the `Dockerfile` automatically. Confirm:
   - **Runtime:** Docker
   - **Instance type:** Free
   - **No environment variables needed** — the scanner reads only tool
     descriptions, so there's no Anthropic key to set. (That changes when we
     add the runtime-proxy slice.)
5. Click **Create Web Service**. First build takes a few minutes (Node build +
   Python install). When it's done you get a URL like
   `https://mcp-attack-defense-range.onrender.com`.

Open it, select **Poisoned math server**, hit **Run scan** — the same live
readout you have locally, now on a link you can put on a resume.

## Free-tier tradeoffs (both fine for a portfolio piece)

- **Cold start.** The service sleeps after 15 minutes of no traffic and takes
  ~30–60s to wake. The first visitor after a nap sees a loading page, then it's
  fast. A paid instance ($7/mo) removes this if you ever want always-on.
- **History resets.** The filesystem is ephemeral, so the SQLite run history
  clears whenever the service sleeps or redeploys. Fine here — history is a
  demo of persistence within a session, not a system of record. (A managed
  Postgres would make it durable later.)

## Local dev is unchanged

Nothing here affects your local workflow. `dashboard/dist` doesn't exist
locally, so FastAPI skips the static mount and runs API-only; you still use the
Vite dev server:

- Backend: `uv run python run_api.py`
- Dashboard: `cd dashboard && npm run dev`
