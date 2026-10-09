# SceneActBench Reconstruction — Harbor edition

Reconstruction tasks from [SceneActBench](https://arxiv.org/abs/2607.22393), packaged as
[Harbor](https://github.com/laude-institute/harbor) tasks, plus the tooling to make your own.

**The task:** an agent gets 3 pictures of a furnished room (with the exact camera positions) and an empty
Blender. It must rebuild every piece of furniture in 3D. The scene it leaves in Blender is scored against a
hidden 3D answer key. Scoring is pure geometry, with no LLM judge.

## Samples

| Task | Room | Items | Golden solution | Kimi K3 (Harbor) |
|---|---|---|---|---|
| `tasks/recon-living-room` | Living room (`samples/living-room`) | 11 | 1.000 | **0.136** |
| `tasks/recon-gaming-room` | Gaming room (`samples/gaming-room`) | 7 | 1.000 | **0.121** |

Reward = average per-item F-score (0–1). Before/after pictures and per-item scores: [`results/`](results/README.md).
Single runs vary: Kimi K3 has scored 0.121, 0.161 and 0.273 on the gaming room across three runs.

## Quick start: run a task

You need [Harbor](https://github.com/laude-institute/harbor), Docker, and an API key for a vision model.
Docker installs Blender and everything else inside the task.

```bash
# sanity checks: the answer key must score ~1.0, doing nothing must score 0
harbor run -p tasks/recon-gaming-room -a oracle
harbor run -p tasks/recon-gaming-room -a nop

# run a model with the included SceneActBench agent (any OpenAI-compatible API)
export VERCEL_AI_GATEWAY_API_KEY=...
PYTHONPATH=agents harbor run -p tasks/recon-gaming-room \
    -a sceneactbench_agent.harbor_agent:SceneActBenchAgent -m moonshotai/kimi-k3
```

The reward is in the Harbor job folder (`<trial>/verifier/reward.txt`), with per-item detail in
`<trial>/verifier/score.json`. To get the before/after picture and score table:

```bash
python tooling/report.py jobs/<job>/<trial> --task tasks/recon-gaming-room --out results/<model>/recon-gaming-room
```

### Which agent?
- **`agents/sceneactbench_agent`** (recommended) is the original SceneActBench agent loop, packaged as a Harbor
  agent. It works with any OpenAI-compatible endpoint; see [`agents/sceneactbench_agent/README.md`](agents/sceneactbench_agent/README.md)
  for other providers. It sends images in a way every provider accepts.
- **Other Harbor agents** also work if they support MCP tools *and* can view images. Each task declares a
  `blender` MCP server in `task.toml`. Check that your model provider accepts images inside tool results;
  the Vercel AI Gateway, for example, silently drops them.

## Make your own sample

Bring a `.blend` of a furnished room, write a short `scene.json` saying which objects make up each piece of
furniture, and run one command:

```bash
pip install -r requirements.txt              # plus Blender 4.2+ installed locally
python tooling/make_sample.py --list samples/my-room/my_room.blend
python tooling/make_sample.py samples/my-room/scene.json     # -> tasks/recon-my-room
harbor run -p tasks/recon-my-room -a oracle  # ~1.0
harbor run -p tasks/recon-my-room -a nop     # 0.0
```

Step-by-step guide: **[CONTRIBUTING.md](CONTRIBUTING.md)**.

## Repository layout

```
samples/<name>/            scene.json + the source .blend (what a contributor provides)
tasks/recon-<name>/        generated Harbor tasks (what you run)
  instruction.md             agent prompt: official SceneActBench Reconstruction prompt + the 3 views
  task.toml                  timeouts, resources, the `blender` MCP server
  environment/               Dockerfile (Ubuntu + Blender 5.0.1 + blender-mcp) and the 3 input images
  solution/                  oracle: loads the golden solution into Blender
  tests/                     verifier + hidden answer key (copied in only at grading time)
agents/sceneactbench_agent/ Harbor agent: the SceneActBench loop, for OpenAI-compatible models
tooling/
  make_sample.py             .blend + scene.json -> golden solution, input views, Harbor task, checks
  report.py                  Harbor run -> before/after picture + score table
  verify.py                  score any .glb against a task offline
  scorer/metrics.py          the scorer (same file as tasks/*/tests/scorer/)
  harbor_template/           files copied into every task (environment, tests, solution)
  blender/                   Blender-side scripts used by the tools
results/kimi-k3/            Kimi K3 results on the two samples
docs/SCENEACTBENCH_OVERVIEW.md  benchmark description, scoring details, quality checklist
validation/                 oracle / nop check results for the shipped tasks
```

## How a task runs
1. **Environment.** The container has Blender and the `blender` MCP server (`execute_blender_code`,
   `render_scene_view`, `get_scene_info`, …). Blender starts headless on first use.
2. **Agent.** It reads `instruction.md`, looks at `/app/input/render_000{0,1,2}.png`, builds the furniture in
   Blender, renders to compare, and iterates.
3. **Answer.** Whatever meshes are in the Blender scene when the agent stops. Blender also autosaves after
   every command, so grading works even if Blender exits with the agent.
4. **Verifier.** Exports the scene (meshes only, modifiers applied), scores it, and writes the reward.

## Scoring
`reward = obj_f@5%_nn`, from 0 to 1:
1. The agent's scene is aligned to the answer key once, as a whole (scale, rotation, position).
2. Each point on the agent's surfaces is assigned to the nearest answer-key item.
3. Each item gets an F-score at a tolerance of 5% of its own size. Precision is the share of points
   assigned to it that lie on its surface; recall is the share of its surface that is covered.
4. The reward is the average over items. Missing items score 0; an empty scene scores 0.

This is the SceneActBench Reconstruction scorer with corrections. Without them, an exact copy of the answer
key scored only 18–24 / 100:
- the answer key is converted from Y-up to Blender's Z-up;
- surfaces are sampled evenly instead of using mesh vertices;
- the agent's modifiers are applied;
- items are matched by nearest surface instead of clustering, which merged touching furniture;
- every item in the answer key is scored, with no name filter.

Details: [`docs/SCENEACTBENCH_OVERVIEW.md`](docs/SCENEACTBENCH_OVERVIEW.md).

## Notes
- The image is `linux/amd64` because Blender only ships x64 Linux builds. On Apple Silicon it runs under
  emulation, so the agent's preview renders take about 15 s.
- The official benchmark gives Reconstruction 35 agent steps (the default of the included agent). The task
  time limit is 2 hours.
- The blender-mcp server's telemetry is switched off inside the container.

## Credits
SceneActBench: Zhao et al., 2026, [arXiv:2607.22393](https://arxiv.org/abs/2607.22393); harness MIT,
dataset CC BY-NC 4.0. blender-mcp: MIT. The sample `.blend` files are third-party downloads; check their
licences before redistributing.
