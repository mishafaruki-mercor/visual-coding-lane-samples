"""Model-agnostic agent loop. Shared by every model; only the adapter differs."""

import json
import time
from dataclasses import dataclass, field

from adapters import AssistantTurn


# Signature strings for a Blender process crash (if they appear in an execute_code result, treat Blender as dead / MCP disconnected).
# Triggers vary widely: a material name with a long float -> stoi out_of_range; boolean/subdivide etc. C++ abort.
_BLENDER_DEAD_MARKERS = (
    "connection closed", "could not connect", "broken pipe",
    "connection refused", "communication error with blender",
    "make sure the blender addon is running",
)


def _looks_like_blender_dead(text: str) -> bool:
    t = (text or "").lower()
    # The MCP server wraps ordinary Python errors as "Communication error with Blender:
    # Code execution error: ..." — Blender answered, so it is alive.
    if "code execution error" in t:
        return False
    return any(m in t for m in _BLENDER_DEAD_MARKERS)



@dataclass
class StepLog:
    step: int
    assistant_text: str | None
    tool_calls: list  # [{name, arguments, result}]


@dataclass
class RunResult:
    finished: bool          # model stopped on its own (no more tool calls)
    steps: list             # list[StepLog]
    error: str | None = None
    elapsed: float = 0.0
    mcp: object = None       # the mcp handle finally used (a new one is swapped in after a Blender crash restart); scoring uses it


# ---- Context compaction (LLM summary) ----

def _estimate_tokens(messages: list) -> int:
    """Rough estimate of the token count of messages (1 token ~= 4 chars for text, images counted at a fixed token cost)."""
    total = 0
    for m in messages:
        if isinstance(m, dict):
            content = m.get("content", "")
            if isinstance(content, str):
                total += len(content) // 4
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            total += len(block.get("text", "")) // 4
                        elif block.get("type") in ("image_url", "image"):
                            total += 1000  # ~1000 tokens per image
                        else:
                            total += len(json.dumps(block)) // 4
            # raw message from assistant (may contain tool_calls etc.)
            raw_str = json.dumps(m)
            # base64 images inflate the json significantly
            if "base64" in raw_str:
                total += raw_str.count("base64") * 800
    return total


COMPACT_PROMPT = (
    "You are a context compaction assistant. Summarize the conversation history "
    "below into a concise memory that preserves:\n"
    "1. What objects/parts have been identified and their properties\n"
    "2. What actions have been taken (code executed, objects moved/rotated)\n"
    "3. Current state of the scene (what's done, what's pending)\n"
    "4. Any errors encountered and lessons learned\n"
    "5. The plan for next steps\n\n"
    "Be concise but complete. Omit image data descriptions — just note 'rendered "
    "and checked' or 'reference frames viewed'. Output only the summary, no preamble."
)


def _compact_messages(adapter, messages: list, verbose: bool = False) -> list:
    """Compact messages[2:] (the middle history) into a single summary user message, keeping messages[0:2] (system + initial task).
    Uses the same model for one lightweight call to generate the summary. All images are dropped (replaced by text in the summary)."""
    if len(messages) <= 4:
        return messages  # too short, don't compact

    # Extract plain-text summary material from the middle history (drop images)
    history_text = []
    for m in messages[2:]:
        if not isinstance(m, dict):
            continue
        role = m.get("role", "")
        content = m.get("content", "")
        if isinstance(content, str):
            text = content[:500]
        elif isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(block.get("text", "")[:300])
                    elif block.get("type") in ("image_url", "image"):
                        parts.append("[image]")
                    elif block.get("type") == "tool_use":
                        parts.append(f"[tool_call: {block.get('name','')}({json.dumps(block.get('input',{}))[:100]})]")
                    elif block.get("type") == "tool_result":
                        parts.append(f"[tool_result: {str(block.get('content',''))[:200]}]")
            text = " ".join(parts)
        else:
            text = str(content)[:300]
        # truncate the full json of tool_calls
        tc = m.get("tool_calls")
        if tc:
            tc_summary = ", ".join(f"{c.get('function',{}).get('name','?')}" for c in tc[:5])
            text += f" [called: {tc_summary}]"
        history_text.append(f"[{role}] {text[:400]}")

    history_blob = "\n".join(history_text[-30:])  # keep at most the last 30 entries as summary input

    # Do one compaction call with the same model
    try:
        compact_msgs = [
            adapter.system_message(COMPACT_PROMPT),
            adapter.user_message(f"Conversation history to summarize:\n\n{history_blob}"),
        ]
        turn = adapter.run(compact_msgs, tools=[])
        summary = turn.text or "(compaction failed)"
    except Exception as e:
        summary = f"(compaction error: {str(e)[:100]})"

    if verbose:
        print(f"  [compact] {len(messages)} msgs -> summary ({len(summary)} chars)")

    # Rebuild messages: system + initial task + summary as a user message
    compacted = [
        messages[0],  # system
        messages[1],  # initial user (with reference frames)
        adapter.user_message(
            f"[CONTEXT MEMORY — summary of your previous {len(messages)-2} conversation turns]\n\n"
            f"{summary}\n\n"
            f"[END MEMORY — continue from where you left off]"
        ),
    ]
    return compacted


