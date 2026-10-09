# SceneActBench · Reconstruction

You are working in a Linux container with a **headless Blender** instance. Control it through the
**`blender` MCP tools** (most importantly `execute_blender_code`, `render_scene_view`,
`get_scene_info`, `get_object_info`). The Blender scene starts empty.

- **Reference images** are in `/app/input/` (`render_0000.png`, `render_0001.png`, `render_0002.png`).
  Open and look at them; they are your only visual evidence.
- **Your answer is the 3D scene you leave in Blender.** When you finish, the furniture meshes in the
  Blender scene are exported and scored against a hidden 3D ground truth. As a safeguard, also save the
  scene before you stop, by running this with `execute_blender_code`:
  `import bpy; bpy.ops.wm.save_as_mainfile(filepath='/app/output/scene.blend')`

The task instructions follow.

---

You are a procedural 3D modeling expert. Given multiple reference images of an
indoor scene (a room with a few pieces of furniture), you reconstruct EVERY furniture piece in
Blender by writing bpy code, matching its geometry AND its visible color.

# Input
- N reference images of the SAME room from different camera viewpoints (each with a known camera
  pose). Use them as multi-view evidence: cross-reference views to resolve depth, proportions,
  occluded structure, and hidden sides.
- The Blender scene starts EMPTY. The reference images are NOT available to your script at runtime.

# Reading the references — do this carefully BEFORE you build
1. Identify each furniture piece visible in any view. Count them.
2. For each piece, infer:
   - Category and characteristic shape.
   - Overall dimensions (length × width × height) in METERS, calibrated against the room.
   - Position and yaw (rotation about Z) in the world frame given the camera poses.
   - Symmetries (bilateral / radial), repeating sub-parts (slats, drawers, legs, lamp shades).
   - Distinctive ornament (panels, drawer pulls, mattress, pendant cords).
3. When images give clear quantitative cues (e.g. "4 legs", "3 drawers", "5 hanging cords"),
   reproduce those counts EXACTLY rather than approximating.
4. Read the dominant Base Color of every piece so each gets the right material color.

# Geometry quality bar
For each furniture piece, push for as much geometric detail as the reference shows. Compose
multiple primitives + bmesh edits + modifiers. Use bpy.ops.mesh.primitive_*_add for body shapes;
use bmesh operators (bevel / extrude / inset) to add edges and indents; use array / mirror
modifiers for repeating parts (legs, slats, drawers); exploit symmetry (mirror modifier) for
bilateral pieces. Do not ship a single naked cube for a complex piece.

Keep total mesh complexity under a few hundred thousand vertices. Build at real-world scale
(meters), every piece sitting on the floor (lowest Z = 0). World is Z-up.

# What NOT to build
- NO room shell: no floor plane, no walls, no ceiling, no skirting boards, no windows, even
  though the references show them. Furniture only.
- NO decorative props (books, plants, pictures) unless they are unmistakably present and large.
- DO NOT try to reproduce textures / patterns / fabric weave; only solid Base Color is required.

# Materials
For every mesh object, attach a Principled BSDF material with the correct Base Color, e.g.:
    mat = bpy.data.materials.new("m_bed_frame"); mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
    obj.data.materials.append(mat)
Set roughness ≈ 0.7 and metallic = 0 by default (override only when clearly metal/glossy).

# How to place pieces
Set the FULL world matrix (T @ R) — rotation_euler/location piecemeal can fail under MCP:
    import bpy, mathutils
    obj = bpy.data.objects["bed"]
    T = mathutils.Matrix.Translation((x, y, z))
    R = mathutils.Matrix.Rotation(yaw_radians, 4, 'Z')
    obj.matrix_world = T @ R

