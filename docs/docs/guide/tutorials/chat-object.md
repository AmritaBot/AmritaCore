# 1. Create Your First Agent

## Goal of This Chapter

Run a real conversation with an LLM. By the end you will be able to:

- Initialize AmritaCore and create an agent
- Understand what a `ChatObject` is and why it wraps the conversation
- See both workflows: the default simple chat and the explicit step loop

## Concepts at a Glance (introduced only when needed)

- **Agent**: a factory that binds your LLM endpoint. You ask it for
  conversations (`get_chatobject`).
- **`ChatObject`**: one dialogue. It owns the stream, the session state and the
  workflow that runs the conversation.
- **Strategy**: the "driver" that decides how the agent acts (call tools, stop,
  answer). AmritaCore ships a step-driven ReAct strategy — you opt into it by
  passing the step-loop workflow explicitly.

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

## 3. Two Workflows: Simple Chat vs the Step Loop

`get_chatobject()` without any extra argument runs the **simple chat
workflow**: one LLM call, one answer. It is the fastest way to talk — and it
does not decompose tasks or run a Step loop.

```python
    chat = agent.get_chatobject("What is the capital of France?")
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            print(msg, end="", flush=True)
```

To run the built-in **step-driven ReAct strategy** — where the LLM decomposes
the task into a plan, the framework walks it Step by Step, and the agent can
call tools and even revise its own plan — you must **explicitly pass the
step-loop workflow**:

```python
from amrita_core.chatmanager import _step_workflow_rendered

    chat = agent.get_chatobject(
        "What is the capital of France?",
        workflow=_step_workflow_rendered,
    )
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            print(msg, end="", flush=True)
```

You can watch the steps as structured metadata:

```python
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            if isinstance(msg, str):
                print(msg, end="", flush=True)
            else:
                print(f"\n[meta:{msg.metadata}] {msg.content}", flush=True)
```

You will see `step` events (`decompose` / `intro` / `leave`) interleaved with
the text — see [Streaming and Callbacks](streaming.md) for the full list.

> **Why explicit?** The simple workflow is the default so that a bare
> `get_chatobject()` always "just works" for plain conversations. The Step
> loop trades simplicity for plan-driven autonomy — pass
> `workflow=_step_workflow_rendered` whenever you want that.

## What Just Happened

- `minimal_init()` + `create_agent()` → ready to talk
- `ChatObject` = one dialogue: workflow + stream + session
- Default workflow = simple chat (one call, one answer)
- Step loop requires `workflow=_step_workflow_rendered` explicitly

## Next

[2. Add Tools to Your Agent](tools.md) — give your agent something to do.
