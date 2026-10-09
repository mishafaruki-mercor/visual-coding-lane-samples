#!/bin/bash
# MCP server entrypoint for the agent (stdio). Starts Blender on first use, then serves
# the blender-mcp tools. Nothing may be printed to stdout except the MCP protocol.
/opt/sceneactbench/start_blender.sh 1>&2 || exit 1
export BLENDER_MCP_DISABLE_TELEMETRY=1
exec /opt/sceneactbench/venv/bin/blender-mcp
