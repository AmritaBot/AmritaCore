# Streaming and Callbacks

AmritaCore streams all responses by default. In this tutorial you will consume the stream directly and switch to a callback-based style.

## 1. Stream the Response

Every [ChatObject](../api-reference/classes/ChatObject.md) exposes `io_stream`, whose `get_response_generator()` yields response chunks as they arrive:

```python
import asyncio

from amrita_core import create_agent, minimal_init


async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
        train="You are a helpful assistant.",
    )

    chat = agent.get_chatobject("Write a haiku about the sea.")
    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            print(message if isinstance(message, str) else message.get_content(), end="")
        await chat  # Wait for the task to finish — exiting would cancel it
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
```

Each yielded item is either a plain `str` chunk or a typed content object — `message.get_content()` returns its text. Exiting the `async with` block cancels the internal task, so always `await chat` inside the block.

## 2. Callback-Based Consumption

If you prefer, register a callback that is invoked for every chunk. Use `set_callback_func()` on the stream, then `begin()` runs the conversation and drives the callback:

```python
async def response_callback(chunk) -> None:
    print(chunk if isinstance(chunk, str) else chunk.get_content(), end="")


async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
        train="You are a helpful assistant.",
    )

    chat = agent.get_chatobject("Tell me a fun fact about space.")
    chat.io_stream.set_callback_func(response_callback)
    chat.begin()
    await chat  # begin() only starts the task; await it to completion
    print("\n")
```

## 3. Full Response with `full_response()`

To collect the complete response at once (no streaming), use `full_response()` after `begin()`:

```python
async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
    )

    chat = agent.get_chatobject("What is the capital of France?")
    chat.begin()
    response = await chat.full_response()
    print(response)
```

`full_response()` is a one-time consumer — use it **instead of** `get_response_generator()`, never both.

## What Just Happened

- `io_stream.get_response_generator()` is an async generator that emits chunks in real time
- `set_callback_func()` switches to push-style consumption — the callback fires per chunk while `begin()` runs
- `full_response()` gives you the assembled final response after execution

## Next Steps

- [Intercept the pipeline with events](event-hooks.md)
- [Manage memory and sessions](memory.md)
- Deep dive: [SuspendObjectStream](https://sense.amritabot.com) in the `amrita-sense` package
