"""
MCP tool-poisoning scanner.

Connects to an MCP server, retrieves every tool it advertises, and runs the
description of each tool through the detection rules.

Usage:
    uv run python scanner/scan.py servers/poisoned_math.py
"""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from scanner.rules import scan_text, verdict


async def scan_server(server_script: str):
    params = StdioServerParameters(command="python", args=[server_script])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resp = await session.list_tools()

            print(f"\n=== Scanning: {server_script} ===")
            print(f"Tools advertised: {len(resp.tools)}\n")

            server_findings = []
            for tool in resp.tools:
                findings = scan_text(tool.description or "")
                v = verdict(findings)
                server_findings.extend(findings)

                mark = {"clean": "[ OK ]", "SUSPICIOUS": "[WARN]",
                        "MALICIOUS": "[FAIL]"}[v]
                print(f"{mark} {tool.name}: {v}")
                for label, sev in findings:
                    print(f"        - ({sev}) {label}")

            overall = verdict(server_findings)
            print(f"\n>>> SERVER VERDICT: {overall}")
            return overall


async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scanner/scan.py <server_script>")
        return
    await scan_server(sys.argv[1])


if __name__ == "__main__":
    asyncio.run(main())