# ---- Main agent loop ----

def run_agent(adapter, mcp, system_prompt: str, task_prompt: str,
              max_steps: int = 30, verbose: bool = True,
              images: list = None, videos: list = None,
              extra_tools: dict = None,
              compact_threshold: int = 80000,
              restart_blender=None,
              on_checkpoint=None, checkpoint_every: int = 0,
              checkpoint_at=None) -> RunResult:
    """extra_tools: {name: {"schema": {...}, "handler": callable(args)->{"text","images"}}}
       Synthetic tools handled directly by the harness (not via MCP). Used e.g. for read_reference_frames:
       the agent calls it and gets back the real reference frame images, without routing through Blender rendering.

    compact_threshold: trigger context compaction when the estimated token count of messages exceeds this threshold.
       Set to 0 to disable compaction. Default 80000 (about 60% of most models' 128k context).

    restart_blender: optional callback callable()->new_mcp. When an execute_code step detects that the Blender
       process crashed (e.g. agent code triggers a Blender 5.x stoi/boolean etc. C++ crash) and the MCP disconnects,
       it is called to restart Blender and return a new mcp handle; then a note is injected telling the agent the scene was reset and needs rebuilding.
       If not passed, the old behavior applies (once crashed, it errors all the way through).

    on_checkpoint: optional callback callable(step:int, mcp). Used by the unbounded step-curve experiment: every
       checkpoint_every steps, and when the agent finishes on its own / hits max_steps, it is called with the current
       Blender session state to score and record. The callback must only read observations or use an isolated snapshot; it must not leave the
       eval camera, GT geometry, or file-cleanup side effects in the live session. If not passed, nothing is triggered (main experiment path behavior unchanged).
    checkpoint_every: trigger on_checkpoint every this many steps. 0=disabled.
    checkpoint_at: an extra set of forced trigger step numbers (e.g. main experiment step points 35/60/80, when not a multiple of checkpoint_every)."""
    extra_tools = extra_tools or {}
    _cp_at = set(checkpoint_at or [])
    mcp_tools = mcp.list_tools()
    for nm, spec in extra_tools.items():
        mcp_tools = mcp_tools + [{
            "name": nm,
            "description": spec.get("description", ""),
            "input_schema": spec.get("schema", {"type": "object", "properties": {}}),
        }]
    tools = adapter.convert_tools(mcp_tools)

    messages = [
        adapter.system_message(system_prompt),
        adapter.user_message(task_prompt, images=images, videos=videos),
    ]

    steps: list[StepLog] = []
    t0 = time.time()
    try:
        for step in range(max_steps):
            # ---- Context compaction: compact history when over threshold ----
            if compact_threshold > 0 and len(messages) > 4:
                est = _estimate_tokens(messages)
                if est > compact_threshold:
                    if verbose:
                        print(f"  [step {step}] context ~{est} tokens > {compact_threshold}, compacting...")
                    messages = _compact_messages(adapter, messages, verbose=verbose)

            # Per-step API call retry: exponential backoff, up to max_retries times
            # 500/502/503 -> upstream intermittent error, just wait a bit longer
            # 429/402 -> rate-limit/quota, needs a long wait (30-120s, gemini 402 quota recovery)
            # 400 token exceed -> trigger emergency compact and retry once
            turn = None
            max_retries = 10
            for attempt in range(max_retries):
                try:
                    turn = adapter.run(messages, tools)
                    # Empty-response detection: no tool calls and no text = empty API response (not a real completion),
                    # treated as a retryable error. An empty response on the first step makes the agent exit instantly and produce an empty glb
                    # (once misjudged the strongest model's empty API response as its "capability ceiling").
                    _empty = (not turn.tool_calls) and (not (turn.text or "").strip())
                    if _empty and attempt < max_retries - 1:
                        wait = min(3 * (2 ** attempt), 30)
                        if verbose:
                            print(f"  [step {step}] empty response (no tool, no text), retry {attempt+1}/{max_retries-1} (wait {wait}s)")
                        time.sleep(wait)
                        continue
                    break
                except Exception as e:
                    err_str = str(e)
                    # token over limit -> emergency compact and retry (at most one compact)
                    if ("exceed" in err_str.lower() and "token" in err_str.lower()) or \
                       ("too long" in err_str.lower()) or ("content_length" in err_str.lower()):
                        if len(messages) > 4:
                            if verbose:
                                print(f"  [step {step}] token over limit, emergency compact...")
                            messages = _compact_messages(adapter, messages, verbose=verbose)
                            continue  # retry with compacted context
                        else:
                            raise  # already minimal, can't help
                    # 402/429 quota/rate-limit: long wait (30-120s)
                    if "402" in err_str or "429" in err_str or "rate_limit" in err_str.lower():
                        wait = min(30 * (attempt + 1), 120)
                    else:
                        # 500/502/503/timeout: exponential backoff 3->6->12->24->... up to 60s
                        wait = min(3 * (2 ** attempt), 60)
                    if attempt < max_retries - 1:
                        if verbose:
                            print(f"  [step {step}] API retry {attempt+1}/{max_retries-1}: {err_str[:100]} (wait {wait}s)")
                        time.sleep(wait)
                    else:
                        raise
            messages.append(turn.raw)

            if verbose and turn.text:
                print(f"  [step {step}] {turn.text[:200]}")

            if not turn.tool_calls:
                steps.append(StepLog(step, turn.text, []))
                if on_checkpoint:
                    try: on_checkpoint(step + 1, mcp)
                    except Exception as _ce:
                        if verbose: print(f"  [checkpoint] step {step+1} failed: {_ce!r}")
                return RunResult(finished=True, steps=steps, elapsed=time.time() - t0, mcp=mcp)

            results, call_logs = [], []
            blender_died = False
            for tc in turn.tool_calls:
                if verbose:
                    print(f"  [step {step}] -> {tc.name}({json.dumps(tc.arguments)[:120]})")
                try:
                    if tc.name in extra_tools:
                        res = extra_tools[tc.name]["handler"](tc.arguments or {})
                        if not isinstance(res, dict):
                            res = {"text": str(res), "images": []}
                        res.setdefault("images", [])
                        res.setdefault("text", "")
                    else:
                        res = mcp.call_tool_rich(tc.name, tc.arguments)
                except Exception as e:
                    res = {"text": f"ERROR calling tool: {e}", "images": []}
                # Detect whether Blender crashed on this step (only for real tools via MCP, not synthetic extra_tools)
                if tc.name not in extra_tools and _looks_like_blender_dead(res.get("text", "")):
                    blender_died = True
                results.append(res)
                n_img = len(res.get("images", []))
                call_logs.append({"name": tc.name, "arguments": tc.arguments,
                                  "result": res["text"][:2000],
                                  "images_returned": n_img})
                if verbose and n_img:
                    print(f"  [step {step}]    <- {n_img} image(s) returned")

            messages.extend(adapter.tool_result_messages(turn.tool_calls, results))
            steps.append(StepLog(step, turn.text, call_logs))

            # Blender crash recovery: restart the process + reconnect MCP, and tell the agent the scene has been cleared and must be rebuilt.
            if blender_died and restart_blender is not None:
                if verbose:
                    print(f"  [step {step}] !! Blender process crashed, restarting and notifying the agent to rebuild the scene")
                try:
                    new_mcp = restart_blender()
                    if new_mcp is not None:
                        mcp = new_mcp
                    messages.append(adapter.user_message(
                        "[SYSTEM] The Blender process crashed during your last code "
                        "execution and has been restarted with an EMPTY scene — all "
                        "objects you created are gone. This is usually triggered by an "
                        "operation that crashes Blender's C++ core (e.g. naming a "
                        "datablock with a long floating-point number like "
                        "bpy.data.materials.new(f'm_{angle}'), or certain boolean/"
                        "subdivide ops). Avoid float-based datablock names (use integer "
                        "suffixes), and apply/validate risky ops incrementally. Please "
                        "rebuild the scene from scratch now, in smaller execute_code "
                        "steps so a single failure doesn't lose everything."))
                except Exception as _re:
                    if verbose:
                        print(f"  [step {step}] Blender restart failed: {_re}")

            # Unbounded curve experiment: score and record every checkpoint_every steps, or when hitting a forced checkpoint_at point
            if on_checkpoint and (
                (checkpoint_every and (step + 1) % checkpoint_every == 0)
                or (step + 1) in _cp_at):
                try: on_checkpoint(step + 1, mcp)
                except Exception as _ce:
                    if verbose: print(f"  [checkpoint] step {step+1} failed: {_ce!r}")

        # Hit max_steps: add a final checkpoint (if the last step is not a multiple of checkpoint_every)
        if on_checkpoint and checkpoint_every and max_steps % checkpoint_every != 0:
            try: on_checkpoint(max_steps, mcp)
            except Exception as _ce:
                if verbose: print(f"  [checkpoint] step {max_steps} failed: {_ce!r}")
        return RunResult(finished=False, steps=steps,
                         error="max_steps reached", elapsed=time.time() - t0, mcp=mcp)
    except Exception as e:
        return RunResult(finished=False, steps=steps, error=repr(e),
                         elapsed=time.time() - t0, mcp=mcp)
