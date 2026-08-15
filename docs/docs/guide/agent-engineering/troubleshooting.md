# Troubleshooting & Pitfalls

The failure modes below are the ones you will actually hit. Each entry gives
the symptom, the root cause, and the fix — solutions come from how AmritaCore
actually executes, not from folklore.

## 1. The Agent Loops Calling the Same Tool

**Symptom**: the agent calls the same tool with the same arguments over and
over; tokens burn fast.

**Root cause**: a tool result didn't change anything, but the model keeps
trying — classic ReAct failure.

**Fixes** (AmritaCore has them built in):

| Mechanism                | Config / trigger                        | Effect                                                                                                                         |
| ------------------------ | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Stall detection**      | `builtin.loop_reasoning_trigger = N`    | After N identical tool signatures, a give-up prompt is injected and the Step ends                                              |
| **Pre-execution cancel** | same trigger                            | The N-th identical call is cancelled _before_ running and returns `"Cancelled: Reach the max limit of repeatly calling tool."` |
| **Hard call limit**      | `function_config.agent_tool_call_limit` | The loop stops after this many rounds regardless                                                                               |

Where detection runs matters. Stall detection is a **per-iteration hook**
(`after_iteration`, called after every `STEP_EXEC` round) — it must live
_inside_ the loop. A previous design checked only in `leave_step`, which runs
after the loop exits: a model stuck calling one tool never reached
`leave_step`, so the stall never fired and tokens burned without limit. The
step loop also carries a hard cap in `iter_cond` (`called_count > max_times`)
so an inner-loop stall can't outlive the budget. `leave_step` keeps a
stall check as an idempotent backstop.

**Tuning**: if your task legitimately repeats a tool (e.g. polling), raise
`loop_reasoning_trigger`; if the agent still loops, lower `agent_tool_call_limit`.

## 2. HTTP 400: `reasoning_content` must be passed back

**Symptom**: HTTP 400 "The `reasoning_content` in the thinking mode must be
passed back", not intermittent — happens on every subsequent request once the
assistant has produced reasoning.

**Root cause**: some providers require the assistant `reasoning_content` to be
returned verbatim on later requests. **Whether the rule applies is decided by
the provider, not the adapter**: Anthropic requires it whenever extended
thinking is enabled; DeepSeek requires it even in its OpenAI-compatible mode.
So "thinking mode" is not the trigger — the provider is. Two historical bugs
caused this: the thinking filter **mutated live message objects in place**, and
the tool-result append dropped `reasoning_content`.

**Fix**: both are fixed in v0.13 — the filter (`thinking_config.content_mode`)
shallow-copies messages (`model_copy(deep=False)`) instead of mutating, and
every assistant message append carries `response_msg.reasoning_content` back.
If you write a custom strategy, keep both rules: **never strip reasoning in
place; always pass it back** — safe for every provider, mandatory for the ones
above.

## 3. `insufficient tool messages following tool_calls message`

**Symptom**: OpenAI-compatible API rejects the request.

**Root cause**: every assistant message with `tool_calls` must be followed by
matching `ToolResult` messages.

**Fix**: the built-in strategies append **one assistant message per tool_call**
with its `ToolResult` — never batch multiple calls into one assistant message
unless you pair them all. Custom strategies: follow the same pairing rule (see
[Agent Strategy](../concepts/agent-strategy.md)). Any context injection that
splits a tool-call/result pair (e.g. plan-status notes) breaks the contract —
AmritaCore injects those at Step boundaries only, never mid-pair.

## 4. Empty Responses (with thinking enabled)

**Symptom**: the model sometimes returns an empty `content`; decomposition or
summary calls fail.

**Root cause**: some providers return `''` when thinking is engaged.

**Fix**: built in — empty responses degrade to a fallback instead of crashing
(decompose → run directly; summarize → `"Completed <phase>"`). The warning log
includes the **original request id** so you can find the call in provider
logs: `Empty decomposition response (request_id=..., thinking_content=True)`.

> **Request-id gotcha**: DeepSeek puts the trace id in `x-ds-trace-id`
> (sometimes `eo-log-uuid`), **not** OpenAI's `x-request-id`. The adapter
> probes all three headers in order before falling back to its internal id.
> If you grep provider logs for `x-request-id` on a DeepSeek call, you will
> find nothing — search by the id in the warning instead.

## 5. Token Burn Without an Obvious Loop

**Symptom**: usage is high even though the agent isn't looping.

**Checklist**:

- `function_config.agent_tool_call_limit` — hard cap per run
- `llm.memory_abstract_threshold` — enable summarization for long sessions
- `function_config.agent_step_token_budget` — per-Step prompt-token budget;
  when exhausted, `iter_cond` stops the Step (`TokenBudget.exhausted`)
- Between-Step compression — the step loop compresses history when prompt
  tokens exceed the threshold (`step` metadata with `extra_type="compress"`);
  the fold keeps a tool-call/result pair together so the kept context stays
  well-formed
