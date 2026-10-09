"""Collect the agent's final Blender scene as a GLB for scoring (stdlib only).

Order: live headless Blender (socket) -> autosave .blend -> agent-saved scene.blend -> agent-saved scene.glb.
Meshes only, modifiers applied -- the same export the SceneActBench harness uses.
"""
import json
import os
import shutil
import socket
import subprocess
import sys

OUT = sys.argv[1]
PORT = int(os.environ.get("BLENDER_PORT", "9876"))
BLENDER = os.environ.get("BLENDER", "/opt/blender/blender")
EXPORT = (
    "import bpy\n"
    "bpy.ops.object.select_all(action='DESELECT')\n"
    "for o in bpy.data.objects: o.select_set(o.type=='MESH' and o.visible_get())\n"
    "n=sum(1 for o in bpy.context.selected_objects)\n"
    "print('MESHES', n)\n"
    "if n: bpy.ops.export_scene.gltf(filepath={out!r}, use_selection=True, export_format='GLB', export_apply=True)\n"
)


def live():
    with socket.create_connection(("127.0.0.1", PORT), timeout=5) as s:
        s.settimeout(600)
        s.sendall(json.dumps({"type": "execute_code", "params": {"code": EXPORT.format(out=OUT)}}).encode())
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


def from_blend(path):
    script = "/tmp/_export_scene.py"
    open(script, "w").write(EXPORT.format(out=OUT))
    subprocess.run([BLENDER, "-b", path, "--python", script], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)


if os.path.exists(OUT):
    os.remove(OUT)
sources = [("live Blender", live),
           ("autosave", lambda: from_blend("/app/output/.autosave.blend") if os.path.exists("/app/output/.autosave.blend") else None),
           ("scene.blend", lambda: from_blend("/app/output/scene.blend") if os.path.exists("/app/output/scene.blend") else None),
           ("scene.glb", lambda: shutil.copy("/app/output/scene.glb", OUT) if os.path.exists("/app/output/scene.glb") else None)]
for name, fn in sources:
    try:
        fn()
    except Exception as e:
        print(f"[export] {name}: {e!r}")
        continue
    if os.path.exists(OUT) and os.path.getsize(OUT) > 0:
        print(f"[export] scene taken from: {name}")
        sys.exit(0)
print("[export] no scene found (no meshes in Blender and no saved scene)")
sys.exit(1)
