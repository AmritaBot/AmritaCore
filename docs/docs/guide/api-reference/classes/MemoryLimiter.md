# MemoryLimiter

`MemoryLimiter` is an async context processor that manages conversation context memory length and token count limits, ensuring the chat context remains within predefined constraints by summarizing context and removing messages.

## Overview

When the conversation grows too long, `MemoryLimiter` automatically:

1. **Limits message count** — Drops oldest messages when exceeding `memory_length_limit`
2. **Limits token usage** — Drops messages until total tokens are within `session_tokens_windows`
3. **Summarizes context** — Optionally calls LLM to generate an abstract of dropped messages (when `enable_memory_abstract` is `True`)

On exception, the context manager automatically **rolls back** messages to their original state.

## Usage

```python
from amrita_core.chatmanager import MemoryLimiter
from amrita_core.types import MemoryModel, Message

memory = MemoryModel(messages=[])
train = Message(role="system", content="You are a helpful assistant")

async with MemoryLimiter(memory, train) as limiter:
    await limiter.run_enforce()
```

## Constructor

```python
MemoryLimiter(
    memory: Memory,
    train: dict[str, str] | Message[str],
    config: AmritaConfig | None = None,
    abstract_instruction: str | None = None,
)
```

**Parameters:**

- `memory` (`Memory`): The memory model (`MemoryModel`) to process
- `train` (`dict[str, str] | Message[str]`): Training data (system prompts)
- `config` (`AmritaConfig | None`, optional): Configuration. Defaults to global config.
- `abstract_instruction` (`str | None`, optional): Custom instruction for context summarization

## Attributes

| Attribute | Type                       | Description                                       |
| --------- | -------------------------- | ------------------------------------------------- |
| `config`  | `AmritaConfig`             | Current configuration                             |
| `usage`   | `UniResponseUsage \| None` | Token usage from summarization (initially `None`) |
| `memory`  | `Memory`                   | The memory model being processed                  |

## Class Methods

### `set_abstract_instruction(instruction: str)`

Override the default abstract instruction used for context summarization.

**Parameters:**

- `instruction` (`str`): New abstract instruction text

**Raises:**

- `TypeError`: If instruction is not a string
- `ValueError`: If instruction is empty

---

### `get_abstract_instruction() -> str`

Get the current abstract instruction text.

**Returns:** `str`

---

### `reset_abstract_instruction()`

Reset the abstract instruction to the framework default.

## Instance Methods

### `async run_enforce()`

Execute memory limitation processing. Must be called within the async context manager (`async with` block).

**Raises:**

- `RuntimeError`: If called outside the context manager

## Example with Custom Configuration

```python
from amrita_core.config import AmritaConfig, LLMConfig
from amrita_core.chatmanager import MemoryLimiter

config = AmritaConfig(
    llm=LLMConfig(
        memory_length_limit=50,
        session_tokens_windows=4096,
        enable_memory_abstract=True,
        memory_abstract_proportion=0.15,
    )
)

async with MemoryLimiter(memory, train, config=config) as limiter:
    await limiter.run_enforce()
    if limiter.usage:
        print(f"Summarization usage: {limiter.usage}")
```
