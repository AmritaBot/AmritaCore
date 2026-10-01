# Agent Strategy

## The Strategy Contract

A strategy implements the `AgentStrategy` ABC (or `StrategyLikedObject` for
stateful instances) and declares a **category** via `get_category()`:

| Category                | Execution                    | Framework's role          |
| ----------------------- | ---------------------------- | ------------------------- |
| `agent` / `agent-mixed` | `single_execute()` per round | Framework runs the loop   |
| `rag` / `workflow`      | `run()` once                 | Strategy has full control |

Dispatch is workflow control flow, not Python: `_prepare_strategy` only builds
the `StrategyContext`, then two guarded branches pick the execution shape —
`NATIVE_IF(is_agent_category, ...)` runs the framework loop, and
`NATIVE_IF(not_agent_category, RUN_INLINE_STRATEGY)` calls `run()` once. Each
branch is skipped when its predicate is false, so no category can execute
twice (see [Workflow Engine](../advanced/workflow-engine.md)).

## Resource Access via DI

Strategies never reach through `ChatObject` for resources — `_StrategyBase`
exposes **convenience properties** that resolve from `StrategyContext` DI
fields, falling back to `chat_object`:

| Property                | Resolves from          | Fallback                           |
| ----------------------- | ---------------------- | ---------------------------------- |
| `self.preset`           | `ctx.preset`           | `chat_object.preset`               |
| `self.config`           | `ctx.config`           | `chat_object.config`               |
| `self.io_stream`        | `ctx.io_stream`        | `chat_object.io_stream`            |
| `self.train_content`    | `ctx.train_content`    | `chat_object.train.content`        |
| `self.stream_id`        | `ctx.stream_id`        | `chat_object.stream_id`            |
| `self.usage`            | `ctx.usage`            | `chat_object._di_resp.usage`, else `None` |

> `self.usage` is the run-scoped `SessionUsageProxy` ledger. It covers
> workflow-internal usage (strategy tool rounds plus auxiliary calls); the
> final completion's usage lives on `resp.response.usage`.

> `chat_object` is the **lifecycle-manager handle** — the core reference, not
> a deprecated path. Prefer DI fields; fall back to `chat_object`.

## The Built-in Step-Driven ReAct Strategy

`ReActAgentStrategy` (category `agent-mixed`) is the default strategy class.
Its execution is **node-driven**: the LLM decides whether to decompose the task
into a semantic DAG; the framework walks the DAG in topological order, one
**Step** per node.

```
intro_step → [NATIVE_WHILE: single_execute → after_iteration] → leave_step
```

- **decompose** — LLM returns `{needs_decomposition, dag, reason}`.
  **SIMPLE mode (`needs_decomposition=false`) is still ReAct** — the normal
  tool loop runs; it is just not step-driven (no DAG decomposition). Routine
  questions and simple tasks are assigned to this mode by default.
- **Step** — one DAG node; may span multiple tool rounds
- **stall detection** — repeated identical signatures → give-up prompt + cancel
- **summarize** — each Step ends with a subject-predicate summary (event-overridable)
- **lifecycle events** — `step_intro/leave/iteration`, `tool_call/return`
- **update_step tool** — the agent can revise the plan mid-run

> **Opt-in workflow.** The strategy class is the default, but the Step loop
> only runs when the **step-loop workflow** is active. `ChatObject` defaults
> to `_workflow_rendered`, whose agent branch is the **legacy single-call
> loop** (`AGENT_BLOCK`) — one `single_execute` per round, no DAG
> decomposition; pass `workflow=_step_workflow_rendered` (or
> `SIMPLE_STEP_REACT`) to enable the loop above. See
> [ChatObject](chat-object.md) and
> [Advanced → Step Loop](../advanced/step-loop.md).

Full details: [Advanced → Step Loop](../advanced/step-loop.md).

## Other Built-in Strategies

| Strategy                | Category   | Use case                   |
| ----------------------- | ---------- | -------------------------- |
| `NoActionAgentStrategy` | `workflow` | Skip tool calling entirely |

## Writing a Custom Strategy

```python
from amrita_core.agent.strategy import AgentStrategy
from typing import Literal


class MyStrategy(AgentStrategy):
    async def single_execute(self) -> bool:
        # One tool round. Return True to continue, False to stop.
        return True

    async def on_post_process(self) -> None:
        pass  # after the loop

    @classmethod
    def get_category(cls) -> Literal["agent"]:
        return "agent"
```

For ReAct-style strategies, extend `BaseReActAgentStrategy` instead and
override the template methods (`_append_tool_result_to_context`,
`_handle_error_append`, `_append_reasoning`, ...).

## Next

[Data Layer](data.md) — messages, memory and backends.
