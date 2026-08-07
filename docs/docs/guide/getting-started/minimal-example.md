# Minimal Example

The shortest complete AmritaCore program. Copy, paste, run.

> **What you will see**: the agent's reply streaming out token by token. The
> three lines before the loop (`minimal_init`, `create_agent`,
> `get_chatobject`) are the entire setup — everything else is AmritaCore doing
> the work.

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
    chat = agent.get_chatobject("Hello! Who are you?")
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            print(msg, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
```

## What Just Happened

| Line                         | What it does                                                         |
| ---------------------------- | -------------------------------------------------------------------- |
| `minimal_init()`             | Initializes the global config (required once per process)            |
| `create_agent(...)`          | Builds an `Agent` factory with an LLM adapter bound to your endpoint |
| `agent.get_chatobject(text)` | Creates a `ChatObject` — the basic unit of a dialogue                |
| `chat.begin()`               | Runs the workflow; the agent answers inside this context             |
| `get_response_generator()`   | Streams the response token by token                                  |

## Notes

- `api_key` can be omitted if you use `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` env vars with the matching `base_url`.
- For DeepSeek or other OpenAI-compatible providers, just change `base_url` and `model`.
- Anthropic? Use `protocol="anthropic"` — see [Adapters](../extensions-integration/adapters.md).

## Next

[Basic Example](basic-example.md) — add streaming metadata, tools and sessions.
