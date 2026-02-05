# Tool System

## 3.4.1 Tool Integration Framework

AmritaCore provides a comprehensive framework for integrating external tools and services. Tools can be registered and made available to the agent for use during conversations.

## 3.4.2 @on_tools Decorator Registration

The `@on_tools` decorator registers functions as callable tools:

```python
from amrita_core.tools.manager import on_tools
from amrita_core.types import Function

schema = FunctionDefinitionSchema(
    name="get_time",
    description="Get the current time in a given timezone",
    parameters=...
)

@on_tools(
    data=schema,
    custom_run=True,
    enable_if=lambda: get_config().function_config.agent_middle_message,
)
async def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    # Implementation here
    return f"Weather for {city}: Sunny"
```

## 3.4.3 FunctionDefinitionSchema Function Schema

The [FunctionDefinitionSchema](../api-reference/classes/FunctionDefinitionSchema.md) class defines the schema for function parameters:

```python
from amrita_core.tools.models import FunctionDefinitionSchema

schema = FunctionDefinitionSchema(
    name="get_time",
    description="Get the current time in a given timezone",
    parameters=...
)
```

## 3.4.4 ToolsManager Tool Manager

The [ToolsManager](../api-reference/classes/ToolsManager.md) class manages registered tools:

```python
from amrita_core.tools.manager import ToolsManager

manager = ToolsManager()
# Get available tools
registered_tools = manager.get_tools()
```

## 3.4.5 Dynamic Tool Discovery

Tools are automatically discovered and registered when modules are imported:

```python
# When you import modules containing @on_tools decorated functions
from . import my_tools  # Tools are automatically registered
```
