# Results

All rewards use the corrected scorer (`tooling/scorer/metrics.py`); the golden solution scores 1.000 on both
tasks. Each folder has `RESULTS.md` (score table), `input_vs_output.png` (the 3 input views vs the model's
build from the same cameras), `topdown_overlay.png`, the model's `agent_scene.glb`, `score.json` and
`trajectory_steps.json` (every step the agent took).

## Kimi K3 (`moonshotai/kimi-k3` via Vercel AI Gateway)

| Task | Run | Reward | Steps | Time | Folder |
|---|---|---|---|---|---|
| Gaming room | **Harbor, final task version** | **0.121** | 28 (stopped on its own) | 12.5 min | `kimi-k3/recon-gaming-room/harbor/` |
| Gaming room | Harbor, earlier task version | 0.273 | 15 (stopped on its own) | 7.5 min | `kimi-k3/recon-gaming-room/harbor_earlier/` |
| Gaming room | Original SceneActBench runner | 0.161 | 35 (limit) | 11 min | `kimi-k3/recon-gaming-room/original_runner/` |
| Living room | **Harbor** | **0.136** | 35 (limit) | 20 min | `kimi-k3/recon-living-room/harbor/` |
| Living room | Original SceneActBench runner | 0.128 | 35 (limit) | 14 min | `kimi-k3/recon-living-room/original_runner/` |

- All runs: no harness exceptions, no Blender crashes, no attempts to read the answer key.
- The two Harbor gaming-room runs used identical inputs, prompt, answer key, 2-hour limit and 65k-token
  output cap. The only difference is that the final run used streaming replies, which avoids gateway drops
  on long first steps. The gap between 0.273 and 0.121 is run-to-run variation.
- Spread across the three gaming-room runs: 0.12–0.27. Single runs are noisy; average several before
  comparing models.
