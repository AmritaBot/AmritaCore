# Create Your First Agent

In this tutorial you will create a minimal chat agent using the [`create_agent()`](../api-reference/index.md#create_agent) factory function.

## 1. Initialize AmritaCore

Before creating an agent, initialize the framework. [`minimal_init()`](../api-reference/index.md#minimal_init) applies the global configuration and, if MCP is enabled, loads the MCP clients. Tokenizers and adapters are already registered automatically when you `import amrita_core`:

```python
import asyncio

from amrita_core import minimal_init


async def main() -> None:
    await minimal_init()
```

## 2. Create the Agent

Call `create_agent()` with your LLM endpoint and API key. The factory automatically creates a temporary [ModelPreset](../api-reference/classes/ModelPreset.md) for you — no preset management needed:

```python
from amrita_core import create_agent

agent = create_agent(
    base_url="https://api.openai.com/v1",  # Your LLM API endpoint
    api_key="sk-...",                       # Your API key
    model="gpt-4o-mini",                    # Model identifier (default: "auto")
    train="You are a helpful assistant.",   # Optional system prompt
)
```

You can also pass model tuning parameters via `model_config` (as a dict or [ModelConfig](../api-reference/classes/ModelConfig.md) object):

```python
agent = create_agent(
    base_url="https://api.openai.com/v1",
    api_key="sk-...",
    model="gpt-4o-mini",
    model_config={
        "temperature": 0.7,
        "max_tokens": 1024,
    },
)
```

## 3. Send a Message

`create_agent()` returns an [AgentRuntime](../api-reference/classes/AgentRuntime.md). Call `agent.get_chatobject(user_input)` to create a [ChatObject](../api-reference/classes/ChatObject.md) bound to the agent's configuration, then run it with `async with chat.begin()`:

```python
async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
        train="You are a helpful assistant.",
    )

    chat = agent.get_chatobject("Hello! What can you do?")
    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            print(message if isinstance(message, str) else message.get_content(), end="")
        await chat  # Wait for the task to finish — exiting would cancel it
    print("\n")
```

> ⚠️ **Important**: exiting the `async with` block terminates the internal task instead of waiting for it. Always `await chat` inside the block to let the response complete.

## 4. Run It

```bash
python your_script.py
```

You should see the model's streaming reply printed in your terminal.

## What Just Happened

- `create_agent()` built a temporary `ModelPreset` from `base_url` / `api_key` / `model` and an [AgentRuntime](../api-reference/classes/AgentRuntime.md) around it
- `get_chatobject()` created a `ChatObject` wired to that preset, the agent's system prompt (`train`), and a fresh `session_id`
- `chat.begin()` executed the [ReAct agent strategy](../concepts/agent-strategy.md) (the default) and streamed the response through `io_stream`

## Next Steps

- [Add tools to your agent](tools.md) so it can call functions
- [Stream responses and use callbacks](streaming.md)
- Understand what happened under the hood in [Core Concepts](../concepts/index.md)
