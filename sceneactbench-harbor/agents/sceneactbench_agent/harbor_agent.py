"""Harbor custom agent: the SceneActBench agent loop, driving the task's blender-mcp tools.

Behaves like the original SceneActBench harness:
  - system prompt = the official SceneActBench system prompt, user prompt = the task prompt
    with the reference images attached (images are sent as user-message content);
  - tools = exactly the tools the task's blender-mcp server lists, called through that server;
  - tool images (renders) are fed back as a user message after the tool results;
  - step cap (default 35, the benchmark's Reconstruction budget), crash recovery, compaction.

The loop and model adapters run on the host; every tool call is executed inside the task
container by mcp_bridge.py against /opt/sceneactbench/blender_mcp_stdio.sh.

  PYTHONPATH="<SceneActBench Final>/agents" harbor run -p tasks/recon-gaming-room \
      -a sceneactbench_agent.harbor_agent:SceneActBenchAgent -m moonshotai/kimi-k3

Model access defaults to the Vercel AI Gateway (OpenAI-compatible); the key is read from the
host environment variable named by `api_key_env` (default VERCEL_AI_GATEWAY_API_KEY).
"""
import asyncio
import base64
import json
import os
import re
import sys
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import ClassVar

from pydantic import Field

from harbor.agents.base import BaseAgent
from harbor.agents.options import AgentOptions
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "loop"))
from adapters import build_adapter  # noqa: E402
from agent import run_agent  # noqa: E402

BRIDGE = "/tmp/sceneactbench_mcp_bridge.py"
VENV_PY = "/opt/sceneactbench/venv/bin/python"


class SceneActBenchAgentOptions(AgentOptions):
    max_steps: int = Field(default=35, description="Agent step cap (SceneActBench Reconstruction uses 35).")
    base_url: str = Field(default="https://ai-gateway.vercel.sh/v1", description="OpenAI-compatible base URL.")
    api_key_env: str = Field(default="VERCEL_AI_GATEWAY_API_KEY", description="Host env var holding the API key.")
    max_tokens: int = Field(default=65536, description="Max output tokens per model call. Kimi K3 can reason for 13k-40k tokens on step 0; 16384 truncates it to an empty reply.")
    reasoning_effort: str | None = Field(default=None, description="Optional reasoning_effort passed to the API.")
    stream: bool = Field(default=True, description="Stream completions (keeps long-reasoning requests alive through gateways).")


class ContainerMCP:
    """Same interface as the SceneActBench BlenderMCPClient, backed by environment.exec."""

    def __init__(self, environment: BaseEnvironment, loop: asyncio.AbstractEventLoop):
        self.env, self.loop = environment, loop

    def _exec(self, command: str, timeout: int = 900):
        fut = asyncio.run_coroutine_threadsafe(self.env.exec(command, timeout_sec=timeout), self.loop)
        return fut.result()

    def _bridge(self, mode_args: str) -> dict:
        out = f"/tmp/sab_out_{uuid.uuid4().hex}.json"
        r = self._exec(f"{VENV_PY} {BRIDGE} {mode_args} {out} >/dev/null 2>/tmp/sab_bridge.err; "
                       f"rc=$?; cat {out} 2>/dev/null; rm -f {out}; exit $rc")
        try:
            return json.loads(r.stdout or "")
        except json.JSONDecodeError:
            err = self._exec("tail -c 2000 /tmp/sab_bridge.err").stdout or ""
            return {"text": f"Error executing tool: MCP bridge failed (rc={r.return_code}): {err.strip()[-800:]}",
                    "images": [], "tools": []}

    def list_tools(self) -> list[dict]:
        return self._bridge("list").get("tools", [])

    def call_tool_rich(self, name: str, arguments: dict | None) -> dict:
        args_b64 = base64.b64encode(json.dumps(arguments or {}).encode()).decode()
        path = f"/tmp/sab_args_{uuid.uuid4().hex}.json"
        self._exec(f"echo {args_b64} | base64 -d > {path}")
        res = self._bridge(f"call {name} {path}")
        self._exec(f"rm -f {path}")
        return {"text": res.get("text", ""), "images": res.get("images", [])}

    def call_tool(self, name: str, arguments: dict | None) -> str:
        rich = self.call_tool_rich(name, arguments)
        if rich["images"] and not rich["text"].strip():
            return f"[returned {len(rich['images'])} image(s)]"
        return rich["text"]

    def restart(self):
        self._exec("pkill -f 'blender -b' ; sleep 1; /opt/sceneactbench/start_blender.sh", timeout=300)
        return self


def split_instruction(instruction: str) -> tuple[str, str]:
    """instruction.md = Harbor preamble --- official system prompt --- task prompt.
    Returns (system_prompt, user_prompt) as the SceneActBench harness would send them."""
    parts = re.split(r"\n---\n", instruction)
    if len(parts) >= 3:
        preamble, system, prompt = parts[0].strip(), parts[1].strip(), "\n---\n".join(parts[2:]).strip()
        return system, preamble + "\n\n" + prompt
    return "", instruction


class SceneActBenchAgent(BaseAgent):
    options_model: ClassVar = SceneActBenchAgentOptions

    @staticmethod
    def name() -> str:
        return "sceneactbench-agent"

    def version(self) -> str | None:
        return "1.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        await environment.upload_file(HERE / "mcp_bridge.py", BRIDGE)
        r = await environment.exec("/opt/sceneactbench/start_blender.sh", timeout_sec=300)
        if r.return_code != 0:
            raise RuntimeError(f"headless Blender failed to start: {r.stderr}")

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        opts = self.options or SceneActBenchAgentOptions()
        api_key = os.environ.get(opts.api_key_env) or self._extra_env.get(opts.api_key_env)
        if not api_key:
            raise RuntimeError(f"set {opts.api_key_env} in the host environment (or pass it with --ae)")
        adapter = build_adapter({
            "name": self.model_name or "moonshotai/kimi-k3", "provider": "openai",
            "model": self.model_name or "moonshotai/kimi-k3", "api_key": api_key,
            "base_url": opts.base_url, "vision": True, "max_tokens": opts.max_tokens,
            "reasoning_effort": opts.reasoning_effort,
            "stream": opts.stream,
        })

        system_prompt, user_prompt = split_instruction(instruction)
        images = []
        for path in dict.fromkeys(re.findall(r"/app/input/[\w./-]+\.png", instruction)):
            r = await environment.exec(f"base64 -w0 {path}")
            if r.return_code == 0 and r.stdout:
                images.append({"data": r.stdout.strip(), "mime": "image/png"})
        self.logger.info(f"reference images attached: {len(images)}")

        mcp = ContainerMCP(environment, asyncio.get_running_loop())
        result = await asyncio.to_thread(
            run_agent, adapter, mcp, system_prompt, user_prompt,
            max_steps=opts.max_steps, verbose=True, images=images,
            restart_blender=mcp.restart,
        )

        self.logs_dir.mkdir(parents=True, exist_ok=True)
        steps = [asdict(s) for s in result.steps]
        (self.logs_dir / "steps.json").write_text(json.dumps(steps, indent=1, default=str))
        (self.logs_dir / "run_summary.json").write_text(json.dumps({
            "model": self.model_name, "finished": result.finished, "error": result.error,
            "num_steps": len(steps), "elapsed_sec": round(result.elapsed, 1),
            "reference_images": len(images), "max_steps": opts.max_steps,
        }, indent=1))
        context.metadata = {**(context.metadata or {}), "finished": result.finished,
                            "error": result.error, "num_steps": len(steps)}
