# recon-living-room — Kimi K3 — rollout1: where the points were lost

**Reward 0.136.** Each item scores 0–1 (F-score: precision = how much of what Kimi built for it sits on the real item, recall = how much of the real item Kimi covered, within 5% of the item's size).

**Alignment:** before scoring, the scorer turned Kimi's whole room **-16°**, tilted it **7°** and scaled it **×0.90**. All positions below are after that, in the golden room's frame (*front* = the side the cameras look from, *back wall* = where the TV is). With no alignment this rollout would score **0.117**.

**Note:** Kimi's furniture in this rollout is built from loose panels and cushions that are not assembled (see the renders). Replaying Kimi's exact code reproduces the graded scene (4 mm average gap), so this is what Kimi built, not an export problem.

| Item | Score | Precision | Recall | What went wrong |
|---|---|---|---|---|
| Sofa | 0.43 | 0.53 | 0.36 | centre off by 0.81 m (0.8 m left, 0.2 m toward the back wall); 1.3× too small; its points landed mostly on Table (40%) |
| Shelf | 0.33 | 0.76 | 0.21 | centre off by 0.74 m (0.6 m left, 0.4 m toward the front, 0.4 m too low); 1.5× too big; its points landed mostly on Plant (30%) |
| Plant | 0.33 | 0.50 | 0.25 | centre off by 2.06 m (2.1 m right); its points landed mostly on Shelf (90%) |
| Table | 0.29 | 0.23 | 0.41 | centre off by 0.58 m (0.6 m toward the front, 0.2 m too low); its points landed mostly on Sofa (30%) |
| Pendant | 0.06 | 0.05 | 0.08 | centre off by 0.44 m (0.4 m toward the back wall); 1.9× too big; turned ~90° |
| Bench | 0.02 | 0.04 | 0.01 | centre off by 0.95 m (0.2 m left, 0.9 m toward the back wall, 0.5 m too low); 1.6× too small |
| Lamp_Arc | 0.02 | 0.40 | 0.01 | centre off by 1.72 m (1.7 m toward the front, 0.3 m too high); its points landed mostly on Sofa (100%) |
| TV_Stand | 0.00 | 0.00 | 0.00 | centre off by 1.18 m (0.8 m right, 0.9 m toward the front, 0.3 m too low); 1.3× too big; its points landed mostly on Sofa (38%) |
| TV | 0.00 | 0.00 | 0.00 | centre off by 1.00 m (0.2 m left, 1.0 m toward the front, 0.3 m too low); 1.3× too small; its points landed mostly on TV_Stand (100%) |
| Piano | 0.00 | 0.00 | 0.00 | centre off by 1.36 m (0.6 m left, 1.2 m toward the front, 0.3 m too low); its points landed mostly on Bench (76%) |
| Lamp_Standing | 0.00 | 0.00 | 0.00 | centre off by 1.74 m (0.6 m right, 1.6 m toward the back wall, 0.4 m too low); its points landed mostly on Bench (100%) |

Pictures: `../rollouts_vs_golden.png` (golden vs each rollout from the same 3 cameras, plus each rollout's top-down view as the scorer sees it).
