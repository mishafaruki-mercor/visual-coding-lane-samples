# SceneActBench agent for Harbor

The original SceneActBench agent loop, packaged as a Harbor custom agent. Use it to run any model with an
**OpenAI-compatible chat API** on the Reconstruction tasks.

```bash
PYTHONPATH=agents harbor run -p tasks/recon-gaming-room \
    -a sceneactbench_agent.harbor_agent:SceneActBenchAgent -m <model> [--ak option=value ...]
```

## What it does
- **Prompt:** the official SceneActBench system prompt as the system message, and the task prompt plus the
  3 reference images as the first user message, exactly as the original harness sends them.
- **Tools:** exactly the tools the task's `blender` MCP server lists, called through that server inside the
  container (`mcp_bridge.py`).
- **Images:** renders from `render_scene_view` go back to the model as a user message after the tool
  results. This works with every provider, including gateways that drop images inside tool results.
- **Budget:** 35 steps by default (the official Reconstruction budget). It also handles Blender crashes and
  compacts long conversations.
- **Logs:** writes `steps.json` (every step and tool call) and `run_summary.json` to the trial's `agent/`
  folder.

The loop runs on your machine; only the tool calls run in the container.

## Options (`--ak name=value`)

| Option | Default | Meaning |
|---|---|---|
| `base_url` | `https://ai-gateway.vercel.sh/v1` | OpenAI-compatible endpoint |
| `api_key_env` | `VERCEL_AI_GATEWAY_API_KEY` | Name of the environment variable that holds the API key |
| `max_steps` | `35` | Agent step budget |
| `max_tokens` | `65536` | Max output tokens per call. Reasoning models need a lot: Kimi K3 uses 13k–40k on step 0 |
| `reasoning_effort` | none | Passed through to the API if set |
| `stream` | `true` | Stream replies. Keep this on: some gateways (e.g. Vercel) drop a non-streamed request that is still silent after ~5 minutes, and long-reasoning models can exceed that on step 0 |

`-m` is the model id as your provider names it.

## Providers

```bash
# Vercel AI Gateway (default)
export VERCEL_AI_GATEWAY_API_KEY=...
... -m moonshotai/kimi-k3

# OpenRouter
export OPENROUTER_API_KEY=...
... -m moonshotai/kimi-k3 --ak base_url=https://openrouter.ai/api/v1 --ak api_key_env=OPENROUTER_API_KEY

# Moonshot directly
export MOONSHOT_API_KEY=...
... -m kimi-k3 --ak base_url=https://api.moonshot.ai/v1 --ak api_key_env=MOONSHOT_API_KEY

# OpenAI
export OPENAI_API_KEY=...
... -m gpt-5.4 --ak base_url=https://api.openai.com/v1 --ak api_key_env=OPENAI_API_KEY
```
The model must accept image input.
