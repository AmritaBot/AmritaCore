# ToolData

ToolData 类是注册工具的数据模型。

## 属性

- `data` (ToolFunctionSchema)：工具元数据（函数定义、类型、严格模式）
- `func`：工具函数。`Callable[[dict[str, Any]], Awaitable[str]]` 或 `Callable[[ToolContext], Awaitable[str | None]]`
- `custom_run` (bool)：默认 `False`。是否自定义执行；启用时传入 Context 类而非 dict，且不强制返回值
- `enable_if` (Callable[[], bool])：默认 `lambda: True`。是否启用此工具
- `concurrency_safe` (bool | Callable[[dict[str, Any]], bool])：默认 `True`。该工具的调用是否可以与同一轮的其他调用重叠执行。传可调用对象时按每次调用的已解析参数判定，只有返回字面 `True` 才算安全；抛异常按不安全处理。

## 方法

- `is_concurrency_safe(arguments)`：解析该次调用的并发安全性。`bool` 值直接返回，可调用对象以参数调用；异常或非字面 `True` 的返回值都判为不安全，因此未声明、声明错误或分类器失效时，调用会被单独执行而不是与他人竞争。

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
    concurrency_safe=False,
)
```
