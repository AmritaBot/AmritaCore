# API Reference

This reference is organized by functional module. Each entry links to the class page for full documentation.

## Core API Functions

### `load_amrita()`

The `load_amrita()` function asynchronously loads MCP clients when MCP is enabled in the configuration. Tokenizers and adapters are already registered at import time — `load_amrita()` does not load them.

```python
import asyncio
from amrita_core import load_amrita


async def main():
    await load_amrita()


asyncio.run(main())
```

**Usage Notes**:

- No longer requires `init()` to be called first (since v0.9.0rc1)
- Should be called after `set_config()` if custom configuration is used
- When MCP is enabled, it's required to call `load_amrita()`

### `minimal_init()`

The `minimal_init()` function performs minimal initialization: it applies the config and loads MCP clients if enabled. Tokenizers and adapters are already registered at import time.

```python
from amrita_core import minimal_init

await minimal_init()
```

### `set_config(config)`

The `set_config()` function applies a configuration to AmritaCore.

```python
from amrita_core.config import AmritaConfig, set_config

config = AmritaConfig()
set_config(config)
```

**Parameters**:

- `config` ([AmritaConfig](classes/AmritaConfig.md)): The configuration object to set

**Usage Notes**:

- Should be called before `load_amrita()`

### `get_config()`

The `get_config()` function retrieves the current AmritaCore configuration.

```python
from amrita_core.config import get_config

config = get_config()
print(config.function_config.use_minimal_context)
```

**Returns**: [AmritaConfig](classes/AmritaConfig.md) - The current configuration object

**Usage Notes**:

- Throws `RuntimeError` if AmritaCore is not initialized

### `create_agent()`

The `create_agent()` factory function creates an agent with minimal parameters by automatically creating a temporary preset. **This is the recommended entry point for building agents.**

```python
from amrita_core import create_agent

agent = create_agent(
    "https://api.example.com",  # Replace with your API URL
    "your-api-key",  # Replace with your API key
    model="gpt-4",  # Replace with your desired model
    model_config={"temperature": 0.7},
)
```

**Parameters**:

- `base_url` (str): The API endpoint URL
- `api_key` (str): The API key for authentication
- `model` (str, optional): The model to use. Defaults to `"auto"`
- `train` (str | None, optional): System prompt; defaults to built-in instructions
- `model_config` ([ModelConfig](classes/ModelConfig.md) | dict | None, optional): Optional model configuration. Defaults to None
- `config` ([AmritaConfig](classes/AmritaConfig.md) | None, optional): Configuration for the agent. Defaults to global config
- `**kwargs`: Additional keyword arguments forwarded to [AgentRuntime](classes/AgentRuntime.md) (e.g. `strategy`, `template`, `session_id`, `backend`)

**Returns**: [AgentRuntime](classes/AgentRuntime.md) - Configured agent runtime instance

**Usage Notes**:

- The function automatically creates a temporary preset; use [PresetManager](classes/PresetManager.md) for persistent presets
- The returned agent can be reused for multiple interactions via `get_chatobject()`
- `create_agent()` has **no `protocol` parameter** — it always builds a preset with the default protocol (`"__main__"`, the OpenAI-compatible adapter). The provider is chosen by `base_url` + `model`; DeepSeek, Azure or any OpenAI-compatible endpoint works through the same adapter. To use the Anthropic wire format, construct a `ModelPreset` with `protocol="anthropic"` and pass it to `AgentRuntime` directly — see [Model Adapters](../extensions-integration/adapters.md)

## Configuration

| Class                                       | Description                                                             |
| ------------------------------------------- | ----------------------------------------------------------------------- |
| [AmritaConfig](classes/AmritaConfig.md)     | Central configuration object (function_config / llm / cookie / builtin) |
| [FunctionConfig](classes/FunctionConfig.md) | Functional behavior: context, tokenizer, tool call limit, MCP client    |
| [LLMConfig](classes/LLMConfig.md)           | LLM behavior: token limits, retries, fallbacks, memory summarization    |
| [CookieConfig](classes/CookieConfig.md)     | Cookie leak detection mechanism                                         |

