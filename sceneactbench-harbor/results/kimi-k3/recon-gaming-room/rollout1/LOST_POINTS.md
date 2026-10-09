# recon-gaming-room — Kimi K3 — rollout1: where the points were lost

**Reward 0.121.** Each item scores 0–1 (F-score: precision = how much of what Kimi built for it sits on the real item, recall = how much of the real item Kimi covered, within 5% of the item's size).

**Alignment:** before scoring, the scorer turned Kimi's whole room **+174°**, tilted it **13°** and scaled it **×0.80**. All positions below are after that, in the golden room's frame (*front* = the side the cameras look from, *back wall* = where the TV is). With no alignment this rollout would score **0.240**.

| Item | Score | Precision | Recall | What went wrong |
|---|---|---|---|---|
| Cabinet | 0.40 | 0.47 | 0.34 | centre off by 4.51 m (0.3 m right, 4.5 m toward the front, 0.5 m too low); turned ~90°; its points landed mostly on Desk (91%) |
| Sofa | 0.29 | 0.50 | 0.20 | centre off by 0.91 m (0.9 m right, 0.5 m too low) |
| Desk | 0.16 | 0.25 | 0.12 | centre off by 5.88 m (1.8 m left, 5.6 m toward the back wall); 1.4× too big; turned ~90°; its points landed mostly on Cabinet (100%) |
| Chair | 0.00 | 0.00 | 0.00 | centre off by 6.55 m (1.9 m right, 6.3 m toward the back wall, 0.8 m too low); 1.8× too small; its points landed mostly on Cabinet (100%) |
| TV | 0.00 | 0.00 | 0.00 | centre off by 5.16 m (0.5 m right, 5.1 m toward the front, 1.0 m too low); 2.3× too big; turned ~90°; its points landed mostly on Desk (71%) |
| Monitor_R | 0.00 | 0.00 | 0.00 | centre off by 5.42 m (2.3 m left, 4.9 m toward the back wall, 0.2 m too low); 2.9× too small; turned ~90°; its points landed mostly on TV (72%), Cabinet (28%) |
| Monitor_L | 0.00 | 0.00 | 0.00 | centre off by 6.52 m (1.8 m left, 6.3 m toward the back wall, 0.5 m too low); turned ~90°; its points landed mostly on Cabinet (92%) |

Pictures: `../rollouts_vs_golden.png` (golden vs each rollout from the same 3 cameras, plus each rollout's top-down view as the scorer sees it).
