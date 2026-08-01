# Memory and Sessions

Every conversation in AmritaCore belongs to a **session**, identified by a `session_id`. In this tutorial you will reuse the same session across multiple turns so the agent remembers context, and enable memory summarization for long conversations.

## 1. Session IDs

When you create an agent, a random `session_id` is generated for you. Pass your own via `create_agent(..., session_id=...)` to control which session the agent talks to:

```python
import asyncio

from amrita_core import create_agent, minimal_init


async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
        session_id="my-chat-session",  # Reuse this ID across turns
        train="You are a helpful assistant.",
    )

    # Turn 1: the agent learns something
    chat = agent.get_chatobject("My name is Alice.")
    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            print(message if isinstance(message, str) else message.get_content(), end="")
        await chat  # Wait for the task to finish — exiting would cancel it
    print("\n")

    # Turn 2: same agent, same session — the agent still knows the name
    chat2 = agent.get_chatobject("What is my name?")
    async with chat2.begin():
        async for message in chat2.io_stream.get_response_generator():
            print(message if isinstance(message, str) else message.get_content(), end="")
        await chat2  # Wait for the task to finish — exiting would cancel it
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
```

The session's memory is loaded and committed by the [data backend](../concepts/data-backend.md) — by default `LegacyBackend`, which stores memory in in-process global containers. Different `session_id`s get isolated memory.

## 2. Multiple Agents, Same Session

Because `session_id` lives on the runtime, two agents created with the same `session_id` share conversation history:

```python
agent_a = create_agent(base_url=..., api_key=..., session_id="shared-session")
agent_b = create_agent(base_url=..., api_key=..., session_id="shared-session")
```

This is useful for splitting responsibilities (e.g. different tools or prompts) while keeping one conversation thread.

## 3. Memory Summarization

Long conversations grow unbounded. Enable **memory abstraction** so AmritaCore automatically summarizes older messages when the context gets long:

```python
from amrita_core import create_agent
from amrita_core.config import LLMConfig

agent = create_agent(
    base_url="https://api.openai.com/v1",
    api_key="sk-...",
    model="gpt-4o-mini",
    model_config={"temperature": 0.7},
)

# Enable summarization on the global config
from amrita_core.config import get_config, set_config

config = get_config()
config.llm.enable_memory_abstract = True
config.llm.memory_abstract_proportion = 0.15  # summarize ~15% of history at the limit
set_config(config)
```

You can also constrain how much history is kept with `memory_length_limit` (maximum number of messages in the memory context).

## 4. What Just Happened

- `session_id` scopes conversation memory; reusing it continues the conversation
- `get_chatobject()` creates a `ChatObject` that fetches memory for `session_id` from the backend and commits it back after the run
- `LLMConfig` memory settings (`enable_memory_abstract`, `memory_abstract_proportion`, `memory_length_limit`) control automatic summarization and context trimming

## Next Steps

- Deep dive: [Data Backend](../concepts/data-backend.md) and [Data Containers](../concepts/data-containers.md)
- [Implement a specific feature](../how-to/function-implementation.md)
- [Explore advanced topics](../advanced/index.md)
