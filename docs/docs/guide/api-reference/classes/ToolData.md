# ToolData

The ToolData class is the data model for registering Tools.

## Properties

- `data` (ToolFunctionSchema): Tool metadata (function definition, type, strict mode)
- `func`: The tool function. Either `Callable[[dict[str, Any]], Awaitable[str]]` or `Callable[[ToolContext], Awaitable[str | None]]`
- `custom_run` (bool): Default `False`. Whether to customize execution; if enabled, passes Context class instead of dict and does not enforce a return value
- `enable_if` (Callable[[], bool]): Default `lambda: True`. Whether to enable this tool
- `concurrency_safe` (bool | Callable[[dict[str, Any]], bool]): Default `True`. Whether calls of this tool may overlap sibling calls of the same tool round. A callable decides per call from the parsed arguments and must return a literal `True`; a raised exception counts as unsafe.

## Methods

- `is_concurrency_safe(arguments)`: Resolve the flag for one call. A `bool` is returned as is, a callable is invoked with the arguments; an exception or any return value other than a literal `True` is unsafe, so an undeclared, mis-declared or failing classifier isolates the call instead of letting it race.

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
    concurrency_safe=False,
)
```
