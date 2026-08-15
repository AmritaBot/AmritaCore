# Basic Example

A slightly larger example that shows the three things you will use every day:
**streaming**, **tools**, and **sessions**.

> **What you will see**: the agent calling your `calculate` tool in the first
> turn, then remembering the result in the second turn (same `session_id`).
> If you are new to tools or sessions, Tutorials 2 and 5 explain them in depth.

```python
import asyncio
import os

from amrita_core import create_agent, minimal_init, on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

# 1. Register a tool at module load time.
CALC_DEFINITION = FunctionDefinitionSchema(
    name="calculate",
    description="Perform a simple arithmetic calculation",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "expr": FunctionPropertySchema(
                type="string", description="Arithmetic expression, e.g. '17*3'"
            ),
        },
        required=["expr"],
    ),
)


@on_tools(CALC_DEFINITION)
async def calculate(data: dict[str, str]) -> str:
    expr = data["expr"]
    try:
        return f"{expr} = {eval(expr)}"
    except Exception as e:  # noqa: S307
        return f"Error: {e!s}"


async def main() -> None:
    await minimal_init()
    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key=os.environ["OPENAI_API_KEY"],
        model="gpt-4o-mini",
    )

    # 2. A session keeps memory across turns.
    chat = agent.get_chatobject(
        "What is 17*3? Use the calculate tool.",
        session_id="demo-session",
    )
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            print(msg, end="", flush=True)

    # 3. Same session → the agent remembers the previous turn.
    chat2 = agent.get_chatobject(
        "Double the number you just computed.",
        session_id="demo-session",
    )
    async with chat2.begin():
        async for msg in chat2.io_stream.get_response_generator():
            print(msg, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
```

## Key Concepts Introduced

- **`@on_tools(schema)`**: registers a tool with a JSON Schema — the LLM sees the
  schema, calls the function with validated arguments.
- **`session_id`**: scopes memory. Two `ChatObject` instances with the same
  `session_id` share history; different ids are isolated.
- **Streaming**: `get_response_generator()` yields every chunk; the workflow
  also emits structured `MessageWithMetadata` objects (tool calls; `step`
  boundaries once the Step-loop workflow is active) — see
  [Streaming & Metadata](../tutorials/streaming.md).

## Next

Follow the [Tutorials](../tutorials/index.md) — they build up systematically:
first agent → tools → streaming → hooks → memory.
