"""Turn a Harbor run of a SceneActBench task into a before/after report.

  python tooling/report.py <harbor trial dir> --task tasks/<task> --out results/<model>/<task>

<harbor trial dir> is one trial folder inside a Harbor job, e.g. jobs/my-job/recon-gaming-room__AbC123
(it contains verifier/score.json and verifier/agent_scene.glb). Needs Blender locally for the renders.

Writes to --out: input_vs_output.png, topdown_overlay.png, agent_scene.glb, score.json, RESULTS.md
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tooling"))
sys.path.insert(0, os.path.join(ROOT, "tooling", "scorer"))
import metrics as M  # noqa: E402
from make_sample import blender_bin  # noqa: E402

RENDER = os.path.join(ROOT, "tooling", "blender", "render_views.py")
PALETTE = [(230, 25, 75), (60, 180, 75), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 170, 170),
           (240, 50, 230), (160, 120, 40), (0, 0, 128), (128, 128, 0), (100, 100, 100), (170, 110, 195)]


def flat(path, size):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    return Image.alpha_composite(bg, im).convert("RGB").resize((size, size))


def input_vs_output(inputs, outputs, score, path, W=520, pad=36):
    n = len(inputs)
    c = Image.new("RGB", (W * n + 10 * (n + 1), 2 * (W + pad) + 10), "white")
    d = ImageDraw.Draw(c)
    d.text((10, 10), "INPUT - the reference images the model was given", fill="black")
    d.text((10, W + pad + 18), f"OUTPUT - the model's reconstruction, same cameras   (reward {score:.3f})", fill="black")
    for i, (a, b) in enumerate(zip(inputs, outputs)):
        c.paste(flat(a, W), (10 + i * (W + 10), pad))
        c.paste(flat(b, W), (10 + i * (W + 10), W + 2 * pad + 10))
    c.save(path)


def topdown(golden_dir, agent_glb, path, S=70):
    Q, parts = M.load_gt_furniture(golden_dir)
    P = M.sample_scene_glb(agent_glb)
    lo = np.minimum(P.min(0), Q.min(0)) - 0.3
    hi = np.maximum(P.max(0), Q.max(0)) + 0.3
    Wd, H = int((hi[0] - lo[0]) * S), int((hi[1] - lo[1]) * S)
    im = Image.new("RGB", (Wd, H + 30), "white")
    d = ImageDraw.Draw(im)
    d.text((8, 8), "Top-down: golden (colour) vs model (black), 1 m grid", fill="black")
    for gx in range(int(np.ceil(lo[0])), int(hi[0]) + 1):
        x = (gx - lo[0]) * S
        d.line([(x, 30), (x, H + 30)], fill=(235, 235, 235))
    for gy in range(int(np.ceil(lo[1])), int(hi[1]) + 1):
        y = H - (gy - lo[1]) * S + 30
        d.line([(0, y), (Wd, y)], fill=(235, 235, 235))
    for a, b in zip((P[::4, 0] - lo[0]) * S, H - (P[::4, 1] - lo[1]) * S):
        d.point((a, b + 30), fill=(40, 40, 40))
    for i, (n, g) in enumerate(parts):
        x, y = (g[::4, 0] - lo[0]) * S, H - (g[::4, 1] - lo[1]) * S
        col = PALETTE[i % len(PALETTE)]
        for a, b in zip(x, y):
            d.point((a, b + 30), fill=col)
        d.text((x.mean() + 4, y.mean() + 30), n, fill=col)
    im.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("trial_dir")
    ap.add_argument("--task", required=True, help="tasks/<task> (the Harbor task that was run)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=None, help="model name for the write-up")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    golden_src = os.path.join(a.task, "tests", "golden")
    score = json.load(open(os.path.join(a.trial_dir, "verifier", "score.json")))
    agent_glb = os.path.join(a.trial_dir, "verifier", "agent_scene.glb")
    shutil.copy(agent_glb, os.path.join(a.out, "agent_scene.glb"))
    shutil.copy(os.path.join(a.trial_dir, "verifier", "score.json"), os.path.join(a.out, "score.json"))
    summary_p = os.path.join(a.trial_dir, "agent", "run_summary.json")
    summary = json.load(open(summary_p)) if os.path.isfile(summary_p) else {}

    subprocess.run([blender_bin(), "-b", "--factory-startup", "--python", RENDER, "--", agent_glb,
                    os.path.join(golden_src, "cameras.json"), a.out, "model"], capture_output=True)
    inputs = sorted(glob.glob(os.path.join(a.task, "environment", "input", "render_*.png")))
    outputs = [os.path.join(a.out, f"model_view{i}.png") for i in range(len(inputs))]
    input_vs_output(inputs, outputs, score["reward"], os.path.join(a.out, "input_vs_output.png"))
    topdown(golden_src, agent_glb, os.path.join(a.out, "topdown_overlay.png"))

    model = a.model or summary.get("model", "model")
    rows = "\n".join(f"| {p['part']} | {p['f@5%']:.2f} | {p['precision']:.2f} | {p['recall']:.2f} |"
                     for p in score.get("per_object", []))
    md = f"""# {os.path.basename(os.path.normpath(a.task))} — {model}

**Reward: {score['reward']:.3f}** (per-object F@5%, average over golden items) · golden solution: 1.000

| Run | |
|---|---|
| Steps | {summary.get('num_steps', '?')} (stopped on its own: {summary.get('finished', '?')}) |
| Time | {summary.get('elapsed_sec', '?')} s |
| Whole-room F@5% | {score.get('scene_f@5%', float('nan')):.2f} (precision {score.get('scene_precision@5%', float('nan')):.2f}, recall {score.get('scene_recall@5%', float('nan')):.2f}) |

![Input vs output](input_vs_output.png)

| Item | F@5% | Precision | Recall |
|---|---|---|---|
{rows}

![Top-down](topdown_overlay.png)
"""
    open(os.path.join(a.out, "RESULTS.md"), "w").write(md)
    print(f"report written to {a.out}")


if __name__ == "__main__":
    main()
