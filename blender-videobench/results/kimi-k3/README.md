# Kimi K3 on the office task

Full Harbor runs of Kimi K3 on [`bvb-img-3011-office`](../../bvb-img-3011-office). In each rollout Kimi
built the scene from scratch inside the task's agent container, and the task's verifier graded it.

**Average reward over 2 rollouts: 0.55**

| Rollout | Reward | Counted questions kept | Scene | Agent run (60 min limit) | Task version |
|---|---|---|---|---|---|
| [rollout 1](rollout1) | **0.55** | 6 of 11 | 289 meshes, 8 lights, camera frames 1–729 | about 30 steps, 2 gateway cutoffs retried | `eadb349` (before the instruction stated the grader's gates and scoring) |
| [rollout 2](rollout2) | **0.55** | 6 of 11 | 407 meshes, 4 lights, camera frames 1–730 | 16 steps, 5 gateway cutoffs retried | `b592f36` (current: instruction states gates and scoring; xauth and test.sh fixes) |

Both rollouts score the same but keep different questions: 4 are kept in both, 2 only in rollout 1,
2 only in rollout 2, and 3 are lost in both. The task's questions, grader and judge settings are the same
in both versions; rollout 2's instruction additionally describes the grading.

## Files (in each `rolloutN/`)

| File | What it is |
|---|---|
| `original_vs_kimi-k3_rolloutN.mp4` | The source video next to the 16 frames the judge saw, stretched to the video's length |
| `judge_frames.mp4`, `judge_frames.png` | The 16 frames rendered from Kimi's scene camera that the judge looked at |
| `score_breakdown.json` | The verifier's full output: every question, the judge's answers on the source video and on the render, and the scene check |
| `reward.txt` | The reward |
| `result.blend` | Kimi's submitted scene (Blender 4.2) |
| `agent_config.json` | How the agent was run (the API key is a placeholder) |

## Run

Harbor's `kimi-code` agent with `moonshotai/kimi-k3` through the Vercel AI Gateway, thinking effort high,
image input on, network limited to `ai-gateway.vercel.sh`. Both rollouts used the full 60-minute agent
limit (Harbor reports an `AgentTimeoutError`) and were graded on the scene saved before the limit.

```bash
harbor run -y -p bvb-img-3011-office -a kimi-code -m moonshotai/kimi-k3 \
  --allow-agent-host ai-gateway.vercel.sh \
  --ae 'KIMI_MODEL_BASE_URL=https://ai-gateway.vercel.sh/v1' \
  --ae 'KIMI_MODEL_API_KEY=${VERCEL_AI_GATEWAY_API_KEY}' \
  --ae KIMI_MODEL_MAX_CONTEXT_SIZE=1000000 --ae KIMI_MODEL_CAPABILITIES=image_in,thinking \
  --ae KIMI_MODEL_THINKING_EFFORT=high --ae KIMI_CODE_EXPERIMENTAL_FLAG=true -o jobs
```

## Question by question

Only the 11 questions the judge answers correctly on the source video count. A question is kept (✅)
when a majority of the judge's 5 answers on the render are correct.

| # | Question | Correct answer | Rollout 1 | Rollout 2 | Kept |
|---|---|---|---|---|---|
| 1 | At the very start of the video, is the camera pointed at the floor, the ceiling, the windows, or straight across the office? | floor | ❌ ceiling ×5 | ❌ ceiling ×5 | 0/2 |
| 4 | In the first few seconds of the video, does the camera show the windows or the whiteboard? | windows | ✅ windows ×5 | ✅ windows ×5 | 2/2 |
| 6 | Which of these objects is on a desk: a soda can, a desk lamp, a printer, or a potted plant? | soda can | ✅ soda can ×5 | ❌ potted plant ×5 | 1/2 |
| 7 | What object is lying on the carpet at the start of the video: a book, a cup, a backpack, or a phone? | book | ❌ phone ×5 | ✅ book ×5 | 1/2 |
| 8 | Are the windows covered by roller shades, curtains, vertical blinds, or nothing? | roller shades | ✅ roller shades ×5 | ✅ roller shades ×5 | 2/2 |
| 9 | Is the ceiling an exposed ceiling with ducts, a tiled drop ceiling, or a wooden ceiling? | exposed ceiling with ducts | ❌ tiled drop ceiling ×5 | ❌ tiled drop ceiling ×5 | 0/2 |
| 10 | Which of these is on the far wall of the office: a whiteboard, a TV, a painting, or a clock? | whiteboard | ✅ whiteboard ×5 | ❌ TV ×5 | 1/2 |
| 12 | Are the chairs in the window corner next to the windows or in the middle of the room? | next to the windows | ✅ next to the windows ×5 | ✅ next to the windows ×5 | 2/2 |
| 13 | Which side of the open laptop is the red soda can on, as shown in the video: left or right? | right | ❌ left ×5 | ❌ left ×5 | 0/2 |
| 14 | In the window corner, are the cardboard boxes on the window ledge, on a desk, or on the floor in the middle of the room? | window ledge | ❌ desk ×5 | ✅ window ledge ×5 | 1/2 |
| 15 | Are the desks near the camera arranged in long rows of connected desks, or in separate enclosed cubicles? | rows | ✅ long rows of connected desks ×5 | ✅ long rows of connected desks ×3, long rows ×2 | 2/2 |

Not counted (the judge gets them wrong on the source video): Q2 camera height, Q3 how much of the
office the camera covers, Q5 order of appearance, Q11 number of chairs.

## What Kimi gets right and wrong

In both rollouts Kimi rebuilt the window corner with roller shades and chairs beside the windows,
desks in long rows, and showed the windows first. In both it missed the camera's starting view (the
render starts on a gray floor the judge reads as a ceiling), the exposed-duct ceiling (built flat), and
which side of the laptop the soda can is on. The rest varied between rollouts: rollout 1 got the soda
can on the desk and the whiteboard; rollout 2 got the book on the carpet and the boxes on the window
ledge.
