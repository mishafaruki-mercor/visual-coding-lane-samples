# BVB Human Blind Ranking

The paper analyzes responses from **15 raters**. Each rater ranks **5
anonymized reconstructions** on **9 scenes**. The scenes come from a
**24-scene pool** with 8 scenes each from ARKitScenes, ScanNet, and ScanNet++,
and each rater sees 3 scenes from each source. The study generated 16 survey
forms, so the form count is higher than the 15 raters who returned responses.

The five configurations in the study are GPT-5.6 Sol xhigh, Grok-4.5 high,
Gemini 3.1 Pro high, Claude Opus 4.6 high, and Qwen3.5-397B-A17B high. GPT-6
Astra and Claude Opus 5 were not included. [PROTOCOL.md](PROTOCOL.md) describes
the study design. Run all commands below from the repository root.

New surveys sample scenes at random within each source with a fixed seed and
never read model scores. `BLIND_MAP.json` and `assignments.json` record the
sampling policy and seed. The assignments for the existing study come from the
saved packs, and rerunning with the original seed does not reproduce them.

## Generate surveys

The generator needs FFmpeg, the source videos, and complete camera renders for
the selected models. Beyond that it uses only the Python standard library. Use
a new output directory for each wave, and add `--force` only when rebuilding an
existing pack.

```bash
python eval/human/make_pack.py \
  --out eval/human/packs/wave2 \
  --forms 16 \
  --pool-per-source 8 \
  --per-source 3 \
  --seed 20260822
```

This command writes `survey-r01.html` through `survey-r16.html`. Each file is a
self-contained HTML survey with the clips embedded. Send one form to each
rater. `assignments.json` records the sampled scenes. Keep `BLIND_MAP.json`,
`assignments.json`, and `_clips_cache/` with the experimenter.

After ranking, each rater saves and returns a JSON file, and its `pack_id`
identifies the form. Store the raw responses together with the `BLIND_MAP.json`
that generated them. Adding a model requires a new survey.

## Score returned responses

Put the returned JSON files in the wave's `responses/` directory, then run the
scoring script.

```bash
python eval/human/score_human.py \
  --pack-dir eval/human/packs/wave2 \
  --responses eval/human/packs/wave2/responses \
  --out eval/human/packs/wave2/scored-dv-ls
```

For a completed study, point these arguments at that wave's own directories.
The script never modifies the raw responses. The metric correlations also need
`dual_vqa.jsonl` and `vision_sim.jsonl` for each studied model under
`sandbox/results/<run>/`.

| Output | Contents |
| --- | --- |
| `human_mean_rank.csv` | Mean rank and first-place rate, where a lower rank is better |
| `human_pairwise.csv` | Pairwise win rates implied by the rankings |
| `human_by_scene_model.csv` | Mean human rank and automatic metrics for each scene and model |
| `human_metric_correlation.csv` | Scene-model Spearman correlation between each automatic metric and the negated mean rank |
| `summary.json` | Rater count, scene coverage, means, correlations, and the Overall definition |

**Overall uses only DV and LS** and is computed as
`((sqrt(DV) + sqrt(LS)) / 2) ** 2`. The script stores scores on a 0–1 scale and
clips negative LS values to zero before the square root. The automatic-metric
outputs contain only DV, LS, and Overall. Overall is left blank when DV or LS is
missing, and DV is left blank for a scene with no source-correct questions.

The script computes correlations over **scene-model** pairs. The paper also
compares the global rankings of the five configurations, and the resulting
Overall ρ of 1.00 is a different quantity from the scene-model correlations
reported here. The paper's scene-model LS correlation is ρ = 0.83. Write any
updated analysis to a new output directory, and keep the raw responses and
earlier results unchanged.
