# SceneActBench

## Overview
SceneActBench ("Can Agents Act on the 3D Scenes They See?", arXiv 2607.22393) evaluates whether a vision-language-model (VLM) agent can turn visual evidence into executable 3D outputs on complete multi-object scenes. The agent receives reference images or sampled video frames (and, for some tasks, 3D assets), controls a headless Blender instance through a shared MCP tool interface (`blender-mcp`: `get_scene_info`, `get_object_info`, `execute_blender_code`, `render_scene_view`, …), and leaves its answer in the Blender scene, which the harness exports as JSON or GLB.

A deterministic verifier scores the final output against hidden 3D ground truth with task-specific geometric metrics. Most 3D benchmarks score text answers or single-object operations; SceneActBench scores what the agent actually built or placed in 3D.

The release contains **5 scored tasks** built from **210 source instances**, giving **520 task cases** (including two ablation sets):

| Task | Code id | Cases | Agent receives | Agent produces |
|---|---|---|---|---|
| Layout | `task1_single` | 100 | 1 reference view + its camera pose; the room's furniture as anonymised, centred, un-rotated GLBs | Each object's position and yaw |
| Camera | `task3_camera` | 100 | 1 reference view; the correctly arranged room | A camera pose that reproduces the view |
| Articulated | `task4_anim` | 100 | 32-frame open–close video frames; the object as one static GLB | Per-frame animation of the moving parts |
| Reconstruction | `task5_recon` | 100 | 11 reference views with camera poses; an **empty** scene | Every furniture piece, modelled from primitives in code |
| Dynamic | `task6_anim` | 10 | Frames from a 144-frame reference video; a kit of importable GLB parts | An animated scene (static layout + moving vehicles) |
| *Ablation: multi-view Layout* | `task2_multi` | 100 | Layout with several views | Not in Overall |
| *Ablation: photoreal Dynamic* | `task7_anim` | 10 | Dynamic with Cosmos-photoreal frames | Not in Overall |

Data sources: 3D-FRONT / M3DLayout (100 furnished rooms, 3–7 objects, 27 categories, 11 rendered views each), S2O ACD (100 articulated objects, 32-frame video + per-frame GT mesh), and Kenney CC0 kits (10 dynamic scenes, 144-frame video + animated GT).

The harness is MIT-licensed at github.com/Feinaldo2/SceneActBench; the dataset is on Hugging Face as `FEInaldo/SceneActBench` (CC BY-NC 4.0 for new contributions; underlying assets keep their source licences). Authors: Yifei Zhao, Xiangxin Zhou, Wenhao Yang, Jiaqi Tang, Pu Jian, Huanjin Yao, Jiarui Yao, Haowei Lin, Chunchao Guo, Zhuo Chen, Wenkai Lyu, Jianzhu Ma, Xueqian Wang, Wenxi Zhu (2026).

Published leaderboard: 11 proprietary configurations, Overall **38.6–50.2** (best: Doubao Seed 2.0 Pro High 50.2; Kimi K2.6 Reason 41.2). No model leads on every task.

**Naming note:** the README calls the tasks T1–T5 (Layout, Camera, Articulated, Reconstruction, Dynamic), but the code ids are `task1_single`, `task3_camera`, `task4_anim`, `task5_recon`, `task6_anim`.

## What It Measures
**Spatial grounding (Layout).** Can the agent read a single image plus its camera pose and put each furniture piece at the right world position and yaw, with no mirroring or turning?

**Egocentric spatial reasoning (Camera).** Can the agent recover where a photo was taken from (position and look direction) by rendering and comparing?

**Kinematic reasoning (Articulated).** Can the agent infer which parts move (doors, drawers…), their joint type and direction from video frames, and animate them correctly?

**Shape imagination (Reconstruction).** Can the agent model every furniture piece from scratch in Blender code (primitives, bmesh, modifiers), with the right shape, size and position, from multi-view images with known camera poses?

**Dynamic reasoning (Dynamic).** Can the agent lay out a static scene and animate the moving objects (which ones move, their paths, directions and timing) from a reference video?

## How verification works
Scoring is deterministic (no LLM judge). Each case is scored from what is actually in the Blender scene after the agent stops (object transforms, exported `agent_scene.glb`, or the active camera), compared with hidden 3D ground truth.

**Native metric per task, normalised to 0–100 with fixed reference bounds** (`src/harness/run_io.py`, `TASK_NORM`). Per case: `score = clip(1 − e/ub, 0, 1) × 100` for lower-is-better metrics, `clip(e/ub, 0, 1) × 100` for higher-is-better; tasks with two sub-metrics average them within the case.

