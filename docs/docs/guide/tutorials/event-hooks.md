# Events and Hooks

AmritaCore exposes an event system that lets you intercept the processing pipeline. In this tutorial you will attach hooks that run before and after the LLM completes.

## 1. React to Completions with `@on_completion`

[`@on_completion`](../api-reference/index.md#on_completion) registers a handler that runs after the model finishes generating. The handler receives a [CompletionEvent](../api-reference/classes/CompletionEvent.md):

```python
import asyncio

from amrita_core import create_agent, minimal_init, on_completion
from amrita_core.hook.event import CompletionEvent


@on_completion().handle()
async def log_completion(event: CompletionEvent) -> None:
    print(f"[completion] model said: {event.get_model_response()}")


async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
        train="You are a helpful assistant.",
    )

    chat = agent.get_chatobject("What is 2 + 2?")
    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            print(message if isinstance(message, str) else message.get_content(), end="")
        await chat  # Wait for the task to finish — exiting would cancel it
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
```

The `CompletionEvent` fires once per completion round — including tool-call rounds within a single conversation.

## 2. Pre-Completion Hooks with `@on_precompletion`

[`@on_precompletion`](../api-reference/index.md#on_precompletion) runs **before** the request is sent to the LLM, letting you inspect or modify the outgoing messages. The handler receives a [PreCompletionEvent](../api-reference/classes/PreCompletionEvent.md):

```python
from amrita_core import on_precompletion
from amrita_core.hook.event import PreCompletionEvent


@on_precompletion().handle()
async def log_request(event: PreCompletionEvent) -> None:
    print(f"[request] sending {len(event.messages)} messages to the model")
```

## 3. Custom Events with `@on_event`

For application-specific events, use [`@on_event`](../api-reference/index.md#on_event) with an event type of your own:

```python
from amrita_core import on_event


@on_event("my_app:user_login").handle()
async def handle_login(event) -> None:
    print("user logged in:", event)
```

## 4. What Just Happened

- `@on_completion` / `@on_precompletion` wrap the generic [`on_event`](../api-reference/index.md#on_event) with the built-in [EventTypeEnum](../api-reference/index.md#events--hooks) (`COMPLETION` / `BEFORE_COMPLETION`)
- Handlers are dispatched by the `MatcherManager` (provided by the `amrita-sense` package) with optional `priority` and `block` behavior
- See [Core Concepts: Event System](../concepts/event.md) for the full event catalog and fallback handling

## Next Steps

- [Manage memory and sessions](memory.md)
- Deep dive: [Core Concepts: Event System](../concepts/event.md)
