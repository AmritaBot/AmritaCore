# Data Containers

AmritaCore provides a set of typed data containers that form the backbone of conversation state, message passing, and context management. These containers are defined in the `amrita_core.types` package and integrate with the [data backend](data-backend.md) for persistence.

## Message Type

The [`Message`](../api-reference/classes/Message.md) class represents a single message in a conversation. It is a generic Pydantic model parameterized by content type:

```python
from amrita_core.types import Message

# Create a system message
system_msg = Message(content="You are a helpful assistant.", role="system")

# Create a user message
user_msg = Message(content="Hello, how are you?", role="user")

# Create an assistant message with multimodal content
from amrita_core.types import TextContent, ImageContent
multi_msg = Message(role="user", content=[
    TextContent(text="What's in this image?"),
    ImageContent(image_url=...)
])
```

**Key fields**:

- `role`: `"user"`, `"assistant"`, or `"system"`
- `content`: string, list of `Content` subclasses, or `None`
- `tool_calls`: optional list of [`ToolCall`](../api-reference/classes/ToolCall.md)
- `reasoning_content` / `reasoning_signature`: reasoning/thinking metadata (assistant only)

`Message` uses `model_config = ConfigDict(extra="allow")` so additional fields pass through transparently.

## Content Types

AmritaCore supports three built-in content types registered in the `CT_MAP` registry:

### TextContent

```python
from amrita_core.types import TextContent

content = TextContent(text="This is the actual message text")
```

### ImageContent

```python
from amrita_core.types import ImageContent, ImageUrl

content = ImageContent(image_url=ImageUrl(
    url="https://example.com/image.png",
    detail="auto"
))
```

### FileContent

```python
from amrita_core.types import FileContent, File

content = FileContent(file=File(
    file_id="file-abc123",
    # or inline: filename="doc.pdf", file_data="...", type="application/pdf"
))
```

New content types can be registered via `register_content()` — see [Data Misc](data-misc.md).

## MemoryModel — Conversation Memory

[`MemoryModel`](../api-reference/classes/MemoryModel.md) stores conversation history and context. It inherits from `DirtyAwareBaseModel`, which tracks field modifications (the **dirty-mark** pattern):

```python
from amrita_core.types import MemoryModel

memory = MemoryModel()

# Add messages to memory
memory.messages.append(system_msg)
memory.messages.append(user_msg)
memory.messages.append(assistant_msg)

# Check what changed
print(memory.is_dirty("messages"))  # True
print(memory.get_dirty_vars())       # {"messages"}
memory.clean()                       # Reset dirty tracking
```

**Key fields**:

- `messages`: `list[Message | ToolResult]` — conversation history
- `abstract`: `str` — auto-generated summary (populated by `MemoryLimiter`)
- `time`: `float` — timestamp

The **dirty-mark** pattern is provided by `DirtyAwareBaseModel` / `DirtyAwareModel`. Child containers (`DirtyList`, `DirtyDict`, `DirtySet`) automatically propagate mutations up to the parent model, enabling ORM-like change tracking.

## ToolResult

[`ToolResult`](../api-reference/classes/ToolResult.md) represents the output of a tool invocation:

```python
from amrita_core.types import ToolResult

result = ToolResult(
    role="tool",
    name="calculator",
    content="42",
    tool_call_id="call_abc123"
)
```

`ToolResult` can appear in `memory.messages` alongside `Message` objects — both are valid `CONTENT_LIST_TYPE_ITEM`s.

```python
CONTENT_LIST_TYPE_ITEM = Message | ToolResult
CONTENT_LIST_TYPE = list[CONTENT_LIST_TYPE_ITEM]
```

## StateContext — Runtime State (deprecated since v0.12.0)

> **Marked `@deprecated` in v0.12.0**, will be removed in v0.13.x. This dataclass carried too many roles and has been split into separate DI context objects.