| Task | Native metric (code key) | Normalisation |
|---|---|---|
| Layout | Mean ADD-S in metres (`mean_add_s`), after Hungarian matching of placed objects to GT objects | bound 4 m (↓) |
| Camera | Position error m (`cam_pos_error`) and angle error ° (`cam_angle_error_deg`) | mean of bound 4 m and bound 90° (↓) |
| Articulated | Worst part error (`worst_part_err`) | bound 1.0 (↓) |
| Reconstruction | Per-object F@5% (published key `obj_f@5%_matched`; corrected key `obj_f@5%_nn`, see below) | bound 1.0 (↑) |
| Dynamic | Worst vehicle error (`worst_vehicle_err`) and layout error (`layout_err`) | mean of two bounds of 1.0 (↓) |

- **Task score** = mean of case scores; invalid or missing cases count as 0.
- **Overall** = mean of the 5 task scores (T2 and T7 ablations excluded).
- Secondary diagnostics are stored per case (e.g., Chamfer, placement accuracy, scene success, PointBERT similarity, MSSIM/CLIP/LPIPS for Reconstruction), but do not enter the score.

**Reconstruction scorer, as corrected for our samples.** The published scorer gave an exact copy of the ground truth only 18–24 / 100. Four fixes were needed for the golden solution to score ≥ 95: (1) GT glTF Y-up is converted to Blender Z-up; (2) both sides are measured on area-uniform surface samples instead of mesh vertices; (3) the agent's modifiers are applied on export; (4) per-object scoring assigns each predicted point to its nearest GT object instead of DBSCAN clustering, which merged touching furniture. The corrected headline is:
- one global similarity alignment (scale = bounding-diagonal ratio, rigid ICP over 4 yaw starts),
- each aligned predicted point assigned to its nearest GT object,
- per object, F-score at τ = 5% of that object's bounding diagonal (precision = share of its assigned points within τ of its surface; recall = share of its surface covered within τ),
- headline = mean over GT objects (missing objects score 0).

Golden checks with the corrected scorer: authors' bedroom 99.9, our living room 100.0, our gaming room 100.0.

**[TBC]** Articulated and Dynamic metrics were not exercised in our runs; their definitions above come from code keys and the README only. The published leaderboard used the uncorrected Reconstruction scorer, so its Reconstruction numbers (7.1–12.3) are not comparable with corrected scores.

## Task Taxonomy

### Official SceneActBench task (as released)
Each case is one JSON file; ground truth is kept outside the task file.

| File / field | Role | Description |
|---|---|---|
| `id`, `task_type`, `scene_id` | Identity | Case id, task type (`task1_single`… `task6_anim`), source scene or object |
| `scene_dir` | Data | Folder with assets and hidden GT (`canonical/`, `scene/*_full.glb`, `gt.json`, `render/`). Read by the scorer; **not meant for the agent** |
| `system_prompt` | Agent prompt | Task-type role, conventions (Z-up, metres, floor at 0, set `matrix_world = T @ R`), workflow and what is graded |
| `prompt` | Agent prompt | Case instruction: object count, reference image path(s), camera pose(s), fov_x 39.6° |
| `setup_code` | Environment | bpy code the harness runs first (clears the scene, imports assets, creates `__ref__` camera where applicable) |
| `references` / `reference_image` / `reference_frames` | Input | Images or frames sent to the model (alpha composited onto white, re-encoded as PNG) |
| `reference_camera` / `gt_camera` | Metadata / GT | Camera pose; for Camera this is the hidden answer |

Run outputs land in `runs/<model>/<task_type>/<task_id>/`: `score.json` (headline + full metrics), `steps.json` (every tool call), `task.json`, and `agent_scene.glb` / `agent_camera.json` / `agent_frames/`.

Default step limits (`run_benchmark.sh`): 30; Articulated 60; Reconstruction 35; Dynamic 80.

### Our custom Reconstruction samples (Harbor tasks, `tasks/`)
Each sample is a self-contained Harbor task, generated from a Blender scene of a furnished room (`samples/<name>/`).

