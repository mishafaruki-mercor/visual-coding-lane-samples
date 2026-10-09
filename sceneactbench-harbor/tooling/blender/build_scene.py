"""Build a SceneActBench Reconstruction sample inside Blender (called by tooling/make_sample.py).

  blender -b <source.blend> --python build_scene.py -- <scene.json> <out_dir>

Writes to <out_dir>:
  golden.glb         one mesh per furniture item, metres, Z-up, floor at 0 (the hidden answer key)
  render_000N.png    the reference views (furniture only, plain background)
  cameras.json       camera poses for the views
  report.json        {"ok": bool, "problems": [...], "warnings": [...], "items": {...}}
"""
import bmesh
import fnmatch
import json
import math
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

cfg_path, out = sys.argv[sys.argv.index("--") + 1:]
cfg = json.load(open(cfg_path))
os.makedirs(out, exist_ok=True)

FOV_X = 39.6          # official SceneActBench field of view
RES = 768             # official reference resolution
GEOM_TYPES = ("MESH", "CURVE", "SURFACE", "META", "FONT")
problems, warnings = [], []
report = {"ok": False, "problems": problems, "warnings": warnings, "items": {}}


def finish(ok):
    report["ok"] = ok and not problems
    json.dump(report, open(os.path.join(out, "report.json"), "w"), indent=1)
    sys.exit(0)


def matches(name, patterns):
    return any(fnmatch.fnmatchcase(name, p) for p in patterns)


# ---------------------------------------------------------------- 1. pick objects
items = cfg["items"]
exclude = cfg.get("exclude", [])
geom = [o for o in bpy.data.objects if o.type in GEOM_TYPES]
claimed, groups = {}, {}
for name, patterns in items.items():
    for p in patterns:
        if not any(fnmatch.fnmatchcase(o.name, p) for o in geom):
            problems.append(f'item "{name}": pattern "{p}" matched no objects '
                            f'(run make_sample.py --list to see object names)')
    objs = [o for o in geom if matches(o.name, patterns) and not matches(o.name, exclude)]
    for o in objs:
        if o.name in claimed:
            problems.append(f'object "{o.name}" is listed in both "{claimed[o.name]}" and "{name}"')
        claimed[o.name] = name
    groups[name] = objs
if problems:
    finish(False)

# ---------------------------------------------------------------- 2. units + origin
scale = float(cfg.get("units_to_metres", 1.0))
dg = bpy.context.evaluated_depsgraph_get()


def world_corners(o):
    return [o.matrix_world @ Vector(c) for c in o.bound_box]


all_c = [c for objs in groups.values() for o in objs for c in world_corners(o)]
origin = cfg.get("origin", "auto")
if origin == "auto":
    lo = Vector((min(c.x for c in all_c), min(c.y for c in all_c), min(c.z for c in all_c)))
    hi = Vector((max(c.x for c in all_c), max(c.y for c in all_c), max(c.z for c in all_c)))
    origin = [(lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z]
TO_M = Matrix.Scale(scale, 4) @ Matrix.Translation(-Vector(origin))

# ---------------------------------------------------------------- 3. join each item into one mesh
colors = cfg.get("colors", {})


def source_color(objs):
    for o in objs:
        for m in getattr(o.data, "materials", []) or []:
            if not m:
                continue
            if m.use_nodes and m.node_tree:
                for n in m.node_tree.nodes:
                    if n.type == "BSDF_PRINCIPLED" and not n.inputs["Base Color"].is_linked:
                        return tuple(n.inputs["Base Color"].default_value[:3])
            return tuple(m.diffuse_color[:3])
    return (0.6, 0.6, 0.6)


built = {}
for name, objs in groups.items():
    bm = bmesh.new()
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))  # bakes modifiers / curves
        me.transform(TO_M @ o.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    for f in bm.faces:
        f.material_index = 0
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if len(me.polygons) == 0:
        problems.append(f'item "{name}" has no surface (its objects have no faces)')
    col = tuple(colors.get(name, source_color(objs)))
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*col, 1)
    mat.diffuse_color = (*col, 1)
    me.materials.append(mat)
    built[name] = me

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
sc = bpy.context.scene
objs_out = {}
for name, me in built.items():
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    objs_out[name] = ob

# ---------------------------------------------------------------- 4. sanity checks (metres)
bb = {}
for name, ob in objs_out.items():
    vs = [v.co for v in ob.data.vertices]
    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
    bb[name] = (lo, hi)
    size = hi - lo
    report["items"][name] = {"objects": len(groups[name]), "size_m": [round(x, 2) for x in size],
                             "center_m": [round(x, 2) for x in (lo + hi) / 2]}
    if max(size) > 6:
        warnings.append(f'item "{name}" is {max(size):.1f} m across - is that right?')
lo_all = Vector((min(b[0].x for b in bb.values()), min(b[0].y for b in bb.values()), min(b[0].z for b in bb.values())))
hi_all = Vector((max(b[1].x for b in bb.values()), max(b[1].y for b in bb.values()), max(b[1].z for b in bb.values())))
span = hi_all - lo_all
report["room_span_m"] = [round(x, 2) for x in span]
if max(span.x, span.y) > 25:
    far = sorted(bb, key=lambda n: -((bb[n][0] + bb[n][1]) / 2 - (lo_all + hi_all) / 2).length)[:3]
    problems.append(f"furniture spans {max(span.x, span.y):.0f} m. Wrong units_to_metres, or a stray object "
                    f"far from the room? Furthest items: {', '.join(far)}")
