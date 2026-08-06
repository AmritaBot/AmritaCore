# ToolData

ToolData 类是注册工具的数据模型。

## 属性

- `data` (ToolFunctionSchema)：工具元数据（函数定义、类型、严格模式）
- `func`：工具函数。`Callable[[dict[str, Any]], Awaitable[str]]` 或 `Callable[[ToolContext], Awaitable[str | None]]`
- `custom_run` (bool)：默认 `False`。是否自定义执行；启用时传入 Context 类而非 dict，且不强制返回值
- `enable_if` (Callable[[], bool])：默认 `lambda: True`。是否启用此工具

## 描述

ToolData 类继承自 BaseModel，将工具的元数据与其实现函数包装在一起。它是注册在 [MultiToolsManager](MultiToolsManager.md) 中的单元。

## 示例

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
            description="获取城市天气",
            parameters={"type": "object", "properties": {"city": {"type": "string"}}},
        )
    ),
    func=my_async_weather_func,
)
```
