# ChatObject — Conversation Objects

[ChatObject](../api-reference/classes/ChatObject.md) is the core class for managing individual conversations. Every interaction with an agent — a chat, a tool call, a multi-turn exchange — happens through a `ChatObject` instance.

While the [tutorials](../tutorials/index.md) show the recommended way to create agents with the `create_agent()` factory, this page explains what `ChatObject` is and how the pieces fit together.

## What is a ChatObject?

A `ChatObject` bundles everything a single conversation needs:

- **Input**: `train` (system message) and `user_input` (user query)
- **State**: a `session_id` that ties conversation memory to a session
- **Abilities**: tools, MCP clients, and presets loaded from the [data backend](data-backend.md)
- **I/O**: an `io_stream` that yields responses, with optional streaming callbacks

```python
import asyncio
from amrita_core import ChatObject
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend

backend = BackendSlots(ability=LegacyBackend(), memory=LegacyBackend())

chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Hello!",
    context=None,
    session_id="session_123",
    backend=backend,
)

async def msg_getter(chatobj: ChatObject) -> None:
    async for message in chatobj.io_stream.get_response_generator():
        print(message if isinstance(message, str) else message.get_content(), end="")
    print("\n")

async with chat.begin():
    await msg_getter(chat)
    await chat  # Wait for the task to finish before exiting
```

## PresetManager — Preset Manager

[PresetManager](../api-reference/classes/PresetManager.md) manages model presets:

```python
from amrita_core.preset import PresetManager, ModelPreset

preset_manager = PresetManager()

# Add preset
preset = ModelPreset(...)
preset_manager.add_preset(preset)
preset_manager.set_default_preset(preset.name)

# Get available presets
presets = preset_manager.get_presets()
```

## Stream Processing Design

AmritaCore uses streaming for all responses to provide real-time feedback:

```python
# Responses are returned as asynchronous generators
async for chunk in chat.io_stream.get_response_generator():
    # Process each chunk in real-time
    print(chunk, end="")
```

## Callback-based Responses

AmritaCore supports callback-based responses:

```python
async def callback(chunk):
    print(chunk, end="")

chat.io_stream.set_callback_func(callback)
chat.begin()
await chat
```

## Memory Summarization Mechanism

The memory summarization mechanism automatically compresses conversation history to manage token usage:

```python
# Configured via LLMConfig
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # Summarize a portion of the conversation when reaching the token limit.
)
```

## Suspend and Resume

AmritaCore provides a built-in **suspend/resume mechanism** that allows you to pause and resume the execution flow of a `ChatObject` at any point during processing. This feature enables interactive applications where user intervention or external events may require temporary suspension of the agent's workflow.

Key features include:

- Non-blocking suspension without blocking the main event loop
- Fine-grained control over execution flow
- Timeout support to prevent indefinite waiting
- Seamless integration with all agent strategies

For detailed usage examples and advanced scenarios, see the [Suspend and Resume Mechanism](../advanced/suspend.md) documentation.
