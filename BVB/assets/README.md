# Repository figures and results

The main README uses tracked copies of the paper figures so that they render in
a fresh GitHub checkout without the local `misc/` manuscript directory, which
Git ignores.

| File | Content |
| --- | --- |
| [bvb-logo.png](bvb-logo.png) | BVB logo |
| [bvb-kitchen-input-vs-gpt-6-astra.gif](bvb-kitchen-input-vs-gpt-6-astra.gif) | README teaser showing the source kitchen video and its GPT-6 Astra reconstruction |
| [bvb-figure1.png](bvb-figure1.png) | Full Figure 1 with the benchmark overview and the Overall cost frontier across 51 configurations |
| [bvb-cost-frontier.png](bvb-cost-frontier.png) | Standalone plot of Overall versus Stage-1 cost |
| [bvb-pipeline.png](bvb-pipeline.png) | Reconstruction pipeline followed by Dual VQA and Latent Similarity evaluation |
| [bvb-results.csv](bvb-results.csv) | Full-precision results for all 51 configurations in the paper |

The full Figure 1, including both the benchmark overview and the cost frontier,
was exported from the arXiv manuscript on September 14, 2026. The results CSV
matches the download on the project page. Scores are on a 0–100 scale, and cost
is the mean Stage-1 cost per scene in USD. Overall is the square-root mean of DV
and LS. See [the evaluation guide](../eval/README.md) for definitions and
coverage requirements, and the
[interactive leaderboard](https://yoloytang.me/BVB/#leaderboard) for filtering
and plots.

Earlier teaser, diagnostic, metric, and curation figures have been removed from
this directory. They remain available in Git history or in a local `_archive/`
copy. Use the figures listed above for current results.
