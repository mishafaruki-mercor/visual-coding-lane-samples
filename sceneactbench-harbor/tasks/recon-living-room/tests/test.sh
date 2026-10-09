#!/bin/bash
# SceneActBench Reconstruction verifier: export the agent's final Blender scene, score it, write the reward.
mkdir -p /logs/verifier /app/output
python3 /tests/export_scene.py /app/output/agent_scene.glb 2>&1 | tee /logs/verifier/export.log
/opt/sceneactbench/venv/bin/python /tests/verify.py \
    --golden /tests/golden \
    --pred /app/output/agent_scene.glb \
    --reward /logs/verifier/reward.txt \
    --details /logs/verifier/score.json
cp -f /app/output/agent_scene.glb /logs/verifier/agent_scene.glb 2>/dev/null || true
