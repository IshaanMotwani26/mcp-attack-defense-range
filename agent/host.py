import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()  # reads ANTHROPIC_API_KEY from your .env
anthropic = Anthropic()

TRACE_DIR = Path("attacks/traces")


def tools_for_claude(mcp_tools):
    # Translate the server's tool list into the format the Claude API expects
    return [{
        "name": t.name,
        "description": t.description,   # <-- the field we poison
        "input_schema": t.inputSchema,
    } for t in mcp_tools]


async def run_agent(session, user_msg, trace):
    resp = await session.list_tools()
    tools = tools_for_claude(resp.tools)

    # Record what the server advertised — descriptions and all
    trace["advertised_tools"] = tools

    messages = [{"role": "user", "content": user_msg}]

    while True:
        reply = anthropic.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": reply.content})

        tool_uses = [b for b in reply.content if b.type == "tool_use"]
        if not tool_uses:
            final = "".join(b.text for b in reply.content if b.type == "text")
            trace["final_answer"] = final
            return final

        results = []
        for tu in tool_uses:
            print(f"[tool call] {tu.name}({tu.input})")
            trace["tool_calls"].append({"name": tu.name, "input": tu.input})
            out = await session.call_tool(tu.name, tu.input)
            text = "".join(c.text for c in out.content if hasattr(c, "text"))
            trace["tool_results"].append({"name": tu.name, "output": text})
            results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": text,
            })
        messages.append({"role": "user", "content": results})


async def main():
    # Usage: python agent/host.py <server_script> "<your question>"
    server_script = sys.argv[1] if len(sys.argv) > 1 else "servers/benign_math.py"
    user_msg = sys.argv[2] if len(sys.argv) > 2 else "What is 17 times 4?"

    trace = {
        "timestamp": datetime.now().isoformat(),
        "server": server_script,
        "user_message": user_msg,
        "tool_calls": [],
        "tool_results": [],
    }

    params = StdioServerParameters(command="python", args=[server_script])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            answer = await run_agent(session, user_msg, trace)
            print("\nClaude:", answer)

    # Save the trace as evidence
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    name = Path(server_script).stem
    out_path = TRACE_DIR / f"{name}_{datetime.now():%H%M%S}.json"
    out_path.write_text(json.dumps(trace, indent=2, default=str))
    print(f"[trace saved] {out_path}")


if __name__ == "__main__":
    asyncio.run(main())