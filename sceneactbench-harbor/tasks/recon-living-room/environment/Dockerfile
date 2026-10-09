# SceneActBench Reconstruction task environment: headless Blender + the blender-mcp tool server.
# Blender's official Linux build is x86_64, so the image is pinned to linux/amd64.
FROM --platform=linux/amd64 ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl xz-utils python3 python3-venv \
        libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6 libice6 libxext6 \
        libgl1 libegl1 libglu1-mesa libgl1-mesa-dri libegl-mesa0 libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# Blender 5.0.1 (the version SceneActBench targets)
ARG BLENDER_VERSION=5.0.1
RUN curl -fsSL "https://download.blender.org/release/Blender${BLENDER_VERSION%.*}/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
        | tar -xJ -C /opt \
    && ln -s /opt/blender-${BLENDER_VERSION}-linux-x64 /opt/blender
ENV BLENDER=/opt/blender/blender

# MCP server (agent side) + scoring libraries, in one venv
COPY sceneactbench /opt/sceneactbench
RUN python3 -m venv /opt/sceneactbench/venv \
    && /opt/sceneactbench/venv/bin/pip install --no-cache-dir \
        /opt/sceneactbench/blender-mcp "mcp[cli]>=1.3,<2" \
        "numpy>=1.26" "scipy>=1.11" "trimesh>=4.0" "scikit-learn>=1.3" \
    && chmod +x /opt/sceneactbench/*.sh
ENV BLENDER_MCP_DISABLE_TELEMETRY=1 \
    BLENDER_PORT=9876

# Task input: the reference images only (the answer key is in tests/, copied in at grading time)
COPY input /app/input
RUN mkdir -p /app/output
WORKDIR /app
