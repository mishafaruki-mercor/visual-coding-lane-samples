"""Minimal client for the headless Blender socket (stdlib only).

  python3 blender_client.py <file.py>     run a bpy script inside the live Blender, print its output
"""
import json
import os
import socket
import sys

PORT = int(os.environ.get("BLENDER_PORT", "9876"))


def run_code(code, timeout=600):
    with socket.create_connection(("127.0.0.1", PORT), timeout=10) as s:
        s.settimeout(timeout)
        s.sendall(json.dumps({"type": "execute_code", "params": {"code": code}}).encode())
        buf = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
            try:
                return json.loads(buf.decode())
            except json.JSONDecodeError:
                continue
    raise RuntimeError("no response from Blender")


if __name__ == "__main__":
    print(json.dumps(run_code(open(sys.argv[1]).read())))
