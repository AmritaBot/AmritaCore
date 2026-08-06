# 2. Add Tools to Your Agent

## Goal of This Chapter

Let your agent call functions you wrote. By the end you will be able to:

- Expose a Python function to the model with `@simple_tool`
- Control the call contract precisely with `@on_tools`

## Concepts at a Glance (introduced only when needed)

- **Tool**: a function with a JSON Schema. The model never _executes_ your
  function — it only generates a call request; the framework validates the
  arguments, runs the function, and feeds the result back.

## 1. A Simple Tool with `@simple_tool`

The fastest way to expose a function to the agent — types and docstring are
turned into the JSON Schema automatically:

```python
from amrita_core import simple_tool

@simple_tool
def add(a: int, b: int) -> int:
    """Add two numbers

    Args:
        a (int): First number
        b (int): Second number

    Returns:
        int: Sum of a and b
    """
    return a + b
```

`@simple_tool` reads Google-style docstrings to build the schema. Supported
annotations include Pydantic models, `list[T]`, `Optional[T]` and scalars.

## 2. Use the Tool in Your Agent

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
    chat = agent.get_chatobject("What is 123 + 456? Use the add tool.")
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            print(msg, end="", flush=True)

asyncio.run(main())
```

The agent decides _when_ to call `add`; the framework validates the arguments
against the schema and feeds the result back.

## 3. Full Control with `@on_tools`

When you need precise control over the schema (validation constraints,
descriptions, enum values), define it manually:

```python
from amrita_core import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

WEATHER_DEFINITION = FunctionDefinitionSchema(
    name="get_weather",
    description="Get the current weather for a city",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "city": FunctionPropertySchema(
                type="string",
                description="City name, e.g. 'Paris'",
                minLength=1,
            ),
            "unit": FunctionPropertySchema(
                type="string",
                enum=["celsius", "fahrenheit"],
                description="Temperature unit",
            ),
        },
        required=["city"],
    ),
)

@on_tools(WEATHER_DEFINITION)
async def get_weather(data: dict[str, str]) -> str:
    city = data["city"]
    unit = data.get("unit", "celsius")
    return f"Weather in {city}: 22°{unit[0].upper()}"
```

The handler receives the validated arguments as a `dict` and **must return a
string** (it becomes the tool result the model sees).

For tools that need framework access (streaming, context), use `custom_run`
mode — see [Tool System](../concepts/tool.md).

## What Just Happened

- `@simple_tool`: schema from type hints + docstring, zero boilerplate
- `@on_tools`: explicit JSON Schema with validation constraints
- Both register tools globally at module load; results flow back to the model

## Next

[3. Streaming and Callbacks](streaming.md) — read the stream, including
structured metadata.
