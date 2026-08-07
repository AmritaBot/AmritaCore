# AmritaSense Overview

**We recap the pieces of AmritaSense that AmritaCore builds on.** Full
documentation lives at [sense.amritabot.com](https://sense.amritabot.com).

## The Idea

AmritaSense compiles workflows into a **linear instruction sequence** executed
by a lightweight VM — much like a CPU runs machine code. Nodes are chained with
`>>`; control flow is native instructions (`IF`, `WHILE`, `GOTO`, `CALL`,
`TRY`, `NOP`).

```python
from amrita_sense import Node, WorkflowInterpreter


@Node()
async def step_one() -> None:
    print("[1] load state")


@Node()
async def step_two() -> None:
    print("[2] process")


composition = step_one >> step_two
interpreter = WorkflowInterpreter(composition.render())
await interpreter.run()
```

## What Core Uses from Sense

| Sense primitive                     | Where Core uses it                                                 |
| ----------------------------------- | ------------------------------------------------------------------ |
| `@Node`                             | Every component (`components/llm.py`, `process.py`, `react.py`)    |
| `WorkflowInterpreter`               | `ChatObject._interpreter` runs the conversation pipeline           |
| Dependency injection (type-matched) | Workflow nodes receive `AgentLoopState`, `AbilityState`, ...       |
| `SuspendObjectStream`               | `ChatObject.io_stream` — bidirectional streaming                   |
| Matcher events                      | The pipeline/step hook system (see [Events](../concepts/event.md)) |
| NATIVE instructions                 | The built-in step loop (`NATIVE_DO`/`NATIVE_WHILE`)                |

## The VM

- **Program counter** (`PointerVector`) + call stack drive execution
- Nodes resolve dependencies before running (DI)
- Every node boundary catches exceptions
- `run_step_by()` yields each step for debugging

See [Workflow Engine](workflow-engine.md) for how ChatObject composes its
pipeline, and [sense.amritabot.com](https://sense.amritabot.com/guide/concepts/compose_and_exec)
for the engine reference.
