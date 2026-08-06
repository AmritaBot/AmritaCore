# 1. Create Your First Agent

## Goal of This Chapter

Run a real conversation with an LLM. By the end you will be able to:

- Initialize AmritaCore and create an agent
- Understand what a `ChatObject` is and why it wraps the conversation
- See the built-in step strategy at work (without configuring anything)

## Concepts at a Glance (introduced only when needed)

- **Agent**: a factory that binds your LLM endpoint. You ask it for
  conversations (`get_chatobject`).
- **`ChatObject`**: one dialogue. It owns the stream, the session state and the
  workflow that runs the conversation.
- **Strategy**: the "driver" that decides how the agent acts (call tools, stop,
  answer). AmritaCore ships a step-driven ReAct strategy as the default.

## 1. Initialize AmritaCore

Every process needs the config initialized once:

```python
import asyncio
import os

from amrita_core import create_agent, minimal_init


async def main() -> None:
    await minimal_init()
    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key=os.environ["OPENAI_API_KEY"],
        model="gpt-4o-mini",
    )
```

`create_agent()` returns an `Agent` object — the factory for conversations.

## 2. ChatObject — the Unit of Dialogue

A conversation is a `ChatObject`. It owns the workflow, the stream, and the
session state:

```python
    chat = agent.get_chatobject("What is the capital of France?")
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            print(msg, end="", flush=True)
```

- `get_chatobject(text)` creates one conversation
- `chat.begin()` runs the workflow (streaming is built-in)
- `chat.io_stream.get_response_generator()` yields response chunks

## 3. The Built-in ReAct Strategy

By default, `ChatObject` runs the **step-driven ReAct strategy**: the agent may
call tools, and the framework drives it through a Step loop (decompose → execute
→ summarize). You don't need to do anything — a plain question produces a plain
answer; a multi-step task gets decomposed automatically.

You can watch the steps as structured metadata:

```python
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            if isinstance(msg, str):
                print(msg, end="", flush=True)
            else:
                print(f"\n[meta:{msg.metadata}] {msg.content}", flush=True)
```

You will see `step` events (`intro` / `leave` / `decompose`) interleaved with
the text — see [Streaming and Callbacks](streaming.md) for the full list.

## What Just Happened

- `minimal_init()` + `create_agent()` → ready to talk
- `ChatObject` = one dialogue: workflow + stream + session
- The built-in strategy is already active — no configuration needed

## Next

[2. Add Tools to Your Agent](tools.md) — give your agent something to do.
