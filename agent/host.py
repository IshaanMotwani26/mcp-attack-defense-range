import asyncio

from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()  # reads ANTHROPIC_API_KEY from your .env
anthropic = Anthropic()


def tools_for_claude(mcp_tools):
    # Translate the server's tool list into the format the Claude API expects
    return [{
        "name": t.name,
        "description": t.description,   # <-- the field we poison later
        "input_schema": t.inputSchema,
    } for t in mcp_tools]


async def run_agent(session, user_msg):
    resp = await session.list_tools()
    tools = tools_for_claude(resp.tools)
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
            # No tool calls left — Claude gave a final text answer
            return "".join(b.text for b in reply.content if b.type == "text")

        # Claude asked to call tools — run them and send results back as STRINGS
        results = []
        for tu in tool_uses:
            print(f"[tool call] {tu.name}({tu.input})")
            out = await session.call_tool(tu.name, tu.input)
            text = "".join(c.text for c in out.content if hasattr(c, "text"))
            results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": text,          # <-- the fix: a string, not a list
            })
        messages.append({"role": "user", "content": results})


async def main():
    params = StdioServerParameters(command="python", args=["servers/benign_math.py"])
    # Keep connect + use + cleanup all in one task to avoid async shutdown errors
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            answer = await run_agent(session, "What is 17 times 4?")
            print("\nClaude:", answer)


if __name__ == "__main__":
    asyncio.run(main())