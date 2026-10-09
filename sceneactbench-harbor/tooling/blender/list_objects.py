"""Print every object in a .blend with its type, collection, centre and size (source units).

  blender -b <source.blend> --python list_objects.py
Used by `make_sample.py --list` to help write the "items" section of scene.json.
"""
import bpy
from mathutils import Vector

rows = []
for o in bpy.data.objects:
    if o.type not in ("MESH", "CURVE", "SURFACE", "META", "FONT"):
        continue
    cs = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = [min(c[i] for c in cs) for i in range(3)]
    hi = [max(c[i] for c in cs) for i in range(3)]
    coll = o.users_collection[0].name if o.users_collection else "-"
    rows.append((coll, o.name, o.type, [(a + b) / 2 for a, b in zip(lo, hi)], [b - a for a, b in zip(lo, hi)]))
print("SCENEACTBENCH_LIST_BEGIN")
print(f"{'collection':<16} {'object':<28} {'type':<6} {'centre (x, y, z)':<26} size (x, y, z)")
for coll, name, typ, c, s in sorted(rows):
    print(f"{coll[:16]:<16} {name[:28]:<28} {typ:<6} "
          f"({c[0]:7.2f},{c[1]:7.2f},{c[2]:6.2f})    ({s[0]:.2f}, {s[1]:.2f}, {s[2]:.2f})")
print(f"{len(rows)} objects")
print("SCENEACTBENCH_LIST_END")
