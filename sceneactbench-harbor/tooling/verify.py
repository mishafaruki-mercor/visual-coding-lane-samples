"""Score any reconstruction .glb against a task's golden solution (same scorer as the Harbor verifier).

  python tooling/verify.py tasks/recon-gaming-room --pred my_scene.glb      # score a reconstruction
  python tooling/verify.py tasks/recon-gaming-room --golden-check           # golden vs itself, must be >= 0.95

The .glb should be a Blender export (Z-up, as the Harbor verifier and the SceneActBench harness produce).
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scorer"))
import metrics as M  # noqa: E402


def per_item_no_alignment(P, parts):
    """Same per-item F@5% as the reward, but on the model's own coordinates (no alignment)."""
    Qp = [np.asarray(g) for _, g in parts]
    owner = np.concatenate([np.full(len(g), i) for i, g in enumerate(Qp)])
    _, nn = cKDTree(np.vstack(Qp)).query(P)
    lab = owner[nn]
    fs = []
    for i, g in enumerate(Qp):
        pp = P[lab == i]
        tau = 0.05 * np.linalg.norm(g.max(0) - g.min(0))
        fs.append(M.f_score(pp, g, tau)["fscore"] if len(pp) >= 10 else 0.0)
    return float(np.mean(fs))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("task_dir", help="tasks/<task>")
    ap.add_argument("--pred", help="reconstruction .glb to score")
    ap.add_argument("--golden-check", action="store_true", help="score the golden solution against itself")
    ap.add_argument("--json", help="also write the full score dict here")
    a = ap.parse_args()

    golden_dir = os.path.join(a.task_dir, "tests", "golden")
    golden_glb = os.path.join(a.task_dir, "solution", "golden_scene.glb")
    if a.golden_check:
        pred = golden_glb
    elif a.pred:
        pred = a.pred
    else:
        ap.error("give --pred <file.glb> or --golden-check")

    Q, parts = M.load_gt_furniture(golden_dir)
    P = M.sample_scene_glb(pred)
    sc = M.score_reconstruction(P, Q, gt_parts=parts)

    print(f"task   : {os.path.basename(os.path.normpath(a.task_dir))}")
    print(f"scored : {pred}")
    print(f"\nREWARD  per-object F@5% (obj_f@5%_nn) = {sc['obj_f@5%_nn']:.3f}")
    print("\nper item                F@5%   precision  recall  tolerance")
    for p, (_, g) in zip(sc["per_object_nn"], parts):
        tol = 5 * np.linalg.norm(g.max(0) - g.min(0))
        print(f"  {p['part']:<20s} {p['f@5%']:.2f}    {p['precision']:.2f}       {p['recall']:.2f}    {tol:.0f} cm")
    diag = np.linalg.norm(Q.max(0) - Q.min(0))
    print(f"\nwhole room  F@5% (tol {diag * 5:.0f} cm) = {sc['scene_f@5%']:.2f}"
          f"  (precision {sc['scene_prec@5%']:.2f}, recall {sc['scene_recall@5%']:.2f})")
    if a.golden_check:
        print(f"\ngolden check: {'PASS' if sc['obj_f@5%_nn'] >= 0.95 else 'FAIL'} (needs >= 0.95)")
    else:
        print(f"\ncheck: same metric with NO alignment = {per_item_no_alignment(P, parts):.3f}"
              " (alignment should never lower the reward)")
    if a.json:
        json.dump(sc, open(a.json, "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
