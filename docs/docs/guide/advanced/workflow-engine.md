# Workflow Engine

> Starting from AmritaCore v0.9.0rc1, ChatObject is driven by [AmritaSense](https://sense.amritabot.com)'s composable workflow engine.

## Overview

ChatObject's execution pipeline is decomposed into discrete **Nodes**, executed by AmritaSense's `WorkflowInterpreter`. AmritaCore does not implement its own workflow engine — it uses AmritaSense's directly.

The workflow engine's core types (`Node`, `NodeComposeRendered`, `WorkflowInterpreter`) and control-flow instructions (`IF`/`WHILE`/`JUMP`/`TRY`/`CALL`/`ALIAS`) are all provided by AmritaSense.

**Full Documentation:**

| Topic                            | AmritaSense Docs                                                                        |
| -------------------------------- | --------------------------------------------------------------------------------------- |
| Workflow Composition & Execute   | [Compose & Execute](https://sense.amritabot.com/guide/concepts/compose_and_exec)        |
| @Node Decorator & Custom Nodes   | [Custom Nodes](https://sense.amritabot.com/guide/advanced/custom_node)                  |
| Control Flow (IF/WHILE/JUMP/TRY) | [Control Flow](https://sense.amritabot.com/guide/concepts/flow_control)                 |
| ALIAS / Subprogram Calls         | [Control Flow](https://sense.amritabot.com/guide/concepts/flow_control)                 |
| Dependency Injection             | [Dependency Injection](https://sense.amritabot.com/guide/advanced/dependency_injection) |
| Event System                     | [Event System](https://sense.amritabot.com/guide/advanced/event_system)                 |
| Execution & Interrupt            | [Execution & Interrupt](https://sense.amritabot.com/guide/concepts/exec_and_interrupt)  |

## ChatObject Node Chain (v0.12.0+)

Since v0.12.0, core workflow nodes have been extracted to the `amrita_core.components` package. Component nodes are injected with DI context objects via type-annotation-based dependency injection rather than directly accessing `ChatObject` attributes.

```mermaid
graph LR
    A[__entry__] --> B[JINJA2_RENDER]
    B --> C[_limiting_memory]
    C --> D[BUILD_MESSAGE]
    D --> E[_pre_runner]
    E --> F[_run_strategy]
    F --> G[LLM_COMPLETION]
    G --> H[_post_runner]
    H --> I[COMMIT_MEMORY]
    F -.->|agent mode| J[STRATEGY_INIT]
    J --> K[AGENT_ENTRY]
    K --> L[SINGLE_STRATEGY_CALL]
    L -->|WHILE| L
    L --> M[AGENT_POST_PROCESS]
```

The `_run_strategy` node branches into an agent sub-workflow when using `"agent"` or `"agent-mixed"` strategy categories. The sub-workflow uses a `WHILE` loop with a counter factory (`REACT_COUNTER`) to iterate over tool calls.

| Node                   | SuspendEnum Tag     | Location                         | Description                                           |
| ---------------------- | ------------------- | -------------------------------- | ----------------------------------------------------- |
| `LOAD_STATE`           | `LOAD_STATE`        | `amrita_core.components.process` | Loads runtime state from backends                     |
| `JINJA2_RENDER`        | `TRAIN_RENDER`      | `amrita_core.components.llm`     | Renders the Jinja2 system prompt template             |
| `_limiting_memory`     | `MEMORY`            | `chat_object.py` (retained)      | Applies memory length and token limits                |
| `BUILD_MESSAGE`        | `MESSAGES_PREPARED` | `amrita_core.components.process` | Prepares the final message list for the LLM           |
| `_pre_runner`          | `PRECOMPLE`         | `chat_object.py` (retained)      | Triggers pre-completion matcher events                |
| `_run_strategy`        | `STRATEGY_START`    | `chat_object.py` (retained)      | Executes strategy; branches to agent sub-workflow     |
| `STRATEGY_INIT`        | —                   | `amrita_core.components.react`   | Initializes `StrategyContext` with DI resource fields |
| `AGENT_ENTRY`          | —                   | `amrita_core.components.react`   | Initializes agent strategy instance                   |
| `SINGLE_STRATEGY_CALL` | `SINGLE_TOOL`       | `amrita_core.components.react`   | Executes one tool call iteration                      |
| `REACT_COUNTER`        | `ADVANCE_COUNTER`   | `amrita_core.components.react`   | Advances the tool-call counter                        |
| `AGENT_POST_PROCESS`   | —                   | `amrita_core.components.react`   | Post-processes strategy after all tool calls          |
| `LLM_COMPLETION`       | `LLM_CALL`          | `amrita_core.components.llm`     | Calls the LLM via the adapter                         |
| `_post_runner`         | `COMPLE`            | `chat_object.py` (retained)      | Triggers post-completion matcher events               |
| `COMMIT_MEMORY`        | `COMMIT_MEMORY`     | `amrita_core.components.process` | Commits memory back to the backend                    |
| `APPEND_RESPONSE`      | `MEMORY_APPEND`     | `amrita_core.components.process` | Appends LLM response to context wrap                  |
| `APPLY_CONTEXT`        | `APPLY_CONTEXT`     | `amrita_core.components.process` | Writes context wrap back into memory model            |

### Control Flow Instructions

The agent sub-workflow uses AmritaSense v0.3.0+ control flow instructions:

- **`GOTO(BuiltinName.STRATEGY_EOF)`** — Skips the agent sub-workflow when using non-agent strategies
- **`ALIAS(_agent_entry, BuiltinName.AGENT_STRATEGY)`** — Registers the agent entry point as a subprogram target
- **`WHILE(_single_strategy_exec).ACTION(_counter_factory())`** — Loops tool call execution with a counter to enforce call limits
- **`ALIAS(NOP, BuiltinName.STRATEGY_EOF)`** — Marks the end of the agent sub-workflow

### SuspendEnum Tags

Since v0.9.1, additional suspend tags are available:

- `SuspendEnum.ADVANCE_COUNTER` — Before advancing the tool call counter
- `SuspendEnum.STRATEGY_EOF` — At the end of the agent strategy sub-workflow

## AmritaCore-Specific Concepts

### WorkflowInterpreter Integration

ChatObject assembles the workflow in `__init__` and executes it:

- `_middleware` parameter can wrap the entire workflow
- `archived_nodes` parameter appends custom nodes after the standard pipeline
- `BuiltinName.AGENT_STRATEGY` alias enables subprogram calls

### BuiltinName

```python
from amrita_core.chatmanager import BuiltinName
BuiltinName.AGENT_STRATEGY  # "ChatObject::__agent_main__"
```

### Middleware

```python
async def my_middleware(chat_obj: ChatObject) -> None:
    """Middleware that wraps the entire ChatObject workflow."""
    logger.info("Workflow starting...")
    try:
        await chat_obj._interpreter.run()
    finally:
        logger.info("Workflow finished.")

chat = ChatObject(
    ...,
    middleware=my_middleware,
)
```

### Extending with archived_nodes

```python
from amrita_sense import Node
from amrita_sense.instructions import ARCHIVED_NODES

custom_nodes = ARCHIVED_NODES()

@Node("custom_logging")
async def log_completion(self):
    logger.info(f"Response: {self.response.content}")

custom_nodes._nodes += (log_completion,)

chat = ChatObject(..., archived_nodes=custom_nodes)
```

## Pre-composed Workflows (v0.12.6+)

Since v0.12.6, AmritaCore ships pre-composed workflow pipelines in `amrita_core.builtins.workflows`. These are ready-to-use `NodeComposeRendered` graphs that can be passed directly to `ChatObject(workflow=...)`.

| Workflow       | Composition                                                                                      | Use Case                              |
| -------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------- |
| `REACT_BLOCK`  | `STRATEGY_INIT >> AGENT_ENTRY >> WHILE(...) >> AGENT_POST_PROCESS`                               | ReAct loop block (no LLM completion)  |
| `SIMPLE_REACT` | `LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> REACT_BLOCK >> LLM_COMPLETION >> COMMIT_MEMORY` | Full ReAct pipeline with tool calling |
| `REACT_ONLY`   | `LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> REACT_BLOCK`                                    | ReAct pipeline without final LLM call |
| `SIMPLE_CHAT`  | `LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> LLM_COMPLETION >> COMMIT_MEMORY`                | Plain chat without agent/tool calling |

### Using Custom Workflows

Pass a pre-composed workflow via the `workflow` parameter:

```python
from amrita_core import ChatObject
from amrita_core.builtins.workflows import SIMPLE_REACT, SIMPLE_CHAT

# Use the full ReAct pipeline
chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Search for the latest AI news.",
    session_id="session_123",
    workflow=SIMPLE_REACT,
)

# Or use plain chat (no agent)
chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Hello!",
    session_id="session_456",
    workflow=SIMPLE_CHAT,
)
```

> **Note**: `workflow` and `archived_nodes` are **mutually exclusive** — providing both raises a `ValueError`. When neither is supplied, the built-in default pipeline is used.

## Migration from v0.8.x

| Old Approach                            | New Approach                               |
| --------------------------------------- | ------------------------------------------ |
| Override `_run()`                       | `@Node` decorator + `archived_nodes`       |
| `from amrita_core.protocol import ...`  | `from amrita_core.base.adapter import ...` |
| `from amrita_core.streaming import ...` | `from amrita_sense.streaming import ...`   |
| `from amrita_core.logging import ...`   | `from amrita_sense.logging import ...`     |
