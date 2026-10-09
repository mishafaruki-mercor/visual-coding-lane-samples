#!/bin/bash
# Oracle: load the golden solution into the live headless Blender, as an agent would leave it.
set -e
/opt/sceneactbench/start_blender.sh
cat > /tmp/load_golden.py <<PY
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.gltf(filepath='/solution/golden_scene.glb')
print('loaded', sum(1 for o in bpy.data.objects if o.type == 'MESH'), 'meshes')
PY
python3 /opt/sceneactbench/blender_client.py /tmp/load_golden.py
