# Step Lifecycle Events

The step loop emits **mutable** events at every boundary. Matchers registered
for the event type string may modify event fields (the hook reads them back) or
raise `StepAbortError` for control flow.

```python
from amrita_sense.hook.matcher import Matcher

matcher = Matcher("agent.tool_call", priority=1)

@matcher.handle()
async def guard(event):
    event.cancel = True

# clean up after the test / run:
# matcher._dead_at = <past datetime>
```

> Use the **literal string** (`"agent.step_intro"`), not
> `StepIntroEvent.event_type` — the latter is a property object.

## StepAbortError

`BaseException` raised by matchers to abort the current operation — passed via
`exception_ignored` so it propagates out of `trigger_event` to the hook, which
decides how to act (skip the work, end the Step early, ...).

## Events

### StepIntroEvent — `agent.step_intro`

Broadcast when a Step begins (`intro_step`).

| Field            | Meaning                               |
| ---------------- | ------------------------------------- |
| `step_index`     | Global step counter                   |
| `phase`          | The phase being entered               |
| `simple_mode`    | Bare run (no DAG)?                    |
| `plan_summary`   | First 5 plan descriptions             |
| `override_phase` | **Mutable** — redirect the phase name |

### StepLeaveEvent — `agent.step_leave`

Broadcast when a Step finishes (`leave_step`).

| Field                               | Meaning                              |
| ----------------------------------- | ------------------------------------ |
| `step_index` / `phase`              | Which Step                           |
| `verb` / `object`                   | The auto summary (subject-predicate) |
| `stall_injected`                    | Give-up prompt was injected?         |
| `override_verb` / `override_object` | **Mutable** — replace the summary    |

### StepIterationEvent — `agent.step_iteration`

Broadcast after each tool round inside the execute Step.

| Field                  | Meaning                          |
| ---------------------- | -------------------------------- |
| `step_index` / `phase` | Which Step                       |
| `tool_signatures`      | Signatures in the current window |
| `end_step`             | **Mutable** — force-end the Step |

### StepToolCallEvent — `agent.tool_call`

Broadcast _before_ a regular tool executes (built-in tools excluded).

| Field                   | Meaning                                                             |
| ----------------------- | ------------------------------------------------------------------- |
| `tool_name` / `tool_id` | The tool call                                                       |
| `arguments`             | **Mutable** — rewrite the call arguments                            |
| `cancel`                | **Mutable** — cancel without executing (returns `"Cancelled: ..."`) |

### StepToolReturnEvent — `agent.tool_return`

Broadcast _after_ a regular tool returned.

| Field                   | Meaning                                               |
| ----------------------- | ----------------------------------------------------- |
| `tool_name` / `tool_id` | The tool call                                         |
| `result`                | **Mutable** — rewrite what the model sees             |
| `skip_append`           | **Mutable** — skip writing the result back to context |

All events are constructed from `AgentRunState` via their `constructor()`
classmethod.

## Related

- [AgentRunState](AgentRunState.md) — the state events are constructed from
- [Concepts → Event System](../concepts/event.md) — matcher mechanics
- [Advanced → Step Loop](../advanced/step-loop.md) — when each event fires
