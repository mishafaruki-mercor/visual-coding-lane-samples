"""Runs inside `blender -b --python blender_boot.py -- <port>`.

Starts the blender-mcp addon's socket server headless. Background Blender never
fires bpy.app.timers, so the addon's "run on the main thread" call is redirected
into a queue that this script drains forever.
"""
import os
import queue
import sys
import types

import bpy

port = int(sys.argv[sys.argv.index("--") + 1])
AUTOSAVE = os.environ.get("SCENEACTBENCH_AUTOSAVE", "/app/output/.autosave.blend")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "blender-mcp"))
import addon  # noqa: E402

_q = queue.Queue()


def _enqueue(fn, first_interval=0.0, persistent=False):
    _q.put(fn)


_app = types.SimpleNamespace(**{k: getattr(bpy.app, k) for k in dir(bpy.app) if not k.startswith("__")})
_app.timers = types.SimpleNamespace(register=_enqueue)
addon.bpy = types.SimpleNamespace(**{k: getattr(bpy, k) for k in dir(bpy) if not k.startswith("__")})
addon.bpy.app = _app
sys.modules["bpy"] = bpy

try:
    addon._register_scene_props()
except Exception as e:
    print(f"[boot] scene props: {e}")

bpy.context.preferences.filepaths.save_version = 0  # no .blend1 backups next to the autosave

server = addon.BlenderMCPServer(port=port)
server.start()
print(f"[boot] headless BlenderMCP listening on {port}", flush=True)

while True:
    try:
        fn = _q.get(timeout=0.05)
    except queue.Empty:
        continue
    try:
        fn()
    except Exception as e:
        print(f"[boot] command error: {e}", flush=True)
    # Keep a copy of the current scene so grading still works if Blender exits with the agent.
    try:
        os.makedirs(os.path.dirname(AUTOSAVE), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=AUTOSAVE, copy=True, compress=False)
    except Exception as e:
        print(f"[boot] autosave failed: {e}", flush=True)