| File | Role | Description |
|---|---|---|
| `instruction.md` | Agent prompt | Harbor preamble (Blender via MCP, inputs in `/app/input`, the final Blender scene is the answer) + the official SceneActBench Reconstruction system prompt and prompt, listing the 3 images with exact camera poses (fov_x 39.6°) |
| `task.toml` | Config | Timeouts (agent 7200 s, verifier 900 s, build 1800 s), 4 CPU / 8 GB, the `blender` stdio MCP server, metadata (source scene, golden items, golden reward) |
| `environment/Dockerfile` | Environment (scaffolding) | Ubuntu 24.04 (linux/amd64) + Blender 5.0.1 + blender-mcp (telemetry off) + numpy/scipy/trimesh/scikit-learn |
| `environment/input/` | Agent input | The 3 reference renders (768 px, furniture only, composited on white — the same pixels the SceneActBench harness sends) |
| `environment/sceneactbench/` | Environment (scaffolding) | Headless-Blender launcher, boot script (MCP socket + autosave after every command), MCP stdio wrapper, socket client |
| `solution/solve.sh`, `golden_scene.glb` | Gold solution | Oracle: loads the golden solution into the live Blender; must score ≈ 1.0 |
| `tests/test.sh` | Verifier (scaffolding) | Exports the final scene, scores it, writes `/logs/verifier/reward.txt` and `score.json` |
| `tests/export_scene.py` | Verifier | Takes the scene from live Blender → autosave → agent's `scene.blend` → `scene.glb`; meshes only, modifiers applied |
| `tests/verify.py`, `tests/scorer/metrics.py` | Verifier | Corrected Reconstruction scorer; reward = `obj_f@5%_nn` |
| `tests/golden/scene/*_full.glb`, `tests/golden/cameras.json` | Answer key | Golden solution and reference camera poses; only present at grading time |

Shared scaffolding (`environment/`, `tests/` except the golden files, `solution/solve.sh`) is identical across tasks.

## Contributor Workflow
**Scene Selection:** Pick one furnished indoor room as a Blender file and check that it suits the difficulty you're after. A good room has 5–12 main pieces of furniture at realistic sizes, each clearly visible from at least one corner of the room. Avoid rooms that are mostly small clutter or have furniture completely hidden behind other pieces.