## Chat Management

| Class                                       | Description                                     |
| ------------------------------------------- | ----------------------------------------------- |
| [ChatObject](classes/ChatObject.md)         | Core class for individual conversations         |
| [ChatManager](classes/ChatManager.md)       | Manages running ChatObject instances            |
| [ChatObjectMeta](classes/ChatObjectMeta.md) | Metadata model for ChatObject snapshots         |
| [SuspendEnum](classes/SuspendEnum.md)       | Standardized breakpoint tags for suspend/resume |

## Types

| Class                                           | Description                                             |
| ----------------------------------------------- | ------------------------------------------------------- |
| [Message](classes/Message.md)                   | A single message in the conversation                    |
| [SendMessageWrap](classes/SendMessageWrap.md)   | Iterable wrapper for the message list sent to the model |
| [MemoryModel](classes/MemoryModel.md)           | Stores conversation history                             |
| [ModelConfig](classes/ModelConfig.md)           | Model-specific behavior parameters                      |
| [ModelPreset](classes/ModelPreset.md)           | Complete configuration for a specific model             |
| [ThinkingConfig](classes/ThinkingConfig.md)     | Thinking/reasoning configuration                        |
| [TextContent](classes/TextContent.md)           | Text content within messages                            |
| [ToolCall](classes/ToolCall.md)                 | An invocation of a tool                                 |
| [ToolResult](classes/ToolResult.md)             | The result of a tool invocation                         |
| [UniResponse](classes/UniResponse.md)           | Unified response format                                 |
| [UniResponseUsage](classes/UniResponseUsage.md) | Usage statistics for responses                          |
| [EmbeddingChunk](classes/EmbeddingChunk.md)     | Embedding vector returned by the embedding adapter      |
| [BaseModel](classes/BaseModel.md)               | Base class for all data models                          |

## Tools

| Class                                                           | Description                                                  |
| --------------------------------------------------------------- | ------------------------------------------------------------ |
| [FunctionDefinitionSchema](classes/FunctionDefinitionSchema.md) | Function definition schema (name, description, parameters)   |
| [ToolFunctionSchema](classes/ToolFunctionSchema.md)             | Complete function-calling schema (function + type + strict)  |
| [ToolData](classes/ToolData.md)                                 | Data model for registering tools (metadata + implementation) |
| [ToolContext](classes/ToolContext.md)                           | Context passed to tool functions during execution            |
| [ToolsManager](classes/ToolsManager.md)                         | Singleton tool registry                                      |
| [MultiToolsManager](classes/MultiToolsManager.md)               | Multi-instance tool registry with enable/disable support     |
| [MCPClient](classes/MCPClient.md)                               | MCP client for connecting to MCP servers                     |
| [ClientManager](classes/ClientManager.md)                       | Manages a single MCP client                                  |
| [MultiClientManager](classes/MultiClientManager.md)             | Manages multiple MCP clients                                 |

## Backends & Contexts

| Class                                               | Description                                               |
| --------------------------------------------------- | --------------------------------------------------------- |
| [BackendSlots](classes/BackendSlots.md)             | Bundles ability and memory backends for I/O               |
| [AbilityBackend](classes/AbilityBackend.md)         | Abstract base for loading tools, MCP clients, and presets |
| [MemoryBackend](classes/MemoryBackend.md)           | Abstract base for loading and committing memory           |
| [LegacyBackend](classes/LegacyBackend.md)           | Default in-process backend implementation                 |
| [AbilityContext](classes/AbilityContext.md)         | Runtime ability state (tools, presets, MCP clients)       |
| [StateContext](classes/StateContext.md)             | Runtime session state (session_id, memory, ability)       |
| [DatabackendOptions](classes/DatabackendOptions.md) | Fine-grained control over backend fetch/commit operations |

## Agent Strategies