[`StateContext`](../api-reference/classes/StateContext.md) is the runtime state container passed to every `ChatObject`. It is a **dataclass** (not a Pydantic model):

```python
from amrita_core.contexts import StateContext, AbilityContext

state = StateContext(
    session_id="session_abc",
    memory=MemoryModel(),
    ability=AbilityContext()
)
```

**Fields**:

- `session_id`: `str` — session identifier
- `memory`: `MemoryModel` — conversation memory
- `ability`: `AbilityContext` — tools, presets, MCP clients
- `extra`: `dict[str, Any]` — extension point

`StateContext` is **lazily initialized** by `ChatObject` via the [data backend](data-backend.md). You normally don't create it yourself — the backend does.

### Alternative: DI Context Objects

Since v0.12.0, ChatObject internally uses the following DI context objects to replace `StateContext`'s responsibilities:

| DI Context                                                                         | Purpose                           |
| ---------------------------------------------------------------------------------- | --------------------------------- |
| `_di_session` ([`SessionMetadata`](../api-reference/classes/SessionMetadata.md))   | Session identity and timing       |
| `_di_memory` ([`MemoryContext`](../api-reference/classes/MemoryContext.md))        | Runtime conversation memory       |
| `_di_ability` ([`AbilityState`](../api-reference/classes/AbilityState.md))         | Config, preset, backend slots     |
| `_di_input` ([`GeneralInput`](../api-reference/classes/GeneralInput.md))           | User input, template, Jinja2 vars |
| `_di_working` ([`WorkingState`](../api-reference/classes/WorkingState.md))         | Context message wrapper           |
| `_di_resp` ([`RespState`](../api-reference/classes/RespState.md))                  | LLM response and usage stats      |
| `_di_loop` ([`AgentLoopState`](../api-reference/classes/AgentLoopState.md))        | Agent loop state                  |
| `_di_opt` ([`DatabackendOptions`](../api-reference/classes/DatabackendOptions.md)) | Backend fetch/commit control      |
| `_di_agent` ([`StrategyPayload`](../api-reference/classes/StrategyPayload.md))     | Agent strategy reference          |

These DI objects are automatically injected into workflow nodes by `WorkflowInterpreter`'s dependency injection, no manual passing required.

## AbilityContext

[`AbilityContext`](../api-reference/classes/AbilityContext.md) groups the "abilities" available to a session:

```python
from amrita_core.contexts import AbilityContext

ability = AbilityContext(
    tools=ToolsManager(),       # defaults to global ToolsManager singleton
    presets=PresetManager(),    # defaults to global PresetManager singleton
    mcp=ClientManager(),        # defaults to global ClientManager singleton
    extra={}
)
```

When no arguments are provided, all fields default to the **global singleton** managers — this is the behavior of `LegacyBackend`.

## Manager Pattern — Multi\* vs Singleton Managers

AmritaCore uses a two-tier pattern for manager classes: a **`Multi*Manager`** base with instance-level state, and a **singleton subclass** that provides a global shared instance. The singleton is the default used by `AbilityContext` and `LegacyBackend`.

### ToolsManager / MultiToolsManager

[`MultiToolsManager`](../api-reference/classes/MultiToolsManager.md) is a tool registry that stores [`ToolData`](../api-reference/classes/ToolData.md) entries keyed by function name. Each `ToolData` bundles a schema (`ToolFunctionSchema`) with an async callable and an optional `enable_if()` predicate.

```python
from amrita_core.tools.manager import ToolsManager, MultiToolsManager

# Global singleton (used by default)
tm = ToolsManager()

# Or create an isolated instance
tm = MultiToolsManager()
```

**Key methods**:

