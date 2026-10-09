# recon-gaming-room — Kimi K3 — rollout2: where the points were lost

**Reward 0.190.** Each item scores 0–1 (F-score: precision = how much of what Kimi built for it sits on the real item, recall = how much of the real item Kimi covered, within 5% of the item's size).

**Alignment:** before scoring, the scorer turned Kimi's whole room **-66°**, tilted it **18°** and scaled it **×1.07**. All positions below are after that, in the golden room's frame (*front* = the side the cameras look from, *back wall* = where the TV is). With no alignment this rollout would score **0.085**.

| Item | Score | Precision | Recall | What went wrong |
|---|---|---|---|---|
| Monitor_R | 0.50 | 0.53 | 0.48 | Kimi built ONE wide curved monitor instead of two; it partly covers this one's spot |
| Desk | 0.44 | 0.53 | 0.37 | centre off by 0.54 m (0.4 m right, 0.4 m toward the front) |
| Monitor_L | 0.33 | 0.52 | 0.24 | Kimi built ONE wide curved monitor instead of two; centre off by 0.67 m (0.3 m right, 0.6 m toward the back wall); its points landed mostly on Monitor_R (45%) |
| Sofa | 0.05 | 0.05 | 0.06 | centre off by 1.64 m (1.6 m right, 0.3 m toward the back wall, 0.5 m too high) |
| TV | 0.00 | 0.00 | 0.00 | centre off by 0.60 m (0.4 m right, 0.4 m toward the front) |
| Chair | 0.00 | 0.00 | 0.00 | centre off by 1.91 m (1.0 m right, 1.6 m toward the back wall, 0.5 m too low); its points landed mostly on Desk (100%) |
| Cabinet | 0.00 | 0.00 | 0.00 | centre off by 1.84 m (1.3 m left, 1.3 m toward the front, 0.6 m too low); its points landed mostly on Sofa (52%) |

Pictures: `../rollouts_vs_golden.png` (golden vs each rollout from the same 3 cameras, plus each rollout's top-down view as the scorer sees it).
