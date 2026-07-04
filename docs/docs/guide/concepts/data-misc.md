# Data Misc

This page covers miscellaneous data types that support the core data containers and backend system.

## ModelConfig — Model Configuration

[`ModelConfig`](../api-reference/classes/ModelConfig.md) holds tuning parameters for LLM requests:

```python
from amrita_core.types import ModelConfig

model_config = ModelConfig(
    temperature=0.7,
    top_p=0.9,
    top_k=50,
    stream=True,
    multimodal=False,
    cot_model=False,
)
```

| Field         | Default | Description                          |
| ------------- | ------- | ------------------------------------ |
| `temperature` | `0.6`   | Sampling temperature                 |
| `top_p`       | `0.8`   | Nucleus sampling                     |
| `top_k`       | `50`    | Top-K sampling                       |
| `stream`      | `False` | Enable streaming                     |
| `multimodal`  | `False` | Enable multimodal input              |
| `cot_model`   | `False` | Strip `\<think\>` tags from response |

## ModelPreset — Model Preset

[`ModelPreset`](../api-reference/classes/ModelPreset.md) bundles model identity, endpoint credentials, protocol, and configuration:

```python
from amrita_core.types import ModelPreset, ModelConfig

preset = ModelPreset(
    model="gpt-4",
    name="my-gpt4",
    base_url="https://api.openai.com/v1",
    api_key="sk-xxx",
    protocol="openai",                    # Adapter protocol
    config=ModelConfig(temperature=0.7),
    thinking_config=ThinkingConfig(
        thinking_type="enabled",
        thinking_effort="high",
    ),
)
```

`ModelPreset` also provides `load(path)` / `save(path)` for JSON serialization.

## ThinkingConfig — Reasoning Configuration

[`ThinkingConfig`](../api-reference/classes/ThinkingConfig.md) controls reasoning/thinking features for models that support them:

```python
from amrita_core.types import ThinkingConfig

tc = ThinkingConfig(
    thinking_type="enabled",          # "enabled" | "disabled" | None
    enable_thinking=True,
    thinking_effort="high",           # "minimal" | "low" | "medium" | "high" | "xhigh" | "max"
    content_mode="optional",          # "never" | "by-tool" | "optional"
)
```

## PresetManager — Preset Management

[`PresetManager`](../api-reference/classes/PresetManager.md) provides centralized management of `ModelPreset` instances. It is a **singleton** — all sessions share the same instance:

```python
from amrita_core.preset import PresetManager
from amrita_core.types import ModelPreset, ModelConfig

manager = PresetManager()

manager.add_preset(ModelPreset(
    model="gpt-3.5-turbo", name="fast",
    api_key="sk-xxx", config=ModelConfig(stream=True)
))
manager.add_preset(ModelPreset(
    model="gpt-4", name="smart",
    api_key="sk-xxx"
))

manager.set_default_preset("fast")
preset = manager.get_preset("smart")
default = manager.get_default_preset()  # auto-fallback
```

**Automatic fallback**: If no default is set, `get_default_preset()` picks a random registered preset. Use `test_presets()` for async connectivity checks.

## UniResponse / UniResponseUsage — Unified Response

[`UniResponse`](../api-reference/classes/UniResponse.md) is the unified response format returned by all adapters:

```python
from amrita_core.types import UniResponse, UniResponseUsage

response = UniResponse(
    content="Hello! How can I help?",
    role="assistant",
    tool_calls=None,
    reasoning_content=None,
    usage=UniResponseUsage(
        prompt_tokens=50,
        completion_tokens=20,
        total_tokens=70,
    ),
)
```

All adapter `call_api` / `call_tools` methods yield `UniResponse` instances, providing a vendor-neutral interface.

## SendMessageWrap — Message Wrapper

[`SendMessageWrap`](../api-reference/classes/SendMessageWrap.md) wraps the message list sent to the LLM. It separates the system message (`train`), memory, user query, and any appended end-messages:

```python
from amrita_core.types import SendMessageWrap

wrap = SendMessageWrap.validate_messages([
    Message(role="system", content="You are helpful."),
    Message(role="user", content="What is 2+2?"),
])

# Iterate over all messages in order:
for msg in wrap:
    print(msg.role, msg.content)

# Unwrap to a flat list (optionally excluding system)
flat = wrap.unwrap(exclude_system=False)

# Append extra messages after the user query
wrap.append(Message(role="assistant", content="4"))
```

`SendMessageWrap` is used internally by `ChatObject`'s `context_wrap` and `StrategyContext.original_context`.

## EmbeddingChunk — Embedding Result

[`EmbeddingChunk`](../api-reference/classes/EmbeddingChunk.md) represents a single embedding vector:

```python
from amrita_core.types import EmbeddingChunk

chunk = EmbeddingChunk(
    embedding=[0.1, 0.2, 0.3, ...],
    index=0
)
```

Returned by embedding adapters via `call_embed()`. Compatible with OpenAI's embedding response format.

## register_content — Custom Content Types

New content types can be registered dynamically:

```python
from amrita_core.types import Content, register_content
from typing import Literal

class MyCustomContent(Content[Literal["my_type"]]):
    type: Literal["my_type"] = "my_type"
    payload: str

register_content(MyCustomContent)
```

After registration, `Message` validation automatically deserializes `{"type": "my_type", ...}` dicts into `MyCustomContent` instances.

## Dirty Tracking

`DirtyAwareModel` / `DirtyAwareBaseModel` (in `amrita_core.dirty`) provide automatic mutation tracking for Pydantic models. `MemoryModel` inherits from `DirtyAwareBaseModel`, so:

```python
memory = MemoryModel()
memory.messages.append(msg)     # auto-marked dirty
print(memory.is_dirty())        # True
print(memory.get_dirty_vars())  # {"messages"}
memory.clean()                  # reset
```

This is designed for ORM-style workflows where you only want to persist changed fields.