| Class                                                           | Description                                        |
| --------------------------------------------------------------- | -------------------------------------------------- |
| [AgentRuntime](classes/AgentRuntime.md)                         | Agent runtime wrapper returned by `create_agent()` |
| [AgentStrategy](classes/AgentStrategy.md)                       | Abstract base class for agent strategies           |
| [StrategyContext](classes/StrategyContext.md)                   | Context passed to strategy execution               |
| [BaseReActAgentStrategy](classes/BaseReActAgentStrategy.md)     | Base ReAct strategy implementation                 |
| [ReActAgentStrategy](classes/ReActAgentStrategy.md)             | Standard ReAct strategy                            |
| [HybridReActAgentStrategy](classes/HybridReActAgentStrategy.md) | Hybrid ReAct strategy                              |
| [NoActionAgentStrategy](classes/NoActionAgentStrategy.md)       | Strategy that performs no actions                  |

## Events & Hooks

| Class                                               | Description                                                                                                                                              |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [CompletionEvent](classes/CompletionEvent.md)       | Fired after model completion (event type `COMPLETION`)                                                                                                   |
| [PreCompletionEvent](classes/PreCompletionEvent.md) | Fired before strategy run and completion (`BEFORE_COMPLETION`)                                                                                           |
| [FallbackContext](classes/FallbackContext.md)       | Base context for preset fallback events (`PRESET_FALLBACK`); subclasses: `CompletionFallbackContext`, `ToolsFallbackContext`, `EmbeddingFallbackContext` |

## Presets & Tokenizers

| Class                                               | Description                                           |
| --------------------------------------------------- | ----------------------------------------------------- |
| [PresetManager](classes/PresetManager.md)           | Manages model presets                                 |
| [MultiPresetManager](classes/MultiPresetManager.md) | Multi-instance preset management with testing support |
| [BaseTokenizer](classes/BaseTokenizer.md)           | Abstract base class for custom tokenizers             |
| [ModelAdapter](classes/ModelAdapter.md)             | Abstract base class for model adapters                |

## Decorators

### `@simple_tool`

The `@simple_tool` decorator is used to register a simple tool.

```python
from amrita_core import simple_tool


@simple_tool
def add(a: int, b: int) -> int:
    """Add number

    Args:
        a (int): First number
        b (int): Second number
    """
    return a + b
```

**Purpose**: Register a simple tool with automatic schema inference from type annotations and docstrings.

**Supported Parameter Types**:

- Basic types: `str`, `int`, `float`, `bool`
- Literal types: `Literal["a", "b"]` → auto-generates `string` + `enum` constraint; `Literal[1, 2, 3]` likewise supports `integer` enum
- Pydantic BaseModel classes for complex nested structures
- Container types: `List[T]` (single-level only)
- Optional types: `Optional[T]` or `T | None`

**Unsupported Types** (will raise ValueError):

- Dict types (use Pydantic models instead)
- Nested containers (e.g., `List[List[str]]`)
- Multi-type unions (e.g., `str | int`)
- `Any` or `object` types

**Registration Behavior**:

- Tools are registered to the **global container** during module loading
- Available to all sessions since registration happens before session creation
- For session-specific tool management, use direct `MultiToolsManager` operations instead

**Usage Notes**:

- The tool is registered with the name of the function
- The description of each parameter comes from the function's docstring (Google-style)
- All function parameters must have type annotations (no untyped parameters allowed)

### `@on_tools`

The `@on_tools` decorator registers functions as callable tools for the agent.

```python
from typing import Any

from amrita_core import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

DEFINITION = FunctionDefinitionSchema(
    name="Add number",
    description="Add two numbers",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "a": FunctionPropertySchema(type="number", description="The first number"),
            "b": FunctionPropertySchema(type="number", description="The second number"),
        },
        required=["a", "b"],
    ),
)


@on_tools(DEFINITION)
async def add(data: dict[str, Any]) -> str:
    """Add two numbers"""
    return str(data["a"] + data["b"])
```