if max(span) < 0.8:
    problems.append(f"furniture spans only {max(span):.2f} m. Is units_to_metres too small?")
if problems:
    finish(False)

# ---------------------------------------------------------------- 5. golden export
for ob in objs_out.values():
    ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(out, "golden.glb"), export_format="GLB",
                          use_selection=True, export_apply=True)

# ---------------------------------------------------------------- 6. cameras
engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
sc.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in engines else "BLENDER_EEVEE_NEXT"
sc.render.resolution_x = sc.render.resolution_y = RES
sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
w = bpy.data.worlds.new("W")
sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
for rot, energy in (((math.radians(50), 0, math.radians(30)), 3.0), ((math.radians(60), 0, math.radians(210)), 1.2)):
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = energy
    sun.rotation_euler = rot
    sc.collection.objects.link(sun)

cd = bpy.data.cameras.new("refcam")
cd.sensor_width = 36.0
cd.lens = 36.0 / (2 * math.tan(math.radians(FOV_X) / 2))
cam = bpy.data.objects.new("refcam", cd)
sc.collection.objects.link(cam)
sc.camera = cam


def aim(pos, target):
    p = Vector(pos)
    d = (Vector(target) - p).normalized()
    cam.matrix_world = Matrix.Translation(p) @ d.to_track_quat("-Z", "Y").to_matrix().to_4x4()
    bpy.context.view_layer.update()
    return p, d


def in_frame(name, margin=0.03):
    lo, hi = bb[name]
    for x in (lo.x, hi.x):
        for y in (lo.y, hi.y):
            for z in (lo.z, hi.z):
                v = world_to_camera_view(sc, cam, Vector((x, y, z)))
                if v.z <= 0 or not (margin <= v.x <= 1 - margin and margin <= v.y <= 1 - margin):
                    return False
    return True


def visible_fraction(name, n=120):
    ob = objs_out[name]
    vs = ob.data.vertices
    step = max(1, len(vs) // n)
    pts = [vs[i].co.copy() for i in range(0, len(vs), step)]
    dgv = bpy.context.evaluated_depsgraph_get()
    origin_c = cam.matrix_world.translation
    seen = 0
    for p in pts:
        d = p - origin_c
        hit, loc, _, _, hobj, _ = sc.ray_cast(dgv, origin_c, d.normalized(), distance=d.length + 1e-3)
        if not hit or hobj.name == name or (loc - p).length < 0.02:
            seen += 1
    return seen / max(1, len(pts))


target_default = Vector(((lo_all.x + hi_all.x) / 2, (lo_all.y + hi_all.y) / 2, lo_all.z + 0.35 * span.z))
views = []
if "cameras" in cfg:   # explicit poses (metres, final frame)
    for c in cfg["cameras"]:
        views.append((c["position"], c.get("target", list(target_default))))
else:                  # automatic: 3 elevated corner views, pulled back until every item is in frame
    dirs = cfg.get("camera_directions", [(-0.55, -0.75, 0.28), (0.8, -0.5, 0.28), (-0.6, 0.75, 0.3)])
    for dvec in dirs:
        dvec = Vector(dvec).normalized()
        dist = 1.1 * span.length
        for _ in range(40):
            aim(target_default + dvec * dist, target_default)
            if all(in_frame(n) for n in objs_out):
                break
            dist *= 1.08
        views.append((list(target_default + dvec * dist), list(target_default)))

# ---------------------------------------------------------------- 7. render + per-view checks
meta = {"camera_angle_x": math.radians(FOV_X), "sensor_width": 36.0, "views": []}
vis = {n: [] for n in objs_out}
cropped = {n: [] for n in objs_out}
for i, (pos, tgt) in enumerate(views):
    p, d = aim(pos, tgt)
    for n in objs_out:
        if not in_frame(n, margin=0.0):
            cropped[n].append(i)
        vis[n].append(round(visible_fraction(n), 2))
    sc.render.filepath = os.path.join(out, f"render_{i:04d}.png")
    bpy.ops.render.render(write_still=True)
    meta["views"].append({"index": f"{i:04d}", "position": list(p), "look_dir": list(d),
                          "matrix_world": [list(r) for r in cam.matrix_world]})
for n, views_cut in cropped.items():
    report["items"][n]["cut_off_in_views"] = views_cut
    if len(views_cut) == len(views):
        problems.append(f'item "{n}" is cut off by the picture edge in every view; '
                        f"move the cameras back (or drop the \"cameras\" entry to place them automatically)")
    elif views_cut:
        warnings.append(f'item "{n}" is partly outside the picture in view(s) {views_cut} '
                        f"(fully visible in the others)")
for n, fr in vis.items():
    report["items"][n]["visible_fraction_per_view"] = fr
    if max(fr) < 0.05:
        problems.append(f'item "{n}" is hidden behind other furniture in every view (visible: {fr})')
    elif max(fr) < 0.25:
        warnings.append(f'item "{n}" is mostly hidden in every view (visible: {fr}); consider other camera_directions')
json.dump(meta, open(os.path.join(out, "cameras.json"), "w"), indent=1)
finish(True)
