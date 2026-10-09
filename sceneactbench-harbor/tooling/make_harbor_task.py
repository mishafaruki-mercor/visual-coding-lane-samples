"""Assemble a built sample (golden .glb + reference renders + camera poses) into a Harbor task.

Normally called by tooling/make_sample.py. Copies tooling/harbor_template/ (environment, tests,
solution scaffolding, identical in every task) into tasks/<task_name>/ and fills in
instruction.md, task.toml, the input images, the golden solution and the oracle file.
"""
import json
import os
import shutil

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATE = os.path.join(ROOT, "tooling", "harbor_template")
OFFICIAL_PROMPT = os.path.join(ROOT, "tooling", "reference", "official_task5_recon_example.json")
SCORER = os.path.join(ROOT, "tooling", "scorer", "metrics.py")

HARBOR_PREAMBLE = """# SceneActBench · Reconstruction

You are working in a Linux container with a **headless Blender** instance. Control it through the
**`blender` MCP tools** (most importantly `execute_blender_code`, `render_scene_view`,
`get_scene_info`, `get_object_info`). The Blender scene starts empty.

- **Reference images** are in `/app/input/` ({files}).
  Open and look at them; they are your only visual evidence.
- **Your answer is the 3D scene you leave in Blender.** When you finish, the furniture meshes in the
  Blender scene are exported and scored against a hidden 3D ground truth. As a safeguard, also save the
  scene before you stop, by running this with `execute_blender_code`:
  `import bpy; bpy.ops.wm.save_as_mainfile(filepath='/app/output/scene.blend')`

The task instructions follow.

---

"""

TASK_TOML = '''schema_version = "1.4"
artifacts = ["/app/output"]

[task]
name = "sceneactbench/{task_name}"
description = "SceneActBench Reconstruction: rebuild the furniture of a {title_lower} in Blender from {n_views} reference views with known camera poses."
keywords = ["sceneactbench", "3d", "blender", "reconstruction", "vision", "mcp"]

[metadata]
benchmark = "SceneActBench"
task_type = "task5_recon"
sample = "{title}"
source_blend = "{source_blend}"
golden_items = {items}
n_golden_objects = {n_items}
n_reference_views = {n_views}
fov_x_deg = 39.6
step_budget_reference = 35
reward_metric = "obj_f@5%_nn (per-object F-score at 5% of object size, after one global alignment)"
golden_reward = {golden_reward}

[verifier]
timeout_sec = 900.0

[agent]
timeout_sec = 7200.0

[environment]
build_timeout_sec = 1800.0
network_mode = "public"
cpus = 4
memory_mb = 8192
workdir = "/app"

[[environment.mcp_servers]]
name = "blender"
transport = "stdio"
command = "/opt/sceneactbench/blender_mcp_stdio.sh"
args = []

[solution.env]
'''


def white_bg_png(src, dst):
    """Same pixels the SceneActBench harness sends to every model: alpha composited onto white."""
    im = Image.open(src)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, rgba)
    im.convert("RGB").save(dst, format="PNG")


def build_prompt(cameras):
    off = json.load(open(OFFICIAL_PROMPT))
    lines = []
    for i, v in enumerate(cameras["views"]):
        M = v["matrix_world"]
        up = [round(M[r][1], 4) for r in range(3)]
        lines.append(f"  - view {i}: /app/input/render_{i:04d}.png\n"
                     f"      cam pos = {[round(x, 4) for x in v['position']]}, "
                     f"look_dir = {[round(x, 4) for x in v['look_dir']]}, up = {up}")
    n = len(lines)
    head, rest = off["prompt"].split("Reference images and their camera poses (each in the same world frame):\n", 1)
    tail = rest[rest.index("\n\nTreat the "):]
    prompt = (head.replace("from 11 reference images", f"from {n} reference images")
              + "Reference images and their camera poses (each in the same world frame):\n"
              + "\n".join(lines) + tail.replace("Treat the 11 images", f"Treat the {n} images"))
    files = ", ".join(f"`render_{i:04d}.png`" for i in range(n))
    return HARBOR_PREAMBLE.format(files=files) + off["system_prompt"].strip() + "\n\n---\n\n" + prompt.strip() + "\n"


def build_task(task_name, title, golden_glb, golden_file, renders, cameras_json, source_blend,
               item_names, golden_reward, tasks_dir=None):
    task = os.path.join(tasks_dir or os.path.join(ROOT, "tasks"), task_name)
    if os.path.exists(task):
        shutil.rmtree(task)
    for sub in ("environment", "tests", "solution"):
        shutil.copytree(os.path.join(TEMPLATE, sub), os.path.join(task, sub))

    # inputs (agent-visible, baked into the image)
    os.makedirs(os.path.join(task, "environment", "input"))
    for i, r in enumerate(renders):
        white_bg_png(r, os.path.join(task, "environment", "input", f"render_{i:04d}.png"))

    # answer key (tests/ is only copied in at grading time) + scorer + oracle file
    os.makedirs(os.path.join(task, "tests", "golden", "scene"))
    shutil.copy(golden_glb, os.path.join(task, "tests", "golden", "scene", golden_file))
    os.makedirs(os.path.join(task, "tests", "scorer"), exist_ok=True)
    shutil.copy(SCORER, os.path.join(task, "tests", "scorer", "metrics.py"))
    shutil.copy(golden_glb, os.path.join(task, "solution", "golden_scene.glb"))

    shutil.copy(cameras_json, os.path.join(task, "tests", "golden", "cameras.json"))  # for tooling/report.py
    cameras = json.load(open(cameras_json))
    with open(os.path.join(task, "instruction.md"), "w") as f:
        f.write(build_prompt(cameras))
    with open(os.path.join(task, "task.toml"), "w") as f:
        f.write(TASK_TOML.format(task_name=task_name, title=title, title_lower=title.lower(),
                                 n_views=len(cameras["views"]), source_blend=os.path.basename(source_blend),
                                 items=json.dumps(item_names), n_items=len(item_names),
                                 golden_reward=round(golden_reward, 4)))
    return task