# Workflow — iterate until satisfied
Build the scene with execute_blender_code, then call render_scene_view at one or more reference
camera poses. Compare each render to the corresponding reference image at the SAME camera angle,
walking through this priority list (in this order):

  1. MISSING PIECES — components in the reference that you did not build at all.
  2. WRONG SILHOUETTE / overall shape of an existing piece.
  3. WRONG PROPORTIONS / size — sizes or aspect ratios visibly disagree with the reference.
  4. WRONG COUNT of repeating parts — legs, drawers, lamp shades, hanging cords.
  5. MISALIGNMENT / FLOATING / wrong yaw.
  6. MISSING GEOMETRIC DETAIL — flat where the reference shows ribs / panels / drawer fronts /
     pleats / multiple lamp shades / etc.
  7. WRONG COLOR — Base Color visibly off vs the reference.

If any priority-1..6 item is clearly wrong, fix it with execute_blender_code, render again, and
re-evaluate. Stop when no priority-1..6 issue remains and priority-7 is at most "minor color
drift". You decide when it is good enough — you have a limited step budget, but use it.

# Conservatism bias
Each fix risks breaking working code. If a piece is recognizably correct and the only differences
are minor proportions or color, leave it alone. Do not rewrite working pieces every round.

When you stop, give a one-paragraph summary of what you built and any remaining differences from
the reference. Do NOT ask clarifying questions; if references are ambiguous, choose reasonable
defaults consistent with the visible views and the object category.

# Grading you'll be measured on
- Per-object f-score and Chamfer (geometry accuracy after global + local alignment).
- Per-object PointBERT cosine (3D semantic similarity — does it look like the right object).
- Per-object position error.
- Multi-view rendered visual fidelity (MSSIM / CLIP / LPIPS) against the references.
You get NO points for rooms, walls, or decorations; you get points for accurate furniture.

---

Reconstruct this indoor scene in 3D from 3 reference images of the SAME ROOM taken from different camera viewpoints (Blender starts empty).

World frame: Z-up, meters. fov_x = 39.6 deg.

Reference images and their camera poses (each in the same world frame):
  - view 0: /app/input/render_0000.png
      cam pos = [-7.1614, -9.7382, 4.5476], look_dir = [0.5663, 0.7722, -0.2883], up = [0.1705, 0.2325, 0.9575]
  - view 1: /app/input/render_0001.png
      cam pos = [10.7683, -6.3052, 4.4989], look_dir = [-0.8129, 0.5081, -0.2845], up = [-0.2413, 0.1508, 0.9587]
  - view 2: /app/input/render_0002.png
      cam pos = [-7.5517, 9.9896, 4.6759], look_dir = [0.5963, -0.7454, -0.2981], up = [0.1862, -0.2328, 0.9545]

Treat the 3 images as MULTI-VIEW evidence of one room (not separate rooms). Cross-reference them to resolve depth, hidden sides, and exact furniture positions.

Step 1 — IDENTIFY every furniture piece visible in any view (bed, wardrobe, nightstand, pendant lamp, dresser, ...). Count them. Read the dominant Base Color of each piece.
Step 2 — For each piece, infer its real-world size (m), world position (x,y,z) and yaw (radians about Z), then plan the geometry: which primitives + bmesh edits + modifiers (mirror/array) you'll use to capture the silhouette and repeating parts.
Step 3 — BUILD with execute_blender_code: create geometry + materials, set obj.matrix_world = T @ R for placement.
Step 4 — RENDER each piece's appearance with render_scene_view at the SAME camera poses listed above; compare to the reference views by priority (missing pieces > silhouette > proportions > count of repeating parts > misalignment > detail > color); fix and re-render until the room matches.
  Also create EXTRA cameras at other angles (e.g. a top-down view and a side view) and render_scene_view from them — the reference poses are 2D projections, so depth errors and objects floating / sunk into the floor only show from other angles. Verify the 3D layout, not just the reference silhouette.
Step 5 — Stop when satisfied; do not ask questions.

REMINDERS:
  - Furniture only. NO floor / walls / ceiling / windows / decorations.
  - Real-world meters; lowest Z = 0; do NOT rescale objects after placement.
  - Reproduce exact counts (legs, drawers, hanging cords) when visible.
  - Use bmesh / mirror / array modifiers for detail and repeating parts; do not ship naked cubes for complex pieces.
