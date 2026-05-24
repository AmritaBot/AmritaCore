# StrategyLikedObject

`StrategyLikedObject` is an abstract base class for agent strategy **instances**. Unlike `AgentStrategy` which receives a **type** (`type[AgentStrategy]`) and is instantiated by the framework for every request, `StrategyLikedObject` is passed directly as an already-initialised instance into `ChatObject`.

## Overview

This class enables **stateful strategies** — the strategy object can carry its own internal state machine, pre-configured parameters, and resources without relying on class-level attributes or global state.

The framework invokes the strategy by calling `strategy(ctx)` once the execution context is ready, which populates `ctx`, `chat_object`, `session`, and `tools_manager`. From that point onward the same instance is used for the lifetime of the conversation, guaranteeing perfect isolation between concurrent dialogs.

### Relationship with AgentStrategy

`AgentStrategy` remains the preferred choice when a strategy is stateless and can be described purely by a class. `ChatObject` accepts both a `StrategyLikedObject` instance and an `AgentStrategy` **type**; the latter is simply instantiated on first use to preserve backward compatibility.

## Strategy Categories

Different strategy categories have different execution patterns:

| Category        | Method             | Description                                                  |
| --------------- | ------------------ | ------------------------------------------------------------ |
| `"agent"`       | `single_execute()` | Step-by-step tool calling, managed by the framework          |
| `"rag"`         | `run()`            | Minimal context (only system message and user query)         |
| `"workflow"`    | `run()`            | Full manual control over tool calling and context management |
| `"agent-mixed"` | `single_execute()` | Handles both RAG and Agent modes dynamically                 |

## Attributes

| Attribute       | Type                  | Description                                                               |
| --------------- | --------------------- | ------------------------------------------------------------------------- |
| `session`       | `SessionData \| None` | The session data associated with the current chat session                 |
| `tools_manager` | `MultiToolsManager`   | Manager for handling available tools in the current context               |
| `chat_object`   | `ChatObject`          | The chat object for yielding responses and managing the conversation flow |
| `ctx`           | `StrategyContext`     | The strategy context containing execution parameters and configuration    |

## Methods

### `__call__(ctx: StrategyContext) -> Self`

Called once by the framework when the execution context is ready. Subclasses may override this to perform additional initialisation, but **must** call `super().__call__(ctx)` first.

**Parameters:**

- `ctx` (`StrategyContext`): The execution context

**Returns:** `Self`

---

### `async single_execute() -> bool`

Execute a single agent step for `"agent"` and `"agent-mixed"` category strategies. Called by the framework to perform one iteration of tool calling.

**Returns:** `True` if should continue to next execution, `False` to stop.

**Note:** This method is used by `"agent"` and `"agent-mixed"` category strategies. `"rag"` and `"workflow"` category strategies should implement `run()` instead.

---

### `async run() -> None`

Run the complete agent strategy for `"rag"` and `"workflow"` category strategies. Gives full control to the strategy implementation for managing tool calling iterations, context construction, error handling, and response generation.

**Category-specific behavior:**

- `"rag"`: Minimal context containing only system message and user query
- `"workflow"`: Complete manual control over everything

**Note:** This method is used by `"rag"` and `"workflow"` category strategies. `"agent"` and `"agent-mixed"` category strategies should implement `single_execute()` instead.

---

### `async call_tool(tool_call: ToolCall) -> str`

Execute a single tool call without modifying the agent's context.

**Parameters:**

- `tool_call` (`ToolCall`): The ToolCall object containing the function name and arguments

**Raises:**

- `RuntimeError`: If the requested tool is not found in the tools manager

**Returns:** `str` — The string response from the tool execution, or a default message if the tool returns `None`

---

### `async on_limited() -> None`

Handle the event when the agent reaches its tool calling limit. Called when the agent strategy has reached the maximum allowed number of tool calls.

**Default behavior:** Sends a notification message to the user about the limit being reached.

---

### `async on_exception(exc: BaseException) -> None`

Handle exceptions that occur during strategy execution.

**Parameters:**

- `exc` (`BaseException`): The exception that occurred

---

### `async on_post_process() -> None`

Used to process after all steps are completed successfully.

---

### `classmethod get_category() -> Literal["agent", "workflow", "rag", "agent-mixed"]`

Get the category of the agent strategy. This is an abstract method that must be implemented by subclasses.

**Returns:** The strategy category as a literal string.

## Usage Example

```python
from amrita_core.agent.strategy import StrategyLikedObject
from amrita_core.agent.context import StrategyContext

class MyCustomStatefulStrategy(StrategyLikedObject):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.call_count = 0

    @classmethod
    def get_category(cls) -> str:
        return "agent"

    async def single_execute(self) -> bool:
        self.call_count += 1
        # Custom agent logic here...
        return self.call_count < 5  # Stop after 5 calls

# Pass instance directly to ChatObject
strategy = MyCustomStatefulStrategy(api_key="sk-...")
chat_obj = ChatObject(
    train={"system": "You are a helpful assistant"},
    user_input="Hello",
    context=None,
    session_id="session_123",
    agent_strategy=strategy,  # Pass instance, not class
)
```
