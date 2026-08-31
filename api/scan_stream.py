"""
Streaming wrapper around the existing signature scanner.

The static scanner (scanner/scan.py) prints its results. For the dashboard we
need the same detection to arrive as a live sequence of events, one per tool,
so the UI can light each channel up as it resolves.

This module does NOT reimplement detection. It calls straight into the shipped
engine:

    scanner.rules.scan_text / verdict   -- the detection rules
    scanner.pinning.fingerprint         -- the SHA-256 tool fingerprint

The only thing added here is transport (async event generator) and pin storage
in SQLite (via api.db) so rug-pull detection persists across runs.
"""

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from scanner.rules import scan_text, verdict
from scanner.pinning import fingerprint
from api import db


def _pin_status(tool):
    """Compare this tool's fingerprint against its stored pin (in the DB)."""
    fp = fingerprint(tool)
    prior = db.get_pin(tool.name)
    if prior is None:
        status = "new"
    elif prior == fp:
        status = "unchanged"
    else:
        status = "CHANGED (possible rug pull)"
    db.set_pin(tool.name, fp)
    return status


async def stream_scan(server_script: str):
    """
    Async generator yielding scan events for one MCP server:

      {"event": "connected", "tool_count": int}
      {"event": "tool", "index": int, "name": str, "verdict": str,
       "findings": [{"label": str, "severity": str}], "pin": str,
       "description": str}
      {"event": "verdict", "overall": str, "flagged": int,
       "rug_pull": bool, "tools": [...]}
      {"event": "error", "message": str}

    The caller (WebSocket handler) is responsible for persistence + framing.
    """
    params = StdioServerParameters(command="python", args=[server_script])
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                resp = await session.list_tools()
                tools = resp.tools

                yield {"event": "connected", "tool_count": len(tools)}

                collected = []
                for i, tool in enumerate(tools):
                    desc = tool.description or ""
                    raw_findings = scan_text(desc)
                    v = verdict(raw_findings)
                    pin = _pin_status(tool)

                    findings = [{"label": lbl, "severity": sev}
                                for lbl, sev in raw_findings]
                    record = {
                        "index": i,
                        "name": tool.name,
                        "verdict": v,
                        "findings": findings,
                        "pin": pin,
                        "description": desc.strip(),
                    }
                    collected.append(record)

                    yield {"event": "tool", **record}
                    # small delay so the sweep is legible in the UI; detection
                    # itself is instant.
                    await asyncio.sleep(0.35)

                overall = verdict(
                    [(f["label"], f["severity"])
                     for t in collected for f in t["findings"]]
                )
                rug_pull = any(t["pin"].startswith("CHANGED") for t in collected)
                flagged = sum(1 for t in collected if t["verdict"] != "clean")

                yield {
                    "event": "verdict",
                    "overall": overall,
                    "flagged": flagged,
                    "rug_pull": rug_pull,
                    "tools": collected,
                }
    except Exception as exc:  # surface connection / spawn failures to the UI
        yield {"event": "error", "message": f"{type(exc).__name__}: {exc}"}
