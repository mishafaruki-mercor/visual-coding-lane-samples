# BVB Sandbox for Stage-1 Agent Runs

Mini-BVB is the shared harness for programmatic video reconstruction. Stage 1
produces an animated `result.blend` for each source video. Stage 2 renders the
submission and scores it on two axes, **Dual VQA** and **Latent Similarity**,
abbreviated DV and LS. Their square-root mean is **Overall**. Scoring runs
separately from the agent loop.

```text
Source video → Mini-BVB agent → animated result.blend
                 ↕                       ↓
          Blender sandbox          camera render
                                  ↙             ↘
                              Dual VQA     Latent Similarity
                                  ↘             ↙
                                      Overall
```

The agent runs on the host and controls a fresh Blender container through
`docker exec`. Every configuration uses the same prompt, tools, sandbox, and
per-scene cost limit. External asset libraries are not allowed.

## 1. One-time setup

The host needs Python 3.10+, Docker, and `ffmpeg`/`ffprobe`. The Docker image
provides Ubuntu 22.04, Blender 4.2, Python, Xvfb, and FFmpeg. Run the following
commands from the `sandbox/` directory.

```bash
docker build -t bvb-sandbox:latest .
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Inside the container, `blender_run --python script.py` is a wrapper around
`xvfb-run -a blender --background`.

Place the source videos at `../VSI-Bench/<dataset>/<scene>.mp4` as described in
the [repository README](../README.md#1-prepare-the-source-videos). The task
loader reads the 288 scene IDs and dataset names directly from
`../eval/test.jsonl`. It never shows the questions or answers to the agent.

## 2. Reconstruct videos

Set the API key for your model's provider, such as `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, or `GEMINI_API_KEY`.

```bash
export OPENAI_API_KEY="..."
.venv/bin/python run_agent.py \
  --model gpt-6-astra \
  --reasoning high \
  --output results/run_001 \
  --cost-limit 3.0 \
  --limit 5
```

This command runs a five-scene smoke test. Remove `--limit 5` to run all 288
scenes. The example uses the paper's GPT-6 Astra `high` configuration, and
LiteLLM passes the reasoning setting to the selected provider. Each run writes
the following files.

```text
results/run_001/
  config.json
  blends/<scene>.blend
  agent_meta/<scene>.json
```

The metadata file for each scene records the number of turns, frames seen,
cost, runtime, completion status, and stop reason. Other useful options are
listed below.

- `--scenes <id ...>` runs only the listed scenes.
- `--resume` skips scenes whose `.blend` already exists.
- `--shard i/N` splits the scenes across independent processes.
- `--cost-limit` sets the Stage-1 cost limit per scene. The paper uses $3.
- `--max-turns` sets an optional cap on turns as a safeguard. The value `0`
  means no limit.
- `--allow-network` enables networking in the container. Leave it off to
  follow the paper protocol.

## 3. Render and score

On a host with Blender and FFmpeg, render each reconstruction from its saved
scene camera.

```bash
.venv/bin/python ../eval/batch_render_camera.py \
  --run results/run_001 \
  --num-frames 64 \
  --resume
```

If Blender is not on your `PATH`, pass `--blender /path/to/blender` or set
`BLENDER_BIN`. This host Blender is separate from the Blender installation
inside the Stage-1 container. The step writes `camera_renders/<scene>.mp4`,
reuses existing renders when `--resume` is set, and does not compute scores.

The [evaluation guide](../eval/README.md) covers the scoring steps.

- **DV** asks the same spatiotemporal questions on the source video and on the
  render. `gpt-5.4-mini` answers each question from 16 sampled frames.
- **LS** compares frozen V-JEPA 2.1 ViT-G features of 64 sampled frames to
  measure layout and motion agreement.
- **Overall** is `((sqrt(DV) + sqrt(LS)) / 2) ** 2` on the 0–100 scale.

## Tools and effort

The harness gives the model two tools, which it calls through fenced blocks.

- `bash` runs a command inside the Blender sandbox.
- `frames` returns frames from the source video, either at listed timestamps
  or as `count=N` evenly spaced frames with optional `start=` and `end=` bounds.

The paper protocol sets no fixed limit on steps or frames. Within the cost
limit, the model decides how much of the video to inspect and how long to work.
It ends the run by replying `DONE`, which is accepted only after it has seen at
least one source frame. `frames_seen` counts the images the model actually
received and is tracked separately from `frames_extracted`. A run with
`frames_seen=0` is invalid.

LiteLLM handles provider routing, retries, and cost accounting. Record the
model, reasoning setting, harness configuration, and actual cost for each run.
