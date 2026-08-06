# Event System

AmritaCore's pipeline is **event-driven**. Workflow nodes and strategies
dispatch events; registered **matchers** intercept them, may mutate them, and
control flow through exceptions.

## Matcher — the Hook Primitive

In AmritaSense terms: events are `ConstructableEvent`s, dispatched through
`MatcherFactory.trigger_event(event, exception_ignored=...)`. Matchers match by
**event type string**:

```python
from amrita_sense.hook.matcher import Matcher

matcher = Matcher("agent.step_intro", priority=1)


@matcher.handle()
async def on_step_intro(event): ...
```

> Use the **literal string**, not `SomeEvent.event_type` — the latter is a
> property object, not a string.

## Event Categories

### Pipeline events

| Event                | Type string | When                                          |
| -------------------- | ----------- | --------------------------------------------- |
| `PreCompletionEvent` | —           | Before the LLM call (mutate context here)     |
| `CompletionEvent`    | —           | After the response (rewrite `model_response`) |

Convenience decorators: `@on_precompletion`, `@on_completion`, `@on_event("<type>")`.

### Step lifecycle events (built-in ReAct)

| Type string            | Mutable fields                     | Raised on                      |
| ---------------------- | ---------------------------------- | ------------------------------ |
| `agent.step_intro`     | `override_phase`                   | Step starts                    |
| `agent.step_leave`     | `override_verb`, `override_object` | Step ends                      |
| `agent.step_iteration` | `end_step`                         | After each tool round          |
| `agent.tool_call`      | `arguments`, `cancel`              | Before a regular tool executes |
| `agent.tool_return`    | `result`, `skip_append`            | After a regular tool returns   |

All step events are constructed from `AgentRunState` via their `constructor()`
classmethod.

## Mutation and Control Flow

Two powerful properties:

1. **Events are mutable** — the hook reads fields back after dispatch:

   ```python
   @on_event("agent.step_leave")
   async def fix_summary(event):
       event.override_verb = "Reviewed"  # replaces the auto summary
   ```

2. **`exception_ignored`** — exceptions listed there propagate out of
   `trigger_event` to the hook. `StepAbortError` (a `BaseException`) is the
   framework's control-flow signal:

   ```python
   from amrita_core.builtins.agent.events import StepAbortError


   @on_event("agent.tool_call")
   async def block_tool(event):
       raise StepAbortError("blocked")  # tool never executes
   ```

## How Events Reach Nodes

Workflow nodes and lifecycle hooks call `_trigger_step_event(...)`; matchers
registered in the same process see every dispatch. This is the extension point
for guardrails, telemetry, and human-in-the-loop.

## Next

[Tool System](tool.md) — how tools are defined and executed.