**Purpose**: Registers a function as an available tool that the agent can call with fine-grained control over the tool schema.

**Registration Behavior**:

- Like `@simple_tool`, registers to the **global container** during module loading
- Provides explicit control over tool schema definition
- Suitable for complex validation requirements not supported by `@simple_tool`

**Usage Notes**:

- Function must have proper type hints for parameters
- Function docstring becomes the tool description

### `@on_event`

The `@on_event` decorator registers functions as event handlers.

```python
from amrita_core.hook.on import on_event


@on_event()
def my_event_handler(event):
    # Handle custom events
    pass
```

**Purpose**: Registers a function to handle specific events during the processing pipeline.

### `@on_precompletion`

The `@on_precompletion` decorator registers functions to run before the completion request is sent to the LLM.

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion


@on_precompletion().handle()
async def preprocess_request(event: PreCompletionEvent):
    # Modify the messages before sending to LLM
    print(event)
```

**Purpose**: Runs before sending the request to the LLM, allowing modification of messages or other preprocessing.

### `@on_completion`

The `@on_completion` decorator registers functions to run after receiving the completion from the LLM.

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion


@on_completion().handle()
async def postprocess_response(event: CompletionEvent):
    # Process the response after receiving from LLM
    print(event)
```

**Purpose**: Runs after receiving the response from the LLM, allowing post-processing of the response.

## Type Definitions

### Predefined Types

AmritaCore provides several predefined types for consistency:

- [BaseModel](classes/BaseModel.md): Base class for all data models
- [EmbeddingChunk](classes/EmbeddingChunk.md): Represents an embedding vector returned by embedding adapter
- [FunctionDefinitionSchema](classes/FunctionDefinitionSchema.md): Schema for function parameters
- [MemoryModel](classes/MemoryModel.md): Stores conversation history
- [ModelConfig](classes/ModelConfig.md): Model-specific configuration
- [ModelPreset](classes/ModelPreset.md): Complete configuration for a specific model
- [ChatManager](classes/ChatManager.md): Manages running ChatObject instances
- [ChatObjectMeta](classes/ChatObjectMeta.md): Metadata model for ChatObject snapshots
- [SuspendEnum](classes/SuspendEnum.md): Standardized breakpoint tags for suspend/resume mechanism
- [TextContent](classes/TextContent.md): Represents text content within messages
- [ToolCall](classes/ToolCall.md): Represents an invocation of a tool
- [ToolContext](classes/ToolContext.md): Provides context for tool execution
- [ToolResult](classes/ToolResult.md): Represents the result of a tool invocation
- [ToolsManager](classes/ToolsManager.md): Manages registered tools
- [UniResponse](classes/UniResponse.md): Unified format for responses
- [UniResponseUsage](classes/UniResponseUsage.md): Usage statistics for responses

### Step-Loop Types (built-in ReAct)

- [AgentRunState](classes/AgentRunState.md): Semantic step-level run state (plan, stall window, tokens)
- [DAGNode](classes/DAGNode.md): A sub-step of the task plan
- [StepEvents](classes/StepEvents.md): The mutable step lifecycle events (`step_intro` / `step_leave` / `step_iteration` / `tool_call` / `tool_return`) and `StepAbortError`

See [Advanced → Step Loop](../advanced/step-loop.md) for how they fit together.

### Exception Types

AmritaCore may raise the following exceptions:

- `RuntimeError`: Raised when accessing configuration before initialization
- `ValueError`: Raised when invalid values are provided to functions
- `TypeError`: Raised when incorrect types are passed to functions

### Type Checking

AmritaCore uses Pydantic models extensively for type validation. When creating custom components, ensure proper type annotations:

```python
from typing import Optional
from amrita_core.types import BaseModel


class CustomConfig(BaseModel):
    param1: str
    param2: Optional[int] = None
    param3: list[str] = []
```

This API reference provides a comprehensive overview of the core AmritaCore interfaces, classes, and decorators. Each component is designed to work together to provide a flexible and powerful framework for building AI agents.
