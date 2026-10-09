# Results

All rewards use the corrected scorer (`tooling/scorer/metrics.py`); the golden solution scores 1.000 on both
tasks. Each rollout folder has `RESULTS.md` (score table), `input_vs_output.png` (the 3 input views vs the
model's build from the same cameras), `topdown_overlay.png`, the model's `agent_scene.glb`, `score.json` and
`trajectory_steps.json` (every step the agent took).

## Kimi K3 — 3 rollouts per task (Harbor)

Model `moonshotai/kimi-k3` via the Vercel AI Gateway, with the SceneActBench agent (35 steps, 65k output tokens,
streamed replies) and identical task versions for all rollouts.

| Task | rollout1 | rollout2 | rollout3 | **Average** | Spread (std) |
|---|---|---|---|---|---|
| Gaming room (7 items) | 0.121 | 0.190 | 0.325 | **0.212** | 0.104 |
| Living room (11 items) | 0.136 | 0.112 | 0.080 | **0.109** | 0.028 |
| **Both tasks (6 rollouts)** | | | | **0.161** | |

| Task | Rollout | Reward | Steps | Stopped on its own | Time | Folder |
|---|---|---|---|---|---|---|
| Gaming room | rollout1 | 0.121 | 28 | yes | 12.5 min | `kimi-k3/recon-gaming-room/rollout1/` |
| Gaming room | rollout2 | 0.190 | 13 | yes | 15.6 min | `kimi-k3/recon-gaming-room/rollout2/` |
| Gaming room | rollout3 | 0.325 | 16 | yes | 8.6 min | `kimi-k3/recon-gaming-room/rollout3/` |
| Living room | rollout1 | 0.136 | 35 | no (step limit) | 20.1 min | `kimi-k3/recon-living-room/rollout1/` |
| Living room | rollout2 | 0.112 | 35 | no (step limit) | 12.2 min | `kimi-k3/recon-living-room/rollout2/` |
| Living room | rollout3 | 0.080 | 30 | yes | 14.3 min | `kimi-k3/recon-living-room/rollout3/` |

All 6 rollouts: no harness exceptions, no Blender crashes, scene taken from the live Blender, no attempts to read
the answer key. One rollout had a single empty first reply that was retried automatically.

### Per-item score, averaged over the 3 rollouts

| Gaming room | r1 | r2 | r3 | Avg |
|---|---|---|---|---|
| Sofa | 0.29 | 0.05 | 0.76 | 0.37 |
| Desk | 0.16 | 0.44 | 0.26 | 0.29 |
| Cabinet | 0.40 | 0.00 | 0.45 | 0.28 |
| Monitor (left) | 0.00 | 0.33 | 0.21 | 0.18 |
| Monitor (right) | 0.00 | 0.50 | 0.00 | 0.17 |
| Chair | 0.00 | 0.00 | 0.30 | 0.10 |
| TV | 0.00 | 0.00 | 0.30 | 0.10 |

| Living room | r1 | r2 | r3 | Avg |
|---|---|---|---|---|
| Sofa | 0.43 | 0.34 | 0.41 | 0.39 |
| Shelf | 0.33 | 0.44 | 0.25 | 0.34 |
| Plant | 0.33 | 0.15 | 0.03 | 0.17 |
| Coffee table | 0.29 | 0.20 | 0.00 | 0.16 |
| TV stand | 0.00 | 0.00 | 0.14 | 0.05 |
| Bench | 0.02 | 0.10 | 0.00 | 0.04 |
| Pendant | 0.06 | 0.00 | 0.06 | 0.04 |
| Arc lamp | 0.02 | 0.00 | 0.00 | 0.01 |
| TV | 0.00 | 0.00 | 0.00 | 0.00 |
| Piano | 0.00 | 0.00 | 0.00 | 0.00 |
| Standing lamp | 0.00 | 0.00 | 0.00 | 0.00 |

The large pieces near the middle of the room (sofa, shelf, desk) are partly right in most rollouts. Wall-mounted
and edge pieces (TV, piano, lamps) are almost never in the right place.

## Other runs (not in the average)

| Task | Run | Reward | Folder |
|---|---|---|---|
| Gaming room | Earlier Harbor run (before streaming was added) | 0.273 | `kimi-k3/recon-gaming-room/extra_run_not_averaged/` |
| Gaming room | Original SceneActBench runner | 0.161 | `kimi-k3/recon-gaming-room/original_runner/` |
| Living room | Original SceneActBench runner | 0.128 | `kimi-k3/recon-living-room/original_runner/` |
