# 工具系统

## 3.4.1 工具集成框架

AmritaCore 提供了一个全面的框架来集成外部工具和服务。工具可以被注册并提供给Agent在对话期间使用。

## 3.4.2 @simple_tool 函数注册

`@simple_tool` 函数可以以较为简单的方式注册工具：

```python
from amrita_core import simple_tool

@simple_tool
def my_tool(arg1: str, arg2: int) -> str:
    """My tool description

    Args:
        arg1 (str): Argument 1 description
        arg2 (int): Argument 2 description
    """
    return "Tool output"
```

### 说明

`@simple_tool` 函数注册了工具，并定义了工具参数和返回值类型。

它将自动从工具的文档字符串中提取参数描述，遵循谷歌的Python英文注释范式，类型由类型注解自动推断，但此装饰器只支持**基本类型**，其他类型参数都将fallback为str。

## 3.4.3 @on_tools 装饰器注册

`@on_tools` 装饰器是一种更高级的将函数注册为可调用工具的方法：

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

## 3.4.4 FunctionDefinitionSchema 函数模式

[FunctionDefinitionSchema](../api-reference/classes/FunctionDefinitionSchema.md) 类定义函数参数的模式：

```python
from amrita_core.tools.models import FunctionDefinitionSchema

schema = FunctionDefinitionSchema(
    name="get_time",
    description="获取给定时区的当前时间",
    parameters=...
)
```

## 3.4.5 ToolsManager 工具管理器

[ToolsManager](../api-reference/classes/ToolsManager.md) 类管理已注册的工具：

```python
from amrita_core.tools.manager import ToolsManager

manager = ToolsManager()
# 获取可用工具
registered_tools = manager.get_tools()
```

## 3.4.6 动态工具发现

工具在导入模块时自动发现和注册：

```python
# 当您导入包含 @on_tools 装饰函数的模块时
from . import my_tools  # 工具会自动注册
```
