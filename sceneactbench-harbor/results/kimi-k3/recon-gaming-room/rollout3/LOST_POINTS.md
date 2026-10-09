# recon-gaming-room — Kimi K3 — rollout3: where the points were lost

**Reward 0.325.** Each item scores 0–1 (F-score: precision = how much of what Kimi built for it sits on the real item, recall = how much of the real item Kimi covered, within 5% of the item's size).

**Alignment:** before scoring, the scorer turned Kimi's whole room **-11°**, tilted it **2°** and scaled it **×1.16**. All positions below are after that, in the golden room's frame (*front* = the side the cameras look from, *back wall* = where the TV is). With no alignment this rollout would score **0.330**.

| Item | Score | Precision | Recall | What went wrong |
|---|---|---|---|---|
| Sofa | 0.76 | 0.73 | 0.80 | centre off by 0.32 m (0.3 m left, 0.2 m toward the front) |
| Cabinet | 0.45 | 0.66 | 0.34 | centre off by 0.26 m (0.2 m right, 0.2 m too low) |
| Chair | 0.30 | 0.32 | 0.28 | centre off by 0.41 m (0.4 m toward the back wall, 0.7 m too low) |
| TV | 0.30 | 0.43 | 0.23 | centre off by 0.46 m (0.4 m right, 0.3 m too high) |
| Desk | 0.26 | 0.64 | 0.16 | centre off by 0.41 m (0.4 m toward the front); turned ~90°; its points landed mostly on Chair (30%) |
| Monitor_L | 0.21 | 0.38 | 0.14 | centre off by 1.00 m (1.0 m left, 0.3 m toward the back wall, 0.3 m too low); 1.6× too small; turned ~90°; its points landed mostly on Desk (100%) |
| Monitor_R | 0.00 | 0.00 | 0.00 | centre off by 1.37 m (1.4 m toward the front, 0.4 m too low); 1.6× too small; turned ~90°; its points landed mostly on Desk (64%), Monitor_L (36%) |

Pictures: `../rollouts_vs_golden.png` (golden vs each rollout from the same 3 cameras, plus each rollout's top-down view as the scorer sees it).
