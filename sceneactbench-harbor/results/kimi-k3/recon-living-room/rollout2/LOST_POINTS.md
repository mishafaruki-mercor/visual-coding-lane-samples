# recon-living-room — Kimi K3 — rollout2: where the points were lost

**Reward 0.112.** Each item scores 0–1 (F-score: precision = how much of what Kimi built for it sits on the real item, recall = how much of the real item Kimi covered, within 5% of the item's size).

**Alignment:** before scoring, the scorer turned Kimi's whole room **-55°**, tilted it **18°** and scaled it **×0.69**. All positions below are after that, in the golden room's frame (*front* = the side the cameras look from, *back wall* = where the TV is). With no alignment this rollout would score **0.201**.

| Item | Score | Precision | Recall | What went wrong |
|---|---|---|---|---|
| Shelf | 0.44 | 0.62 | 0.34 | centre off by 1.45 m (1.4 m left, 0.3 m toward the front, 0.4 m too high); its points landed mostly on Plant (57%) |
| Sofa | 0.34 | 0.53 | 0.25 | centre off by 1.26 m (0.5 m right, 1.2 m toward the front, 0.3 m too high); 1.8× too small; its points landed mostly on Shelf (58%) |
| Table | 0.20 | 0.14 | 0.32 | centre off by 2.15 m (2.1 m right, 0.3 m toward the front, 0.3 m too low); its points landed mostly on Sofa (100%) |
| Plant | 0.15 | 0.14 | 0.15 | centre off by 0.52 m (0.2 m left, 0.5 m toward the back wall, 0.6 m too high); 1.5× too small |
| Bench | 0.10 | 0.67 | 0.05 | centre off by 1.58 m (1.1 m right, 1.1 m toward the back wall, 0.2 m too low); 1.3× too small; its points landed mostly on Sofa (52%), Piano (48%) |
| TV_Stand | 0.00 | 0.00 | 0.00 | centre off by 4.17 m (0.5 m right, 4.1 m toward the front); 2.2× too small; its points landed mostly on Sofa (92%) |
| TV | 0.00 | 0.00 | 0.00 | centre off by 3.92 m (2.9 m right, 2.7 m toward the front, 0.8 m too low); 1.3× too small; turned ~90°; its points landed mostly on Sofa (100%) |
| Piano | 0.00 | 0.00 | 0.00 | centre off by 2.60 m (2.6 m right, 0.5 m toward the front, 0.4 m too low); its points landed mostly on Table (100%) |
| Pendant | 0.00 | 0.00 | 0.00 | placed about right; 1.3× too small |
| Lamp_Standing | 0.00 | 0.00 | 0.00 | centre off by 2.40 m (0.4 m left, 2.4 m toward the back wall); 1.7× too big; its points landed mostly on Bench (67%), Piano (33%) |
| Lamp_Arc | 0.00 | 0.00 | 0.00 | centre off by 3.25 m (3.3 m toward the front, 0.4 m too high); its points landed mostly on Shelf (100%) |

Pictures: `../rollouts_vs_golden.png` (golden vs each rollout from the same 3 cameras, plus each rollout's top-down view as the scorer sees it).
