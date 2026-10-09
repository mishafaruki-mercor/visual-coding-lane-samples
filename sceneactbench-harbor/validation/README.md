# Validation

Harbor v0.23.0, Docker (OrbStack) on Apple Silicon, task image linux/amd64 under emulation.
Tasks generated from the Blender scenes in `samples/`.

| Check | Living room | Gaming room | Expected |
|---|---|---|---|
| `harbor run -a oracle` (golden solution loaded into the live Blender) | **1.000** | **1.000** | ≈ 1.0 |
| `harbor run -a nop` (agent does nothing) | **0.000** | **0.000** | 0.0 |
| Golden check (answer key scored against itself) | 1.000 | 1.000 | ≥ 0.95 |
| Rebuilt from `scene.json` vs. the earlier hand-built task | golden geometry identical; prompt identical; input images within 2/255 | same | — |

Also checked during development:
- **MCP tools:** the container's `blender` MCP server lists 23 tools; `execute_blender_code` runs and
  `render_scene_view` returns an image.
- **Grading fallback:** a real model output loaded through the MCP tools, with Blender then killed, is graded
  from the autosave with the same reward.
- **Extra test room:** a fresh room built and validated the same way scored oracle 1.000 and nop 0.000. (Not shipped.)

Each folder holds the verifier output of that Harbor run: `reward.txt`, `export.log`, `test-stdout.txt`.
