"""Runs INSIDE the task container. One MCP request per invocation, against the task's own
blender-mcp stdio server (the same server task.toml declares for MCP-capable agents).

  python mcp_bridge.py list <out.json>
  python mcp_bridge.py call <tool_name> <args.json> <out.json>
"""
import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = StdioServerParameters(command="/opt/sceneactbench/blender_mcp_stdio.sh", args=[])


async def main():
    mode, out_path = sys.argv[1], sys.argv[-1]
    async with stdio_client(SERVER) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            if mode == "list":
                tools = (await s.list_tools()).tools
                out = {"tools": [{"name": t.name, "description": t.description or "",
                                  "input_schema": t.inputSchema} for t in tools]}
            else:
                name, args = sys.argv[2], json.load(open(sys.argv[3]))
                result = await s.call_tool(name, args)
                parts, images = [], []
                for block in result.content:
                    btype = getattr(block, "type", None)
                    if btype == "text":
                        parts.append(block.text)
                    elif btype == "image":
                        images.append({"data": block.data, "mime": getattr(block, "mimeType", "image/png")})
                    else:
                        parts.append(str(block))
                text = "\n".join(parts)
                if getattr(result, "isError", False):
                    text = f"ERROR: {text}"
                out = {"text": text, "images": images}
    with open(out_path, "w") as f:
        json.dump(out, f)


asyncio.run(main())