- Tool signatures — watch the `stall` metadata to confirm detection works

## 6. Peer Messages Not Reaching the Agent

**Symptom**: `send_to_producer(...)` worked but the agent never saw the text.

**Root cause**: peer messages are consumed **at Step boundaries only**
(`intro_step`); inside a Step they queue; after the run they are dropped
(channel closed).

**Fix**: push before the run starts (or between Steps) for guaranteed
delivery; for mid-run pushes, accept they may be picked up at the next
boundary — see [Streaming](../tutorials/streaming.md).

## 7. `Global AmritaConfig is not initialized`

**Symptom**: `RuntimeError` at startup when registering tools.

**Root cause**: `get_config()` was called before `minimal_init()`/`set_config()`.

**Fix**: call `await minimal_init(config)` (or `set_config`) once before
creating agents or registering tools that read config (e.g. `enable_if`
lambdas).

## 8. `Undefined protocol adapter: <name>`

**Symptom**: `ValueError` when creating an agent or testing a preset.

**Root cause**: `ModelPreset.protocol` names an adapter that was never
registered. Only `"openai"` / `"__main__"` (OpenAI-compatible) and
`"anthropic"` / `"claude"` ship with the framework — see
[Model Adapters](../extensions-integration/adapters.md).

**Fix**: remember the two-layer model — the **adapter** picks the protocol,
the **provider** is just `base_url` + `model`. DeepSeek and Azure are _not_
protocols; they are OpenAI-compatible endpoints reached through the default
protocol. Set `protocol="anthropic"` only when you target the Anthropic wire
format, and register your own adapter (via `get_adapter_protocol()`) before
referencing a custom protocol. `create_agent()` has no `protocol` argument —
it always builds a default-protocol preset.

## 9. `ModelPreset(model_config=...)` Silently Drops the Field

**Symptom**: streaming is off, thinking config is ignored — no error, just
wrong behavior.

**Root cause**: `ModelPreset` has no `model_config` field (`extra="allow"`),
so `ModelPreset(model_config={...})` swallows the dict as an unknown extra
field. Anything you intended to land in `ModelConfig` never does.

**Fix**: use `create_agent(model_config={...})`, which maps the dict onto
`ModelConfig` correctly. Same trap for `ThinkingConfig` — pass it via the
preset's `thinking_config` field, or through `create_agent`'s kwargs.

## 10. Test / Async Traps

These bite when you write tests or embed AmritaCore in a runner:

- **`asyncio.wait_for(coro, timeout=0)` times out immediately** — the
  coroutine never gets to run. Use a small positive timeout
  (e.g. `0.001`) when probing a stream non-blockingly.
- **AnyIO streams are bound to the event loop that created them.** Two
  separate `asyncio.run()` calls in one test share a stream across loops and
  hang. Keep push + drain inside a single `asyncio.run()`.
- **`MagicMock` streams hang on `__anext__`.** Guard stream consumers with
  `isinstance(stream, SuspendObjectStream)`; a mock "succeeds" at
  `get_producer_input_generator()` and then hangs forever on iteration.
- **`TypedDict` metadata can't be `isinstance`-checked.** `isinstance(m,
AgentStepXxxMetadata)` raises `TypeError` — discriminate with
  `m.get("type") == "step" and m.get("extra_type") == ...`.
- **`patch.object(strategy, method, fake_fn)` won't bind `self`.** Use
  `new=AsyncMock()` (or a bound method) so the patched callable receives the
  instance.

## 11. Plan Revision (`update_step`) Seems to Do Nothing

**Symptom**: the model never calls `update_step`; the plan never changes.

**Root cause**: three things must line up, and each has failed historically:

1. **The tool must be visible.** `UPDATE_STEP_TOOL` is only exposed when the
   step loop is active (`_ensure_step_tools` on `intro_step`). Without the
   step-loop workflow, the model cannot see `update_step` at all.
2. **The plan must be in context.** `_inject_plan_status()` writes a
   `[Plan status]` snapshot at Step intro — but only when the snapshot
   changed, and only at a Step boundary (never splitting a tool-call/result
   pair).
3. **Prompt guidance is probabilistic.** Telling the model "call
   `update_step`" in prose works sometimes. The reliable path is the
   **deterministic framework injection**: when a tool result starts with
   `ERROR`, `_maybe_inject_tool_failure_hint()` appends a user message —
   "retry at most once, then call `update_step` (remove_step/replan)" on the
   first failure, "do not retry, call update_step now" on the second
   (`AgentRunState.tool_error_hints` counts per Step).

**Fix**: use the step-loop workflow, keep the plan visible, and rely on the
`ERROR`-prefix convention for hard failures — the framework turns a failing
tool into an explicit revision instruction deterministically.

## Next

[Advanced](../advanced/index.md) — the internals: workflow engine, suspend and
the step loop.
