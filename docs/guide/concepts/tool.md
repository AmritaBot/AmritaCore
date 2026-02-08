# Tool System

## 3.4.1 Tool Integration Framework

AmritaCore provides a comprehensive framework for integrating external tools and services. Tools can be registered and made available to the agent for use during conversations.

## 3.4.2 @simple_tool Decorator Registration

The `@simple_tool` decorator registers functions as simple tools:

```python
from amrita_core import simple_tool

@simple_tool
def add(a: int, b: int) -> int:
    """Adds two numbers
    Args:
        a (int): The first number
        b (int): The second number
    
    Returns:
        int: The sum of the two numbers
    """

```

### Description

The `@simple_tool` decorator registers functions as simple tools.

Args in the function signature are considered arguments to the function.Their types are inferred from the type annotations, and their descriptions are inferred from the docstring which should be written as **Google's Python Docstring format**.

## 3.4.3 @on_tools Decorator Registration

The `@on_tools` decorator registers functions as callable tools and provides a more advanced usage:

```python
from typing import Any

from amrita_core import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

DEFINITION = FunctionDefinitionSchema(
    name="Add number",
    description="Add two numbers",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "a": FunctionPropertySchema(type="number",description="The first number"),
            "b": FunctionPropertySchema(type="number",description="The second number"),
        },
        required=["a", "b"],
    ),
)

@on_tools(DEFINITION)
async def add(data: dict[str, Any]) -> str:
    """Add two numbers"""
    return str(data["a"] + data["b"])

```

## 3.4.4 FunctionDefinitionSchema Function Schema

The [FunctionDefinitionSchema](../api-reference/classes/FunctionDefinitionSchema.md) class defines the schema for function parameters:

```python
from amrita_core.tools.models import FunctionDefinitionSchema

schema = FunctionDefinitionSchema(
    name="get_time",
    description="Get the current time in a given timezone",
    parameters=...
)
```

## 3.4.5 ToolsManager Tool Manager

The [ToolsManager](../api-reference/classes/ToolsManager.md) class manages registered tools:

```python
from amrita_core.tools.manager import ToolsManager

manager = ToolsManager()
# Get available tools
registered_tools = manager.get_tools()
```

## 3.4.6 Dynamic Tool Discovery

Tools are automatically discovered and registered when modules are imported:

```python
# When you import modules containing @on_tools decorated functions
from . import my_tools  # Tools are automatically registered; make sure they are only imported once.
```
