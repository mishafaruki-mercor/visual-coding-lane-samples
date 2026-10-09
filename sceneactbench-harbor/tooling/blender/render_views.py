"""Render a scene .glb from a sample's reference cameras (+ a top-down view), furniture-only style.

  blender -b --factory-startup --python render_views.py -- <scene.glb> <cameras.json> <out_dir> <tag>
Writes <out_dir>/<tag>_view<N>.png and <out_dir>/<tag>_top.png.
"""
import json
import math
import sys

import bpy
from mathutils import Matrix, Vector

glb, cams_path, out, tag = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in engines else "BLENDER_EEVEE_NEXT"
sc.render.resolution_x = sc.render.resolution_y = 768
sc.render.film_transparent = True
bpy.ops.import_scene.gltf(filepath=glb)
w = bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
for rot, e in (((math.radians(50), 0, math.radians(30)), 3.0), ((math.radians(60), 0, math.radians(210)), 1.2)):
    s = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    s.data.energy = e
    s.rotation_euler = rot
    sc.collection.objects.link(s)
meta = json.load(open(cams_path))
cd = bpy.data.cameras.new("c")
cd.sensor_width = 36
cd.lens = 36 / (2 * math.tan(meta["camera_angle_x"] / 2))
cam = bpy.data.objects.new("c", cd)
sc.collection.objects.link(cam)
sc.camera = cam
for i, v in enumerate(meta["views"]):
    cam.matrix_world = Matrix(v["matrix_world"])
    sc.render.filepath = f"{out}/{tag}_view{i}.png"
    bpy.ops.render.render(write_still=True)
# top-down, framed on the reference cameras' common target area
pos = [Vector(v["position"]) for v in meta["views"]]
look = [Vector(v["look_dir"]) for v in meta["views"]]
centre = sum((p + d * ((-p.z) / d.z if d.z < 0 else 8.0) for p, d in zip(pos, look)), Vector()) / len(pos)
cd.type = "ORTHO"
cd.ortho_scale = 11
cam.matrix_world = Matrix.Translation((centre.x, centre.y, 12))
sc.render.filepath = f"{out}/{tag}_top.png"
bpy.ops.render.render(write_still=True)
