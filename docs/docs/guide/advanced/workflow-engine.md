# Workflow Engine

## The Pipeline

Every `ChatObject` runs a pre-compiled workflow. The **default** pipeline is
the simple chat one (one LLM call, no decomposition); the step-driven variant
is opted into by passing `workflow=_step_workflow_rendered` (or
`SIMPLE_STEP_REACT`). Both share the same outer shell:

```mermaid
flowchart LR
    A["LOAD_STATE"] --> B["JINJA2_RENDER"]
    B --> C["BUILD_MESSAGE"]
    C --> D["_pre_runner (events)"]
    D --> E["_run_strategy → strategy block"]
    E --> F["LLM_COMPLETION"]
    F --> G["_post_runner (events)"]
    G --> H["COMMIT_MEMORY"]
```

The **strategy block** is what changes by mode. Simple chat skips it entirely;
the step-driven loop runs:

```mermaid
flowchart LR
    S["_run_strategy<br/>(dispatch on get_category)"] -->|agent / agent-mixed| J["jump_to AGENT_STRATEGY"]
    J --> K["AGENT_ENTRY<br/>(instantiate strategy)"]
    K --> L["NATIVE_DO(STEP_BODY).WHILE(task_cond)"]
    L --> M["AGENT_POST_PROCESS"]
```

```python
# STEP_BODY — one task-loop iteration = one Step
STEP_BODY = NODE_INTRO >> NATIVE_WHILE(iter_cond).ACTION(STEP_EXEC) >> NODE_LEAVE
```

## DI Contexts as the State Layer

Workflow nodes are **stateless functions**; all state lives in DI contexts
injected by parameter type (see [Data Layer](../concepts/data.md)). This is
what makes the same nodes reusable across pipelines.

## Pre-Composed Pipelines

`amrita_core.builtins.workflows` ships ready graphs. Two families, one choice
per family:

| Pipeline                | Composition                                                                                                                                       |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `STEP_REACT_BLOCK`      | `STRATEGY_INIT >> AGENT_ENTRY >> NATIVE_DO(STEP_BODY).WHILE(task_cond) >> AGENT_POST_PROCESS`                                                     |
| `SIMPLE_STEP_REACT`     | `LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> STEP_REACT_BLOCK >> LLM_COMPLETION >> COMMIT_MEMORY`                                             |
| `STEP_REACT_ONLY`       | `LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> STEP_REACT_BLOCK`                                                                                |
| `CHATOBJECT_STEP_REACT` | `ARCHIVED_SEGMENT(ALIAS(AGENT_ENTRY, AGENT_STRATEGY) >> NATIVE_DO(STEP_BODY).WHILE(task_cond) >> AGENT_POST_PROCESS) >> ALIAS(NOP, STRATEGY_EOF)` |
| `REACT_BLOCK` (legacy)  | `STRATEGY_INIT >> AGENT_ENTRY >> WHILE(SINGLE_STRATEGY_CALL).ACTION(REACT_COUNTER) >> AGENT_POST_PROCESS`                                         |
| `SIMPLE_REACT` (legacy) | `LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> REACT_BLOCK >> LLM_COMPLETION >> COMMIT_MEMORY`                                                  |
| `REACT_ONLY` (legacy)   | `LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> REACT_BLOCK`                                                                                     |
| `SIMPLE_CHAT`           | `LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> LLM_COMPLETION >> COMMIT_MEMORY`                                                                 |

**How to choose**:

- `SIMPLE_CHAT` — plain single-turn chat, no agent loop. This is the default
  (`workflow=None` resolves here).
- `*_ONLY` variants stop after the agent block: no final `LLM_COMPLETION`
  flush, no memory commit. Use them when you compose the tail yourself.
- `SIMPLE_*` variants are the full pipeline (prelude + block + completion +
  commit) in one object — pass the object directly to
  `get_chatobject(workflow=...)`.
- `STEP_REACT_BLOCK` / `SIMPLE_STEP_REACT` / `STEP_REACT_ONLY` run the
  **step-driven** loop (the opt-in ReAct mode; see
  [The Step Loop](step-loop.md)).
- `REACT_BLOCK` / `SIMPLE_REACT` / `REACT_ONLY` are the legacy single-call
  loop — kept for compatibility, prefer the step-driven family.
- `CHATOBJECT_STEP_REACT` is the internal variant used when a strategy block
  is archived (JMP-skipped) inside the ChatObject runner — `_run_strategy`
  jumps to `AGENT_STRATEGY`, and a trailing `NOP` aliased `STRATEGY_EOF`
  provides the fall-through. You normally don't pass it by hand.

`ChatObject(workflow=...)` accepts any rendered graph; `workflow` and
`archived_nodes` are mutually exclusive. The default `workflow=None` resolves
to the simple chat pipeline — pass `_step_workflow_rendered` (from
`amrita_core.chatmanager`) for the step-driven loop, or use `SIMPLE_STEP_REACT`
for the full pipeline in one object.

## The Loop Conditions

| Condition   | Stops when                                                                    |
| ----------- | ----------------------------------------------------------------------------- |
| `task_cond` | Call limit hit, `_suggested_stop`, stall injected, or all DAG nodes done      |
| `iter_cond` | Call limit, stall, token budget exhausted, `exec_finished`, or stop suggested |

Both live in `amrita_core.components.react` and read `loop.run_state` — the
semantic state bridged between the loop and the strategy.

## Next

[Suspend & Resume](suspend.md) — pausing the workflow mid-flight.
