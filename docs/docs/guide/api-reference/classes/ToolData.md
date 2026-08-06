# ToolData

The ToolData class is the data model for registering Tools.

## Properties

- `data` (ToolFunctionSchema): Tool metadata (function definition, type, strict mode)
- `func`: The tool function. Either `Callable[[dict[str, Any]], Awaitable[str]]` or `Callable[[ToolContext], Awaitable[str | None]]`
- `custom_run` (bool): Default `False`. Whether to customize execution; if enabled, passes Context class instead of dict and does not enforce a return value
- `enable_if` (Callable[[], bool]): Default `lambda: True`. Whether to enable this tool

## Description

The ToolData class inherits from BaseModel and wraps a tool's metadata together with its implementation function. It is the unit registered in [MultiToolsManager](MultiToolsManager.md) and queried via `get_tool(name)`.

## Example

```python
from amrita_core.tools.models import (
    ToolData,
    ToolFunctionSchema,
    FunctionDefinitionSchema,
)

tool_data = ToolData(
    data=ToolFunctionSchema(
        function=FunctionDefinitionSchema(
            name="get_weather",
            description="Get weather for a city",
            parameters={"type": "object", "properties": {"city": {"type": "string"}}},
        )
    ),
    func=my_async_weather_func,
)
```
