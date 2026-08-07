# AgentRunState

`AgentRunState` is the **semantic step-level run state** of the built-in
step-driven ReAct strategy. It lives outside the workflow and is shared between
`AgentLoopState.run_state` and the strategy (one instance, bridged by
`AGENT_ENTRY`).

```python
from amrita_core.builtins.agent.state import AgentRunState

state = AgentRunState()
state.begin_step("execute")
```

## Fields

| Field                  | Type                    | Meaning                                                          |
| ---------------------- | ----------------------- | ---------------------------------------------------------------- |
| `step_index`           | `int`                   | Global step counter (1-based)                                    |
| `current_phase`        | `str \| None`           | The active phase — a DAG node id (or `"execute"` in simple mode) |
| `plan`                 | `list[DAGNode] \| None` | The task DAG (`None` = no decomposition)                         |
| `simple_mode`          | `bool`                  | True when the LLM decided to run directly                        |
| `current_step_id`      | `str \| None`           | Id of the DAG node being executed                                |
| `completed_step_ids`   | `list[str]`             | Finished DAG node ids (dependency check)                         |
| `plan_revision`        | `int`                   | `update_step` revision counter                                   |
| `step_tool_signatures` | `list[str]`             | Tool-call signatures in the current Step (stall window)          |
| `stall_injected`       | `bool`                  | Give-up prompt injected (once per Step)                          |
| `last_summary`         | `StepSummary \| None`   | Subject-predicate summary of the previous Step                   |
| `tokens`               | `TokenBudget`           | Real API token accounting                                        |
| `exec_finished`        | `bool`                  | Strategy done calling tools → iteration loop ends                |

## Methods

| Method                              | Purpose                                                                                            |
| ----------------------------------- | -------------------------------------------------------------------------------------------------- |
| `begin_step(phase)`                 | Enter a new Step: advance counter, reset per-Step state                                            |
| `begin_node(node)`                  | `begin_step(node.id)` + track `current_step_id`                                                    |
| `record_tool_call(signature)`       | Record a tool signature in the current Step                                                        |
| `is_stalled(threshold)`             | True when the last N signatures are identical                                                      |
| `would_stall(signature, threshold)` | True if recording this signature would trip the detector (pre-execution cancel)                    |
| `next_ready_node()`                 | Next DAG node in topological order (`graphlib.TopologicalSorter`; cyclic plans degrade gracefully) |
| `complete_current_node()`           | Mark the current node done                                                                         |
| `all_plan_done()`                   | True when every DAG node is completed                                                              |

## Related

- [DAGNode](DAGNode.md) — a plan sub-step
- [StepSummary](StepSummary.md) — subject-predicate summary
- [TokenBudget](TokenBudget.md) — token accounting
- See [Advanced → Step Loop](../advanced/step-loop.md) for the full picture
