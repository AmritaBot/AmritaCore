# Troubleshooting

The failure modes below are the ones you will actually hit. Each entry gives
the symptom, the root cause, and the fix.

## 1. The Agent Loops Calling the Same Tool

**Symptom**: the agent calls the same tool with the same arguments over and
over; tokens burn fast.

**Root cause**: a tool result didn't change anything, but the model keeps
trying — classic ReAct failure.

**Fixes** (AmritaCore has them built in):

| Mechanism                | Config / trigger                        | Effect                                                                                                                         |
| ------------------------ | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Stall detection**      | `builtin.loop_reasoning_trigger = N`    | After N identical tool signatures in one Step, a give-up prompt is injected and the Step ends                                  |
| **Pre-execution cancel** | same trigger                            | The N-th identical call is cancelled _before_ running and returns `"Cancelled: Reach the max limit of repeatly calling tool."` |
| **Hard call limit**      | `function_config.agent_tool_call_limit` | The loop stops after this many rounds regardless                                                                               |

**Tuning**: if your task legitimately repeats a tool (e.g. polling), raise
`loop_reasoning_trigger`; if the agent still loops, lower `agent_tool_call_limit`.

## 2. DeepSeek (or Thinking Mode) HTTP 400: `reasoning_content` must be passed back

**Symptom**: HTTP 400 "The `reasoning_content` in the thinking mode must be
passed back", not intermittent — happens on every thinking-mode request after
the first tool round.

**Root cause**: thinking providers require the assistant `reasoning_content`
to be returned verbatim on subsequent requests. Two historical bugs caused
this: the thinking filter mutated live message objects, and the tool-result
append dropped `reasoning_content`.

**Fix**: both are fixed in v0.13 — the filter shallow-copies messages instead
of mutating, and every assistant message append carries
`response_msg.reasoning_content` back. If you write a custom strategy, keep
both rules: **never strip reasoning in place; always pass it back**.

## 3. `insufficient tool messages following tool_calls message`

**Symptom**: OpenAI-compatible API rejects the request.

**Root cause**: every assistant message with `tool_calls` must be followed by
matching `ToolResult` messages.

**Fix**: the built-in strategies append **one assistant message per tool_call**
with its `ToolResult` — never batch multiple calls into one assistant message
unless you pair them all. Custom strategies: follow the same pairing rule
(see [Agent Strategy](../concepts/agent-strategy.md)).

## 4. Empty Responses (with thinking enabled)

**Symptom**: the model sometimes returns an empty `content`; decomposition or
summary calls fail.

**Root cause**: some providers return `''` when thinking is engaged.

**Fix**: built in — empty responses degrade to a fallback instead of crashing
(decompose → run directly; summarize → `"Completed <phase>"`). The warning log
includes the **original request id** (`x-ds-trace-id` for DeepSeek,
`x-request-id` for OpenAI) so you can find the call in provider logs:
`Empty decomposition response (request_id=..., thinking_content=True)`.

## 5. Token Burn Without an Obvious Loop

**Symptom**: usage is high even though the agent isn't looping.

**Checklist**:

- `function_config.agent_tool_call_limit` — hard cap per run
- `llm.memory_abstract_threshold` — enable summarization for long sessions
- Between-Step compression — the step loop compresses history when prompt
  tokens exceed the threshold (`step` metadata with `extra_type="compress"`)
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

**Fix**: call `await minimal_init(config)` once before creating agents or
registering tools that read config (e.g. `enable_if` lambdas).

## Next

[Advanced](../advanced/index.md) — the internals: workflow engine, suspend and
the step loop.
