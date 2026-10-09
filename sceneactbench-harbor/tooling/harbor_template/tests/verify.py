"""SceneActBench Reconstruction verifier (corrected scorer).

Reward = per-object F@5% (obj_f@5%_nn): one global similarity alignment, each predicted
surface point assigned to its nearest golden object, F-score per object at a tolerance
of 5% of that object's size, averaged over golden objects. Golden solution scores 1.0.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scorer"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", required=True, help="dir containing scene/*_full.glb")
    ap.add_argument("--pred", required=True, help="agent scene .glb (Blender export, Z-up)")
    ap.add_argument("--reward", required=True)
    ap.add_argument("--details", required=True)
    a = ap.parse_args()

    reward, details = 0.0, {}
    try:
        if not (os.path.isfile(a.pred) and os.path.getsize(a.pred) > 0):
            raise FileNotFoundError("no agent scene to score")
        import metrics as M
        Q, parts = M.load_gt_furniture(a.golden)
        P = M.sample_scene_glb(a.pred)
        if len(P) == 0:
            raise ValueError("agent scene has no mesh surface")
        sc = M.score_reconstruction(P, Q, gt_parts=parts)
        reward = float(min(max(sc["obj_f@5%_nn"], 0.0), 1.0))
        details = {
            "reward": reward,
            "headline_obj_f@5%_nn": sc["obj_f@5%_nn"],
            "per_object": sc["per_object_nn"],
            "scene_f@5%": sc["scene_f@5%"],
            "scene_precision@5%": sc["scene_prec@5%"],
            "scene_recall@5%": sc["scene_recall@5%"],
            "scene_f@10%": sc.get("f@10%"),
            "mean_pos_err_m": sc.get("mean_pos_err"),
            "legacy_obj_f@5%_matched": sc.get("obj_f@5%_matched"),
        }
    except Exception as e:  # any failure scores 0
        details = {"reward": 0.0, "error": repr(e)}
    os.makedirs(os.path.dirname(a.reward), exist_ok=True)
    open(a.reward, "w").write(f"{reward:.4f}\n")
    json.dump(details, open(a.details, "w"), indent=1, default=float)
    print(json.dumps({k: v for k, v in details.items() if k != "per_object"}, default=float))
    for p in details.get("per_object", []):
        print(f"  {p['part']:<16s} F={p['f@5%']:.2f}  P={p['precision']:.2f}  R={p['recall']:.2f}")


if __name__ == "__main__":
    main()
