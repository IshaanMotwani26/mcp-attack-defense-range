"""
MCP tool-poisoning scanner (with tool pinning for rug-pull detection).

Connects to an MCP server, retrieves every advertised tool, runs each
description through the detection rules, AND fingerprints each tool to detect
whether its definition changed since it was first pinned (a rug pull).

Usage:
    uv run python -m scanner.scan servers/poisoned_math.py
"""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from scanner.rules import scan_text, verdict
from scanner.pinning import load_pins, save_pins, check_and_update


async def scan_server(server_script: str):
    params = StdioServerParameters(command="python", args=[server_script])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resp = await session.list_tools()

            print(f"\n=== Scanning: {server_script} ===")
            print(f"Tools advertised: {len(resp.tools)}\n")

            pins = load_pins()
            server_findings = []
            rug_pull_detected = False

            for tool in resp.tools:
                findings = scan_text(tool.description or "")
                v = verdict(findings)
                server_findings.extend(findings)

                # Tool pinning: has this tool's definition changed since last seen?
                pin_status = check_and_update(tool, pins)
                if pin_status.startswith("CHANGED"):
                    rug_pull_detected = True

                mark = {"clean": "[ OK ]", "SUSPICIOUS": "[WARN]",
                        "MALICIOUS": "[FAIL]"}[v]
                print(f"{mark} {tool.name}: {v}  |  pin: {pin_status}")
                for label, sev in findings:
                    print(f"        - ({sev}) {label}")

            save_pins(pins)

            overall = verdict(server_findings)
            print(f"\n>>> SERVER VERDICT: {overall}")
            if rug_pull_detected:
                print(">>> RUG PULL ALERT: a tool definition changed since it was pinned!")
            return overall


async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python -m scanner.scan <server_script>")
        return
    await scan_server(sys.argv[1])


if __name__ == "__main__":
    asyncio.run(main())