| Method                                     | Description                                      |
| ------------------------------------------ | ------------------------------------------------ |
| `has_tool(name)`                           | Check if a tool is registered and enabled        |
| `get_tool(name)`                           | Get the full `ToolData` (respects `enable_if()`) |
| `get_tool_meta(name)`                      | Get just the `ToolFunctionSchema`                |
| `get_tool_func(name)`                      | Get the raw async callable                       |
| `get_tools()`                              | Get all enabled tools as `dict[str, ToolData]`   |
| `tools_meta()` / `tools_meta_dict()`       | Get all tool schemas for LLM requests            |
| `register_tool(tool)`                      | Register a `ToolData`                            |
| `remove_tool(name)`                        | Remove and undisable a tool                      |
| `enable_tool(name)` / `disable_tool(name)` | Runtime enable/disable toggle                    |

[`ToolsManager`](../api-reference/classes/ToolsManager.md) is the **singleton** subclass of `MultiToolsManager` — all sessions using `LegacyBackend` share the same global tool registry. Tools registered via `@simple_tool` / `@on_tools` land in this global instance.

### PresetManager / MultiPresetManager

[`MultiPresetManager`](../api-reference/classes/MultiPresetManager.md) manages a collection of [`ModelPreset`](data-misc.md#modelpreset-model-preset) instances:

```python
from amrita_core.preset import PresetManager, MultiPresetManager

# Global singleton
pm = PresetManager()

# Or an isolated instance
pm = MultiPresetManager()
```

**Key methods**:

| Method                     | Description                                                    |
| -------------------------- | -------------------------------------------------------------- |
| `add_preset(preset)`       | Register a `ModelPreset` (raises on duplicate name)            |
| `get_preset(name)`         | Lookup by name (raises `ValueError` if missing)                |
| `set_default_preset(name)` | Set the fallback preset                                        |
| `get_default_preset()`     | Returns the default, or a random registered preset if none set |
| `get_all_presets()`        | Returns `list[ModelPreset]`                                    |
| `test_presets()`           | Async generator yielding `PresetReport` for each preset        |

[`PresetManager`](../api-reference/classes/PresetManager.md) is the **singleton** subclass — all sessions share the same preset catalog by default.

### ClientManager / MultiClientManager (MCP)

[`MultiClientManager`](../api-reference/classes/MultiClientManager.md) manages a pool of [`MCPClient`](../api-reference/classes/MCPClient.md) instances, bridging external MCP servers into the tool system:

```python
from amrita_core.tools.mcp import ClientManager, MultiClientManager

# Global singleton
cm = ClientManager()

# Or an isolated instance
cm = MultiClientManager()
```

**Key methods**:

| Method                          | Description                                        |
| ------------------------------- | -------------------------------------------------- |
| `initialize_this(script)`       | Register and connect a single MCP server           |
| `initialize_all()`              | Connect all registered clients                     |
| `reinitialize_all()`            | Reconnect all clients (e.g. after config change)   |
| `unregister_client(script)`     | Disconnect and remove a server                     |
| `get_client_by_tool_name(name)` | Resolve which `MCPClient` owns a given tool        |
| `get_client_by_script(script)`  | Create (but not register) a standalone `MCPClient` |

When an MCP server is loaded, its tools are auto-registered into the bound `tools_manager`. Name collisions trigger automatic remapping (e.g. `search` → `referred_42_search`). See [MCP Server Integration](../extensions-integration/mcp-server-integration.md) for end-to-end examples.

[`ClientManager`](../api-reference/classes/ClientManager.md) is the **singleton** subclass. Each `MCPClient` wraps a single MCP server script and handles connection lifecycle (connect, TTL-based auto-close, tool discovery).

### Summary Table

| Manager                                | Manages               | Singleton       | Default in LegacyBackend |
| -------------------------------------- | --------------------- | --------------- | ------------------------ |
| `MultiToolsManager` / `ToolsManager`   | `ToolData` entries    | `ToolsManager`  | `AbilityContext.tools`   |
| `MultiPresetManager` / `PresetManager` | `ModelPreset` entries | `PresetManager` | `AbilityContext.presets` |
| `MultiClientManager` / `ClientManager` | `MCPClient` pool      | `ClientManager` | `AbilityContext.mcp`     |
