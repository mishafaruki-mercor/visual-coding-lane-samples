#!/bin/bash
# Start headless Blender with the MCP addon socket if it is not already running (idempotent).
PORT="${BLENDER_PORT:-9876}"
up() { (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; }
up && exit 0
nohup "${BLENDER:-/opt/blender/blender}" -b --factory-startup \
    --python /opt/sceneactbench/blender_boot.py -- "$PORT" > /tmp/blender.log 2>&1 &
for _ in $(seq 1 240); do up && exit 0; sleep 0.5; done
echo "headless Blender did not start; see /tmp/blender.log" >&2
exit 1
