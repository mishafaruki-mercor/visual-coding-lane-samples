# Kimi K3 on the office task

A full Harbor run of Kimi K3 on [`bvb-img-3011-office`](../../bvb-img-3011-office): Kimi built the
scene from scratch inside the task's agent container, and the task's verifier graded it.

**Reward: 0.55** (6 of 11 counted questions kept, judge `gpt-5.4-mini`, 5 votes per question, 16 frames)

| File | What it is |
|---|---|
| [`original_vs_kimi-k3.mp4`](original_vs_kimi-k3.mp4) | The source video next to the 16 frames the judge saw, stretched to the video's length |
| [`judge_frames.mp4`](judge_frames.mp4), [`judge_frames.png`](judge_frames.png) | The 16 frames rendered from Kimi's scene camera that the judge looked at |
| [`score_breakdown.json`](score_breakdown.json) | The verifier's full output: every question, the judge's answers on the source video and on the render, and the scene check |
| [`reward.txt`](reward.txt) | The reward |
| [`result.blend`](result.blend) | Kimi's submitted scene (Blender 4.2) |
| [`agent_config.json`](agent_config.json) | How the agent was run (the API key is a placeholder) |

## Run

- **Agent:** Harbor's `kimi-code` agent with `moonshotai/kimi-k3` through the Vercel AI Gateway,
  thinking effort high, image input on. Network during the agent phase: `ai-gateway.vercel.sh` only.
- **What it did:** extracted frames with FFmpeg, looked at them, wrote a Blender build script, saved
  `/app/result.blend`, and rendered test frames to compare with the video. It used its full 60-minute
  limit (about 30 steps); two long replies were cut off by the gateway and retried.
- **Task version:** commit `eadb349`, before the instruction was updated to state the grader's
  gates and describe the scoring, and before the image fixes in later commits. The questions,
  grader, and judge settings are the same as the current version.
- **Scene:** 289 mesh objects, 8 lights, animated camera over frames 1–729.

```bash
harbor run -y -p bvb-img-3011-office -a kimi-code -m moonshotai/kimi-k3 \
  --allow-agent-host ai-gateway.vercel.sh \
  --ae 'KIMI_MODEL_BASE_URL=https://ai-gateway.vercel.sh/v1' \
  --ae 'KIMI_MODEL_API_KEY=${VERCEL_AI_GATEWAY_API_KEY}' \
  --ae KIMI_MODEL_MAX_CONTEXT_SIZE=1000000 --ae KIMI_MODEL_CAPABILITIES=image_in,thinking \
  --ae KIMI_MODEL_THINKING_EFFORT=high --ae KIMI_CODE_EXPERIMENTAL_FLAG=true -o jobs
```

## Question by question

Only questions the judge answers correctly on the source video count. A counted question is kept
when a majority of the judge's 5 answers on the render are correct.

| # | Question | Correct answer | Judge on Kimi's render | Result |
|---|---|---|---|---|
| 1 | At the very start of the video, is the camera pointed at the floor, the ceiling, the windows, or straight across the office? | floor | ceiling ×5 | lost |
| 2 | For most of the video, is the camera close to the desks at standing height, or far away looking over the whole office from above? | close to the desks | — | not counted |
| 3 | Does the camera mostly stay in one corner of the office, or does it travel through the whole office? | one corner | — | not counted |
| 4 | In the first few seconds of the video, does the camera show the windows or the whiteboard? | windows | windows ×5 | kept |
| 5 | What will be the first-time appearance order of the following categories in the video: book, window shade, soda can, whiteboard? | book, window shade, soda can, whiteboard | — | not counted |
| 6 | Which of these objects is on a desk: a soda can, a desk lamp, a printer, or a potted plant? | soda can | soda can ×5 | kept |
| 7 | What object is lying on the carpet at the start of the video: a book, a cup, a backpack, or a phone? | book | phone ×5 | lost |
| 8 | Are the windows covered by roller shades, curtains, vertical blinds, or nothing? | roller shades | roller shades ×5 | kept |
| 9 | Is the ceiling an exposed ceiling with ducts, a tiled drop ceiling, or a wooden ceiling? | exposed ceiling with ducts | tiled drop ceiling ×5 | lost |
| 10 | Which of these is on the far wall of the office: a whiteboard, a TV, a painting, or a clock? | whiteboard | whiteboard ×5 | kept |
| 11 | How many chair(s) are in the window corner? | 2 | — | not counted |
| 12 | Are the chairs in the window corner next to the windows or in the middle of the room? | next to the windows | next to the windows ×5 | kept |
| 13 | Which side of the open laptop is the red soda can on, as shown in the video: left or right? | right | left ×5 | lost |
| 14 | In the window corner, are the cardboard boxes on the window ledge, on a desk, or on the floor in the middle of the room? | window ledge | desk ×5 | lost |
| 15 | Are the desks near the camera arranged in long rows of connected desks, or in separate enclosed cubicles? | rows | long rows of connected desks ×5 | kept |

## What it got right and wrong

Kimi rebuilt the window corner with roller shades, chairs beside the windows, desks in long rows,
a soda can on a desk, and the whiteboard on the far wall. It missed the camera's starting view
(the render starts on a gray floor that the judge read as a ceiling), the book on the carpet
(read as a phone), the exposed-duct ceiling (flat with strip lights), which side of the laptop the
soda can is on, and the boxes on the window ledge.
