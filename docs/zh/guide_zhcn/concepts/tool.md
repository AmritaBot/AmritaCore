# 工具系统

## 3.4.1 工具集成框架

AmritaCore 提供了一个全面的框架来集成外部工具和服务。工具可以被注册并提供给代理在对话期间使用。

## 3.4.2 @on_tools 装饰器注册

`@on_tools` 装饰器将函数注册为可调用工具：

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

## 3.4.3 FunctionDefinitionSchema 函数模式

[FunctionDefinitionSchema](../api-reference/classes/FunctionDefinitionSchema.md) 类定义函数参数的模式：

```python
from amrita_core.tools.models import FunctionDefinitionSchema

schema = FunctionDefinitionSchema(
    name="get_time",
    description="获取给定时区的当前时间",
    parameters=...
)
```

## 3.4.4 ToolsManager 工具管理器

[ToolsManager](../api-reference/classes/ToolsManager.md) 类管理已注册的工具：

```python
from amrita_core.tools.manager import ToolsManager

manager = ToolsManager()
# 获取可用工具
registered_tools = manager.get_tools()
```

## 3.4.5 动态工具发现

工具在导入模块时自动发现和注册：

```python
# 当您导入包含 @on_tools 装饰函数的模块时
from . import my_tools  # 工具会自动注册
```