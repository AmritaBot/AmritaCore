# 4. Events and Hooks

## Goal of This Chapter

Intercept the pipeline without touching framework code. By the end you will be
able to:

- Hook completions and pre-completions with decorators
- Match arbitrary events — including the step lifecycle events — by type string
- Mutate events and use `StepAbortError` for control flow

## Concepts at a Glance (introduced only when needed)

- **Event**: an object describing something that happened (a completion, a Step
  boundary, a tool call).
- **Matcher**: a handler registered for an event _type string_. Matchers may
  modify the event; the framework reads the modified values back.

The pipeline is event-driven: `Matcher`-based hooks let you intercept stages,
mutate messages, and inject context.

## 1. React to Completions with `@on_completion`

```python
from amrita_core import on_completion
from amrita_core.hook.event import CompletionEvent


@on_completion
async def log_response(event: CompletionEvent):
    print(f"[completion] {event.model_response[:80]}...")
```

`CompletionEvent` carries the final response; you can rewrite
`event.model_response` before it is committed.

## 2. Pre-Completion Hooks with `@on_precompletion`

```python
from amrita_core import on_precompletion
from amrita_core.hook.event import PreCompletionEvent


@on_precompletion
async def inject_context(event: PreCompletionEvent):
    # `event.original_context` is a SendMessageWrap — append anything.
    event.original_context.append(
        Message(role="user", content="[system note] Today is 2026-08-06.")
    )
```

## 3. Custom Events with `@on_event`

Match any event type by string:

```python
from amrita_core import on_event


@on_event("agent.step_intro")
async def on_step_intro(event):
    print(f"[step intro] {event.phase}")
```

### Step lifecycle events (built-in ReAct)

| Event type             | Mutable fields                     | Raised on                      |
| ---------------------- | ---------------------------------- | ------------------------------ |
| `agent.step_intro`     | `override_phase`                   | Step starts                    |
| `agent.step_leave`     | `override_verb`, `override_object` | Step ends (summary override)   |
| `agent.step_iteration` | `end_step`                         | After each tool round          |
| `agent.tool_call`      | `arguments`, `cancel`              | Before a regular tool executes |
| `agent.tool_return`    | `result`, `skip_append`            | After a regular tool returns   |

Handlers can **mutate the event** and the lifecycle hook reads the values back;
they can also raise `StepAbortError` to abort the current operation
(cancel a tool call, end the Step early, skip appending a result).

```python
from amrita_core import on_event
from amrita_core.builtins.agent.events import StepAbortError


@on_event("agent.tool_call")
async def guard_tool(event):
    if event.tool_name == "dangerous_delete":
        event.cancel = True  # or: raise StepAbortError("blocked")
```

## 4. What Just Happened

- `@on_completion` / `@on_precompletion` — pipeline boundaries
- `@on_event("<type>")` — arbitrary events, including step lifecycle
- Events are mutable; `StepAbortError` is the control-flow escape hatch

## Next

[5. Memory and Sessions](memory.md) — persist history across turns.
