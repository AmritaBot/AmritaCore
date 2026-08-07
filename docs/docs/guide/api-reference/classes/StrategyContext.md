# StrategyContext

The StrategyContext class provides the execution context for agent strategies.

This dataclass contains all the necessary information that an agent strategy needs to execute its workflow, including the user input, message context, and DI (Dependency Injection) resource fields.

> **v0.12.6**: DI resource fields (`preset`, `config`, `tools_manager`, `io_stream`, `train_content`, `stream_id`, `resp_extra_usage`) are now available directly on `StrategyContext`. Strategies should prefer these fields over reaching through `chat_object`. `chat_object` remains the core lifecycle-manager handle for the conversation — it is not deprecated.

## Properties

### Core Fields

- `user_input` (USER_INPUT): The input from the user
- `original_context` (SendMessageWrap): The original message context containing system message, memory, and user query

### DI Resource Fields (preferred path since v0.12.6)

- `preset` ([ModelPreset](ModelPreset.md) \| None): Model preset for the chat (default: `None`)
- `config` ([AmritaConfig](AmritaConfig.md) \| None): Configuration settings (default: `None`)
- `tools_manager` ([ToolsManager](ToolsManager.md) \| None): Manager for available tools (default: `None`)
- `io_stream` (SuspendObjectStream \| None): Streaming I/O interface for yielding responses (default: `None`)
- `train_content` (str \| None): System/training prompt content string (default: `None`)
- `stream_id` (str \| None): Unique stream identifier (default: `None`)
- `resp_extra_usage` ([UniResponseUsage](UniResponseUsage.md) \| None): Accumulator for response usage statistics (default: `None`)

### Core Reference Field

- `chat_object` ([ChatObject](ChatObject.md) \| None): The **core lifecycle-manager handle** for the current conversation — ChatObject is the basic unit of a dialogue. Resources can be reached through it when not injected directly. (default: `None` in new-style DI workflows)

## Constructor Parameters

- `user_input` (USER_INPUT): Input from the user
- `original_context` (SendMessageWrap): Original message context
- `chat_object` ([ChatObject](ChatObject.md) \| None, optional): The core lifecycle-manager handle for the current conversation. Resources fall back to it when not injected. (default: `None`)
- `preset` ([ModelPreset](ModelPreset.md) \| None, optional): Model preset (default: `None`)
- `config` ([AmritaConfig](AmritaConfig.md) \| None, optional): Configuration (default: `None`)
- `tools_manager` ([ToolsManager](ToolsManager.md) \| None, optional): Tools manager (default: `None`)
- `io_stream` (SuspendObjectStream \| None, optional): I/O stream (default: `None`)
- `train_content` (str \| None, optional): Training content (default: `None`)
- `stream_id` (str \| None, optional): Stream ID (default: `None`)
- `resp_extra_usage` ([UniResponseUsage](UniResponseUsage.md) \| None, optional): Extra usage accumulator (default: `None`)

## Methods

### get_original_context()

Get the original message context.

**Returns**: [SendMessageWrap](SendMessageWrap.md) - The original message context

### get_user_input()

Get the user input.

**Returns**: USER_INPUT - The user input

## Usage Example

### New-style (recommended since v0.12.6)

```python
from amrita_core.agent.context import StrategyContext

# DI resources are injected directly — no chat_object needed
ctx = StrategyContext(
    user_input="What can you do?",
    original_context=message_context,
    preset=model_preset,
    config=amrita_config,
    tools_manager=tools_mgr,
    io_stream=stream,
    train_content="You are a helpful assistant.",
    stream_id="session_abc123",
    resp_extra_usage=usage_tracker,
)

# Strategies access DI fields via _StrategyBase convenience properties:
#   self.preset, self.config, self.io_stream, etc.
# (see agent-strategy docs for details)

user_msg = ctx.get_user_input()
message_context = ctx.get_original_context()
```

### Legacy (still supported)

```python
from amrita_core.agent.context import StrategyContext

# chat_object is the lifecycle-manager handle; resources fall back to it
# when DI fields are not injected
ctx = StrategyContext(
    user_input="What can you do?",
    original_context=message_context,
    chat_object=chat_obj,
)

user_msg = ctx.get_user_input()
message_context = ctx.get_original_context()
```
