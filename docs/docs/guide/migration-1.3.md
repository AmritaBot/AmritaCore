# Migration Guide: 1.2 → 1.3

AmritaCore 1.3 changes **how an agent turn ends**. The tool-round budget is now
exact, the loop winds down instead of being cut off, and a native-thinking run
no longer finishes with a second request that declares no tools. The checklist at
the end lists what to re-check in your own code.

## At a Glance

| Changed                                          | What to do                                                                                                                                                     |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `function_config.agent_tool_call_limit`          | Now means exactly that many tool rounds. A run that relied on the old overshoot makes fewer rounds; raise the number if you tuned around it.                     |
| `function_config.agent_tool_refusal_rounds` (new) | Default `2`. Rounds the agent may keep asking for tools after the budget is spent, before the turn closes.                                                       |
| `strategy.on_limited()`                          | No longer terminates the run. It marks the budget spent and asks the model to answer with what it has.                                                          |
| Native-thinking runs                             | Stream text during tool rounds and skip the separate completion, so the reply arrives while it is produced.                                                     |
| `ModelAdapter.agentic_call_api()` (new)          | Optional capability. Implement it and set `supports_agentic_call = True` to let an adapter serve the new path.                                                  |

## 1. The Tool Budget Is Exact

`agent_tool_call_limit` used to allow two more rounds than its name said: the
guard compared `called_count > limit + 1`. It is now `called_count >= limit`, so
a limit of `10` means ten tool rounds.

The step loop's `task_cond` and `iter_cond` use the same arithmetic, so both
workflows agree.

If a task legitimately needed the overshoot, raise the limit.

## 2. Reaching the Budget Winds Down

`on_limited()` used to append a "do NOT call any tools" instruction and raise
`BreakLoop`. That left the run with no answer, so the workflow fell back to a
completion request that declared no tools — and a model that still wanted a tool
wrote the call into the content as plain text instead of a structured call.

The run now winds down:

1. `on_limited()` marks the budget spent and asks the model to answer with what
   it has.
2. The next round still declares tools.
3. A call the model still makes is answered with a refusal tool result rather
   than executed, so the assistant/tool pairing stays valid.
4. If the model is still asking for tools after `agent_tool_refusal_rounds`
   such rounds, the turn closes with a notice. An answer is always accepted
   whenever it arrives — the notice is the fallback, not the normal ending.

A custom strategy that overrides `on_limited()` should either call `super()` or
set `_budget_exhausted` itself — `budget_exhausted` is the property the workflow
reads to decide whether the wind-down round may run.

## 3. Native Thinking Streams Through the Loop

When the preset enables native thinking **and** its protocol adapter implements
`agentic_call_api()`, the ReAct strategy drives the turn from one request per
round: text streams as it is produced, that round's tool calls come back at the
end, and the round that returns none is the answer. The separate tool-less
completion is skipped for the run.

Everything else keeps the previous path. A native-thinking preset on an adapter
without the capability logs a warning, because that path can still end with the
tool-less request described in §2.

## Checklist

- [ ] If you tuned `agent_tool_call_limit` around the old overshoot, re-check it.
- [ ] If you override `on_limited()`, make sure it still marks the budget spent.
- [ ] If you ship a custom adapter, implement `agentic_call_api()` and set
      `supports_agentic_call = True` to get the streaming path.
