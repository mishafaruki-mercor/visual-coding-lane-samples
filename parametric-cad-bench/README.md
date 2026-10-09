# Parametric CAD Bench: image-to-CAD samples

Harbor dataset `local/cad-bench-image-samples`.

Three Image-to-CAD tasks in Parametric CAD Bench v3 Harbor format. Each task folder is complete: the agent input (instruction and engineering drawing), the agent sandbox, the verifier, the hidden grader spec and reference model, and the oracle solution. `dataset.toml` registers all three so they run as one dataset.

| Task | Part | Spec parameters | Kimi K3 score |
|---|---|---|---|
| `lobed-rotor-image` | Six-rotor lobed housing | 13 | 0.174 (1 rollout) |
| `hand-cannon-image` | Hand cannon | 25 | 0.319 (average of 3 rollouts: 0.035, 0.887, 0.034) |
| `tray-bracket-image` | Perforated tray bracket | 38 | 0.150 (average of 3 rollouts: 0.259, 0.047, 0.144) |

Kimi K3 scores are averages over the rollouts run so far (average across the three tasks: **0.214**), with mini-swe-agent 2.4.6 at reasoning effort max (Oct 2026). The full run outputs (oracle and every Kimi K3 rollout) and a comparison image per task are in [`results/`](results/).

## Task layout (same for all three)

```
<task>/
  instruction.md              Agent prompt: the official v3 image-task prompt, naming /app/<drawing>.png
  task.toml                   Harbor config: artifacts, 9,000 s agent timeout (no network), 600 s verifier, 2 CPU / 4 GB
  environment/
    Dockerfile                Agent sandbox: FreeCAD 1.1.0, numpy 2.4.6, Tesseract OCR; copies the drawing into /app
    <drawing>.png             The engineering drawing, the agent's only source of geometry
    LICENSES/
  tests/
    test.sh                   Verifier entrypoint: hard-zero checks, render answer.png, run the scorer
    run_scorer.py             gnucleus-freecad-validator: geometry v2 + spec consistency, harmonic combine
    Dockerfile                Verifier image: FreeCAD 1.1.0, OCP, gnucleus-freecad-validator 0.6.0
    grader/spec.json          Hidden spec: mode = image_to_cad, description, view-annotated key parameters
    grader/param_check.py     Hidden parameter checker
    grader/reference.FCStd    Hidden reference model
    LICENSES/
  solution/
    solve.sh                  Oracle: copies the reference to /app/answer.FCStd
    reference.FCStd
```

`tests/test.sh`, `tests/run_scorer.py`, `tests/Dockerfile` and `solution/solve.sh` are byte-identical to the official v3 image tasks (checked against `gnucleus-ai/freecad-1338adbf8b`). `instruction.md` and `environment/Dockerfile` are identical apart from the drawing file name.

## Run

```bash
# Oracle: every task should score 1.0
harbor run -p . -a oracle

# Kimi K3, one attempt per task, leaderboard agent settings
harbor run -p . -a mini-swe-agent -m vercel_ai_gateway/moonshotai/kimi-k3 \
  --ak version=2.4.6 --ak reasoning_effort=max \
  --allow-agent-host ai-gateway.vercel.sh --env-file .env
```

For a single task, point `-p` at its folder instead, e.g. `-p hand-cannon-image`.