**Task Authoring:** Say which objects in the Blender file make up each piece of furniture; walls, floors and small decorations are left out. The task generator builds the hidden answer key, takes three pictures of the room from three different corners (the agent's only input), and writes the Harbor task with each camera's position in the prompt. Check the three pictures, and if a piece is missing, hidden or unclear, adjust and regenerate.

**Verifier Construction:** Run the grader on the answer key itself. The oracle loads the real furniture into Blender as if it were the agent's answer and must score 1.0; a no-op run, where the agent builds nothing, must score 0.0.

**Verifier Calibration:** Run rollouts with frontier models and review a spread of good and bad results. Compare the agent's room with the real one using the before/after pictures and per-item scores, and check that every low score matches a visible mistake: a piece missing, in the wrong place, the wrong size or shape, or facing the wrong way. Count a failure only when at least one picture clearly showed the piece; re-run borderline results, since the same model can score quite differently from run to run; and check that scores spread across models.

## Category Distribution
**Published benchmark (by task):**

| Category | Share of 410 scored cases | Definition | Examples |
|---|---|---|---|
| Layout | 24% (100) | Place given furniture to match one view | Bedrooms / living rooms from 3D-FRONT |
| Camera | 24% (100) | Recover the camera pose of one view | Same rooms |
| Articulated | 24% (100) | Animate moving parts from video | Cabinets, doors, drawers (S2O ACD) |
| Reconstruction | 24% (100) | Model every furniture piece from multi-view images | Same rooms, 11 views |
| Dynamic | 2% (10) | Build and animate a scene from video | Kenney town scenes with moving vehicles |

**[TBC]** Room-type split within the 100 3D-FRONT rooms (bedroom vs living room, etc.) is not stated in the README.

**Our samples so far:** 2 Reconstruction samples — living room (11 items), gaming room (7 items).

## Difficulty Distribution
SceneActBench does not define difficulty tiers. Published per-task score ranges across the 11 configurations show the spread:

| Task | Published range | Kimi K2.6 Reason |
|---|---|---|
| Layout | 51.9 – 84.1 | 70.9 |
| Camera | 13.2 – 34.5 | 24.6 |
| Articulated | 48.3 – 73.8 | 57.3 |
| Reconstruction (uncorrected scorer) | 7.1 – 12.3 | 8.5 |
| Dynamic | 41.4 – 70.7 | 44.8 |

**Our target for custom samples:** Kimi K3 headline < 70 on the corrected scorer, with a golden solution ≥ 95. Current results:

| Sample | Kimi K3 | Golden |
|---|---|---|
| Living room | 12.8 | 100.0 |
| Gaming room | 16.1 | 100.0 |

Kimi K3 single runs on official cases, for reference: Layout (Bedroom-5088) 83.8, Camera (same scene) 25.3.

**Caution on Layout:** a do-nothing answer (all objects left piled at the origin) scores **67.9** on the Bedroom-5088 Layout case, because of the loose 4 m bound. A Layout sample below 70 does not by itself show a model failure.

## Quality Checklist

### Official task (harness and data)
**Format compliance**
- ☐ **Valid task JSON.** `id`, `task_type`, `scene_id`, `scene_dir`, `system_prompt`, `prompt`, `setup_code`, and references present; paths resolve on the run machine.
- ☐ **Harness runs end to end.** Headless Blender starts and MCP connects. The public repo lacks `headless/` and the `scripts/` / `tools/` task builders; we added `headless/blender_process.py` + `blender_boot.py`, and pinned `mcp<2` (the 2.x SDK renamed FastMCP).

**Specificity / instruction–verifier alignment**
- ☐ **Prompt states what is graded.** Conventions (Z-up, metres, floor at 0, `T @ R` placement) and what the agent must leave in the scene match what the scorer reads.

**Solvability**
- ☐ **Oracle scores at the top of the range.** Layout oracle 99.8. Reconstruction oracle 99.9–100.0 only with the corrected scorer (published scorer: 18.2 on the authors' bedroom).

**Integrity / anti-cheat**
- ☐ **GT not reachable from the agent.** Agents run arbitrary Python, so they can open any file on disk. In our first Camera run, Kimi opened `gt.json`, `layout.json` and `render/meta.json` (which holds the exact reference camera pose). Released `scene_dir`s hold GT next to the inputs, so isolate inputs before running.
- ☐ **Anonymised assets.** Objects are named `object_NN`, centred and un-rotated, so names and coordinates do not leak the answer.

**Environment fidelity**
- ☐ **Same pixels for every model.** Reference images are alpha-composited onto white and re-encoded as PNG by the harness.
- ☐ **No provider-specific auth hacks.** The harness appended `?cache_task_id=…` to the API key for its internal gateway, which broke other OpenAI-compatible providers (401); now gated to that gateway only.
- ☐ **Blender version recorded.** README targets Blender 5.0; our runs used Blender 5.2.2 LTS.

**Verifier quality**
- ☐ **Crashes detected correctly.** The harness treated ordinary Python errors in agent code as Blender crashes and wiped the scene; fixed in `agent.py`.
- ☐ **Deterministic, no judge.** All scores come from geometry; runs replay exactly from `steps.json`.

### Custom Reconstruction sample (`tasks/recon-<name>/`)
**Format compliance**
- ☐ **Valid Harbor task folder.** `instruction.md`, `task.toml`, `environment/Dockerfile` (+ `input/`, `sceneactbench/`), `solution/solve.sh` + `golden_scene.glb`, `tests/test.sh` + `export_scene.py` + `verify.py` + `scorer/` + `golden/` all present; the image builds and the run executes with no harness error.
- ☐ **Workspace contract.** Scaffolding is identical across tasks (only `input/`, `golden/`, `golden_scene.glb`, `instruction.md`, `task.toml` differ per task); tasks are generated, not edited by hand.
- ☐ **Golden solution well-formed.** One mesh per item, a single material per mesh, metres, Z-up, floor at 0, no stray far-away geometry (enforced by the task generator).

**Specificity / instruction–verifier alignment**
- ☐ **Golden = what the prompt asks for.** Furniture only; no room shell; decor excluded unless large and obvious.
- ☐ **Every golden item is visible.** Each item is fully in frame in at least one view and not hidden in every view (checked by the task generator); `preview.png` reviewed by eye.

**Solvability**
- ☐ **Golden ≥ 95.** The golden check passes (ours: 1.000, 1.000), and the Harbor oracle run scores ≈ 1.0.

**Integrity / anti-cheat**
- ☐ **Answer key isolated during runs.** The golden solution lives only in `tests/` and `solution/`, which the agent never sees; `environment/` contains only the input images.
- ☐ **No free pass.** The Harbor `nop` run (empty scene) scores 0; one box around the whole room scores 0.074.

**Environment fidelity**
- ☐ **Official prompt and limits.** Official Reconstruction system prompt verbatim; 35-step limit; fov_x 39.6°; 768 px renders.
- ☐ **Run is clean.** No crashes, API errors or harness restarts in the run log.

**Verifier quality**
- ☐ **Discriminates good from bad.** On the living room: golden 100, one box per object 47.3, shapes shuffled between positions 23.6, one big box 7.4.
- ☐ **Scoring never lowers the model's result.** The no-alignment check is lower than the headline (living room 7.8 vs 12.8; gaming room 2.2 vs 16.1).
- ☐ **Failure confirmed visually.** The before/after images show the misplacement that the score reports.
- ☐ **Single-run caveat stated.** One run per sample; repeat runs needed before claiming an average.
