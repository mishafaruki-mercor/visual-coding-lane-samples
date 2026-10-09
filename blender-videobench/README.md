# BVB office reconstruction task for Harbor

A [Harbor](https://github.com/laude-institute/harbor) task based on
[BVB (Blender-VideoBench)](https://github.com/yunlong10/BVB): an agent watches a real video and
rebuilds it as an animated Blender scene, then a judge model checks how much of the video survives
in a render of that scene.

The task is [`bvb-img-3011-office/`](bvb-img-3011-office): a 24-second handheld phone video of an
open-plan office. The repo also includes the generator that built it, so you can make your own task
from your own video.

```text
bvb-img-3011-office/      the office task (complete Harbor task, ready to run)
make_task.py              video + questions + golden .blend  ->  a new Harbor task
template/                 files every task shares (agent image, verifier image, grader, oracle)
examples/
  office_questions.jsonl  the office task's 15 questions, as a format reference
  office_make_golden.py   the hand fixes that turned GPT-6 Astra's scene into the office golden
results/
  kimi-k3/                a full Harbor run of Kimi K3: score breakdown, judged frames, video, scene
requirements.txt          Python packages for make_task.py
LICENSE-BVB               license for the BVB scoring code copied into template/ and each task
```

## Run the office task

You need Docker, Harbor (`harbor`), an OpenAI API key for the judge, and a key for the agent's model.
Docker builds Blender and everything else inside the task's containers.

```bash
export OPENAI_API_KEY=...                                  # read by the verifier (judge)
harbor run -y -p bvb-img-3011-office -a oracle -o jobs     # the golden solution
harbor run -y -p bvb-img-3011-office -a nop -o jobs        # an empty submission

# Kimi K3 through the Vercel AI Gateway, as in results/kimi-k3
export VERCEL_AI_GATEWAY_API_KEY=...
harbor run -y -p bvb-img-3011-office -a kimi-code -m moonshotai/kimi-k3 \
  --allow-agent-host ai-gateway.vercel.sh \
  --ae 'KIMI_MODEL_BASE_URL=https://ai-gateway.vercel.sh/v1' \
  --ae 'KIMI_MODEL_API_KEY=${VERCEL_AI_GATEWAY_API_KEY}' \
  --ae KIMI_MODEL_MAX_CONTEXT_SIZE=1000000 --ae KIMI_MODEL_CAPABILITIES=image_in,thinking \
  --ae KIMI_MODEL_THINKING_EFFORT=high --ae KIMI_CODE_EXPERIMENTAL_FLAG=true -o jobs
```

Any Harbor agent that can view image files works the same way: allow its model's API host with
`--allow-agent-host`. `-y` skips Harbor's prompt before it passes `OPENAI_API_KEY` to the verifier.

Each trial's verifier output is in `jobs/<job>/<trial>/verifier/`:

- `reward.txt`: the reward.
- `reward_details.json`: every question with the judge's answers on the source and the render,
  and whether it was kept.
- `render.mp4`: what the judge saw.

### Results so far

| Submission | Reward |
|---|---|
| Golden solution (oracle) | 1.00 (11 of 11 counted questions) |
| GPT-6 Astra (high), unedited scene | 0.91 |
| Kimi K3 (`kimi-code` agent), [full results](results/kimi-k3) | 0.55 (6 of 11) |
| No submission (`nop`) | 0.00 |

Kimi K3 and the empty submission are full Harbor runs with the final settings: the agent built its
scene from scratch in the task's container and the task's verifier graded it. The golden's 1.00 and
the GPT-6 Astra score come from grading saved renders with the task's final questions and 5-vote
judge; an earlier full Harbor run of the golden, with the first question wording and 3 votes,
scored 0.83. A full agent run plus grading takes about 3 hours on an Apple Silicon Mac, which
renders under emulation.

## Environment

Each run uses two containers, both built from the task's Dockerfiles. Both are linux/amd64,
because Blender's Linux build is x86-64 only.

| | Agent container (`environment/`) | Verifier container (`tests/`) |
|---|---|---|
| Base | Ubuntu 22.04 | Ubuntu 22.04 |
| Software | Blender 4.2.0, Xvfb + xauth, FFmpeg, Mesa EGL (headless EEVEE), Python 3 with numpy and Pillow, a `blender_run` helper | Blender 4.2.0, Xvfb + xauth, FFmpeg, Mesa EGL, Python 3 with `openai` 2.54.0 and `opencv-python-headless` 4.11.0.86 |
| Contents | The video at `/app/video.mp4` | The grader, questions, and source answers at `/opt/grader`; `test.sh` at `/tests` |
| Network | None, except the model API host passed with `--allow-agent-host` | Only `api.openai.com`, for the judge |
| Secrets | The agent's model key, passed by the run command | `OPENAI_API_KEY`, passed from the host by `task.toml` |
| Time limit | 60 min | 120 min (rendering is slow without a GPU) |

The task's `task.toml` also sets 2 CPUs, 4 GB of memory, 10 GB of storage, no GPU, and a 60-minute
image build limit. The agent never sees the verifier container; Harbor copies only
`/app/result.blend` into it.

**On Apple Silicon** the containers run under emulation with software rendering. A full agent run
plus grading takes about 3 hours, mostly rendering at about 5 minutes per frame. On an x86 machine
the same run is far faster.

## How a task is graded

The agent gets the video at `/app/video.mp4` and must save `/app/result.blend`. The scene has to be
built from Blender primitives, with a scene camera keyed to retrace the video's camera path. The
task's `instruction.md` gives the full rules and also tells the agent how it is graded: the gates
below, and that a vision judge answers held-back questions about the room from 16 rendered frames.

The verifier runs in a separate container that the agent never sees. It holds the questions, the
judge's answers on the source video, and the grader:

1. **Gate.** `/app/result.blend` must exist, not be a symlink, open in Blender, have a scene
   camera, and contain at least 10 mesh objects. Otherwise the reward is 0.
2. **Render.** The scene camera is rendered with BVB's renderer (EEVEE, 512 px) at 16 evenly
   spaced points across the timeline, exactly the frames the judge sees.
3. **Judge.** `gpt-5.4-mini` answers each question from those 16 frames, using BVB's prompt and
   answer matching. Each question is asked 5 times and the majority decides.
4. **Reward** = Dual VQA retention: of the questions the judge answered correctly on the *source*
   video, the share it still answers correctly on the render. 0 to 1.

The source-side answers are computed once by `make_task.py` and baked into the verifier
(`tests/grader/source_answers.jsonl`). Questions the judge gets wrong on the real video can't
measure anything, so they're dropped automatically: 11 of the office task's 15 count.

The render, frame sampling, prompt, and answer matching are BVB's own code
(`render_blend_video.py`, `dual_vqa_metric.py`, `dual_vqa_scoring.py` from the BVB repository's
`eval/`), copied unchanged under BVB's MIT license.

### How this differs from the BVB paper protocol

This is a Harbor task *based on* BVB. Its rewards aren't comparable to the BVB leaderboard.

| | BVB paper | This task |
|---|---|---|
| Agent | Mini-BVB harness with a `frames` tool | Any Harbor agent; it extracts frames itself with FFmpeg |
| Questions | 5,130 VSI-Bench questions over 288 videos | 15 author-written questions for one video |
| Score | Overall = sqrt-mean of Dual VQA and Latent Similarity (V-JEPA) | Dual VQA retention only |
| Judge | 1 answer per question | Majority of 5 answers per question |
| Instructions | Mini-BVB system prompt; the agent isn't told how it's scored | Same scene rules, plus a note to keep camera angles continuous across ±180°, and a description of the grader's gates and scoring method |

Latent Similarity is left out on purpose. On the office video it rated two unrelated real videos
(80.9 and 86.4) above Kimi K3's reconstruction of the right room (71.1). It also needs a 7.6 GB
model and ideally a GPU in the verifier.

## Make your own task

You need Docker, Harbor, FFmpeg, Python 3.9+ with `pip install -r requirements.txt`, and
`OPENAI_API_KEY` in your environment or in a `.env` file next to `make_task.py`.

### 1. Record the video

- One indoor room, 20–60 s, in a single continuous take.
- Walk slowly with the phone and show each wall and the main furniture at least once. Avoid
  whip-pans and zooming.
- Use steady light, and keep people out of frame if you can.
- Any format FFmpeg reads works. `make_task.py` converts it to 30 fps, no audio, 640 px on the
  long side.

### 2. Write the questions

Write a JSONL file with one question per line, in BVB / VSI-Bench format.
[`examples/office_questions.jsonl`](examples/office_questions.jsonl) is a complete example.

```json
{"id": 1, "question_type": "object_rel_direction", "question": "Which side of the open laptop is the red soda can on, as shown in the video: left or right?", "ground_truth": "B", "options": ["A. left", "B. right"]}
{"id": 2, "question_type": "object_counting", "question": "How many chair(s) are in the window corner?", "ground_truth": "2", "options": null}
```

Rules that make the judge reliable:

- **Put the choices in the question text.** The judge sees only the `question` string, never
  `options`. It answers in a few words, which are matched to the option text.
- **Keep option text short**, one to four words ("left", "roller shades"), so a short answer
  matches it.
- **Numeric types** (`object_counting`, `object_size_estimation`, `room_size_estimation`,
  `object_abs_distance`) take a number as `ground_truth` and `options: null`. Counts must match
  exactly; sizes and distances within 20%.
- **Ask about things a single frame or a short stretch shows clearly.** The judge sees only 16
  frames. In the office task it consistently failed "how many chairs", "how much of the office
  does the camera cover", and an appearance-order question on the real video, and it described
  the camera height in its own words instead of an option ("standing height"), so those four are
  dropped.
- **Avoid wording that depends on viewpoint or sequence the judge has to infer.** "The first desk
  shown up close" and "after looking at the floor, which way does the camera turn first" split
  the judge's votes on a correct scene. "Which side of the open laptop is the red soda can on, as
  shown in the video" and "in the first few seconds, does the camera show the windows or the
  whiteboard" were answered correctly 5 of 5 times.
- **Cover the three areas a reconstruction can get wrong:** perspective and camera path, objects
  (what is present, materials, counts), and positioning (left/right, next to, rows vs. cubicles).
- Aim for 12–20 questions. With fewer than 8 counted questions, one judge flip moves the reward
  by more than 0.12.

### 3. Make the golden solution

The golden scene is the reference reconstruction that the oracle submits. Two ways to get one:

- **Build it from a strong agent's attempt.** Run a model on the task, then fix what it got wrong
  by hand in a Blender script. The office golden is GPT-6 Astra's scene plus
  [`examples/office_make_golden.py`](examples/office_make_golden.py). That script rotates a desk,
  adds a missing dual-monitor desk, lowers dividers, fixes the book's logo, and unwraps a camera
  spin.
- **Build it yourself** in Blender, following the same scene rules the agent gets.

**Save the golden with Blender 4.2.** The verifier runs Blender 4.2, which can't open files saved
by Blender 5.x (`make_task.py` refuses them). If you edit in a newer Blender, re-run your edit
script with Blender 4.2, for example in the office task's agent image:

```bash
docker build -t bvb-blender42 bvb-img-3011-office/environment
docker run --rm -v "$PWD":/work bvb-blender42 \
  blender -b /work/model_attempt.blend --python /work/my_fixes.py -- /work/golden.blend
```

Compare its render with the video side by side before you use it.

### 4. Generate the task

```bash
python make_task.py --name my-kitchen \
  --video ~/Desktop/kitchen.mov \
  --questions my_kitchen_questions.jsonl \
  --golden my_kitchen_golden.blend \
  --author "Your Name"
```

This writes `bvb-my-kitchen/`. It checks the question file, converts the video, asks the judge
each question 5 times on the source video, and prints which questions count. Reword any dropped
question you care about and run it again with `--force`.

Useful options: `--votes`, `--min-meshes`, `--agent-timeout-min`, `--golden-floor`, and
`--source-answers` to reuse an existing answer bank without calling the judge.

### 5. Check the task, then run models

```bash
harbor run -y -p bvb-my-kitchen -a oracle -o jobs   # golden must reach the floor (default 0.8)
harbor run -y -p bvb-my-kitchen -a nop -o jobs      # no submission must score 0
```

Then run agents the same way as for the office task.

## Task layout

```text
bvb-<name>/
  instruction.md          agent prompt: video path, scene rules, camera animation
  task.toml               artifact /app/result.blend; agent offline; verifier separate,
                          allowed only api.openai.com, OPENAI_API_KEY passed from the host
  environment/            agent image: Blender 4.2 + Xvfb + FFmpeg, video at /app/video.mp4
  solution/
    solve.sh              oracle: copies golden.blend to /app/result.blend
    golden.blend
  tests/                  verifier image (never shipped to the agent)
    Dockerfile            Blender 4.2 + openai + opencv; grader baked at /opt/grader
    test.sh               entry point; a missing API key fails the run instead of scoring 0
    grader/
      grade.py            gate, render, judge, reward
      config.json         judge model, votes, frames, render settings, mesh minimum
      questions.jsonl     the held-back questions
      source_answers.jsonl  the judge's fixed answers on the source video
      render_blend_video.py, dual_vqa_metric.py, dual_vqa_scoring.py   BVB code, unchanged
```

## Known limits

- **The judge is an API model.** The verifier needs network access to `api.openai.com` and an
  API key, unlike fully offline Harbor verifiers. Grading one submission costs a few cents.
- **Votes reduce judge noise but don't remove it.** The same frames can get different answers
  between runs, and some questions are inherently borderline. Re-run marginal results before
  calling a task or a model broken.
- **Emulation on Apple Silicon.** The images are linux/amd64 (Blender's Linux build), so on a Mac
  they run under emulation with software rendering. Builds and renders work but are slow, about
  5 minutes per rendered frame there; far less on an x86 machine.
- **EEVEE needs EGL.** Both images install Mesa's EGL libraries for headless rendering.
