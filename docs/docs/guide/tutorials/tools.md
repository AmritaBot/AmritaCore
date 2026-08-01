# Add Tools to Your Agent

Tools let your agent call functions you define — querying a database, calculating values, fetching web pages, and more. In this tutorial you will register tools with [`@simple_tool`](../api-reference/index.md#simple_tool) and [`@on_tools`](../api-reference/index.md#on_tools), then let your agent use them.

## 1. A Simple Tool with `@simple_tool`

The [`@simple_tool`](../api-reference/index.md#simple_tool) decorator registers a function as a tool with automatic schema inference from its type annotations and Google-style docstring:

```python
from amrita_core import simple_tool


@simple_tool
def add(a: int, b: int) -> int:
    """Add two numbers.

    Args:
        a: The first number.
        b: The second number.
    """
    return a + b
```

Supported parameter types are `str`, `int`, `float`, `bool`, `Literal[...]`, Pydantic models, single-level `list[T]`, and `Optional[T]`. Unsupported types (e.g. dicts, nested containers, multi-type unions) raise a `ValueError` at registration time.

## 2. Use the Tool in Your Agent

`@simple_tool` registers into the **global container**, so your agent picks it up automatically:

```python
import asyncio

from amrita_core import create_agent, minimal_init, simple_tool


@simple_tool
def add(a: int, b: int) -> int:
    """Add two numbers.

    Args:
        a: The first number.
        b: The second number.
    """
    return a + b


async def main() -> None:
    await minimal_init()

    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="sk-...",
        model="gpt-4o-mini",
        train="You are a helpful assistant with access to tools.",
    )

    chat = agent.get_chatobject("What is 1234 + 5678?")
    async with chat.begin():
        async for message in chat.io_stream.get_response_generator():
            print(message if isinstance(message, str) else message.get_content(), end="")
        await chat  # Wait for the task to finish — exiting would cancel it
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())
```

The default [ReAct strategy](../concepts/agent-strategy.md) will decide when to call the tool and feed the result back into the conversation.

## 3. Full Control with `@on_tools`

When you need precise control over the tool schema (parameter descriptions, required fields), use [`@on_tools`](../api-reference/index.md#on_tools) with an explicit [FunctionDefinitionSchema](../api-reference/classes/FunctionDefinitionSchema.md):

```python
from typing import Any

from amrita_core import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

DEFINITION = FunctionDefinitionSchema(
    name="add",
    description="Add two numbers",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "a": FunctionPropertySchema(type="number", description="The first number"),
            "b": FunctionPropertySchema(type="number", description="The second number"),
        },
        required=["a", "b"],
    ),
)


@on_tools(DEFINITION)
async def add(data: dict[str, Any]) -> str:
    """Add two numbers"""
    return str(data["a"] + data["b"])
```

Note that with `@on_tools` the handler receives the **arguments dict** (`data`), not named parameters, and must return a string.

## 4. What Just Happened

- `@simple_tool` inferred a schema from your signature and docstring, then registered the tool in the global [ToolsManager](../api-reference/classes/ToolsManager.md)
- The agent's [tool system](../concepts/tool.md) exposed the schema to the model, executed the function when called, and returned the result as a [ToolResult](../api-reference/classes/ToolResult.md)

## Next Steps

- [Stream responses and use callbacks](streaming.md)
- [Intercept the pipeline with events](event-hooks.md)
- Learn about tool execution details in [Core Concepts: Tool System](../concepts/tool.md)
