# recon-living-room — Kimi K3 — rollout3: where the points were lost

**Reward 0.080.** Each item scores 0–1 (F-score: precision = how much of what Kimi built for it sits on the real item, recall = how much of the real item Kimi covered, within 5% of the item's size).

**Alignment:** before scoring, the scorer turned Kimi's whole room **-75°**, tilted it **13°** and scaled it **×0.68**. All positions below are after that, in the golden room's frame (*front* = the side the cameras look from, *back wall* = where the TV is). With no alignment this rollout would score **0.082**.

| Item | Score | Precision | Recall | What went wrong |
|---|---|---|---|---|
| Sofa | 0.41 | 0.76 | 0.28 | centre off by 1.45 m (1.4 m left, 0.5 m toward the front); 2.3× too small |
| Shelf | 0.25 | 0.50 | 0.17 | centre off by 0.91 m (0.7 m right, 0.6 m toward the front, 0.5 m too high) |
| TV_Stand | 0.14 | 0.11 | 0.20 | centre off by 1.70 m (1.3 m right, 1.0 m toward the front, 0.3 m too low); 1.4× too small; turned ~90°; its points landed mostly on Sofa (65%) |
| Pendant | 0.06 | 0.04 | 0.07 | centre off by 0.37 m (0.4 m right, 0.3 m too low); 1.4× too small |
| Plant | 0.03 | 0.07 | 0.02 | centre off by 1.38 m (1.3 m right, 0.3 m toward the back wall, 0.2 m too high); 1.8× too small; its points landed mostly on Shelf (80%), Sofa (20%) |
| TV | 0.00 | 0.00 | 0.00 | centre off by 1.79 m (1.3 m right, 1.2 m toward the front, 0.8 m too low); 1.5× too small; turned ~90°; its points landed mostly on Sofa (72%), TV_Stand (25%) |
| Table | 0.00 | 0.00 | 0.00 | Kimi did not build this item |
| Piano | 0.00 | 0.00 | 0.00 | centre off by 3.81 m (3.0 m right, 2.3 m toward the back wall, 0.2 m too low); its points landed mostly on TV_Stand (99%) |
| Lamp_Standing | 0.00 | 0.00 | 0.00 | centre off by 2.20 m (0.6 m right, 2.1 m toward the back wall, 0.4 m too low); its points landed mostly on Bench (100%) |
| Lamp_Arc | 0.00 | 0.00 | 0.00 | centre off by 4.98 m (2.3 m left, 4.4 m toward the front, 0.3 m too high); 1.3× too small; its points landed mostly on Plant (100%) |
| Bench | 0.00 | 0.00 | 0.00 | centre off by 3.95 m (2.4 m right, 3.1 m toward the back wall, 0.3 m too low); 1.6× too small; its points landed mostly on TV_Stand (66%), Table (34%) |

Pictures: `../rollouts_vs_golden.png` (golden vs each rollout from the same 3 cameras, plus each rollout's top-down view as the scorer sees it).
