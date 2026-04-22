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

`@on_tools` 装饰器将函数注册为可调用工具，并提供更高级的用法：

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

### 高级 FunctionPropertySchema 用法

`FunctionPropertySchema` 支持全面的 JSON Schema 验证，包含类型特定的约束：

#### 数值类型约束

```python
temperature = FunctionPropertySchema(
type="number",
description="摄氏温度",
minimum=-273.15, # 绝对零度
maximum=1000.0, # 合理的上限
multipleOf=0.1, # 精确到 0.1 度
exclusiveMinimum=False, # 最小值包含在内
exclusiveMaximum=False # 最大值包含在内
)

```

#### 字符串类型约束

```python
email = FunctionPropertySchema(
    type="string",
    description="用户邮箱地址",
    minLength=5,          # 最小邮箱长度
    maxLength=254,        # 根据 RFC 的最大邮箱长度
    pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", # 邮箱正则表达式
    format="email"        # 标准邮箱格式
)

password = FunctionPropertySchema(
    type="string",
    description="用户密码",
    minLength=8,          # 最小密码强度
    maxLength=128,        # 最大合理长度
    pattern=r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).*$"  # 必须包含小写、大写和数字
)
```

#### 数组类型约束

```python
tags = FunctionPropertySchema(
type="array",
description="标签列表",
items=FunctionPropertySchema(type="string", minLength=1, maxLength=50),
minItems=1, # 至少需要一个标签
maxItems=10, # 最多 10 个标签
uniqueItems=True # 不允许重复标签
)

```

#### 对象类型约束

```python
address = FunctionPropertySchema(
    type="object",
    description="用户地址",
    properties={
        "street": FunctionPropertySchema(type="string", minLength=1),
        "city": FunctionPropertySchema(type="string", minLength=1),
        "country": FunctionPropertySchema(type="string", minLength=2, maxLength=2), # ISO 国家代码
    },
    required=["street", "city", "country"],
    additionalProperties=False  # 不允许额外属性
)
```

#### 枚举和常量值

```python
# 枚举允许的值
unit = FunctionPropertySchema(
    type="string",
    description="温度单位",
    enum=["celsius", "fahrenheit", "kelvin"]
)

# 常量值（必须完全等于）
api_version = FunctionPropertySchema(
    type="string",
    description="API 版本",
    const="v1.0"
)

# 默认值
optional_note = FunctionPropertySchema(
    type="string",
    description="可选备注",
    default="未提供备注"
)
```

#### 联合类型

```python
# 接受多种类型
flexible_input = FunctionPropertySchema(
    type=["string", "number"],  # 可以是字符串或数字
    description="灵活的输入参数"
)
```

### 验证规则

`FunctionPropertySchema` 强制执行严格的类型特定验证规则：

1. **对象类型 (`object`)**：
   - 必须定义 `properties`
   - 如果未提供，`required` 默认为空列表
   - 数组约束 (`items`, `minItems` 等) 必须为 `None`
   - 字符串/数值约束必须为 `None`

2. **数组类型 (`array`)**：
   - 必须定义 `items`
   - 如果未提供，`uniqueItems` 默认为 `False`
   - 字符串/数值/对象约束必须为 `None`
   - `minItems` 和 `maxItems` 必须为非负数，且 `minItems <= maxItems`

3. **字符串类型 (`string`)**：
   - `minLength` 和 `maxLength` 必须为非负数，且 `minLength <= maxLength`
   - 数值/数组/对象约束必须为 `None`

4. **数值类型 (`number`/`integer`)**：
   - 必须满足 `minimum <= maximum`
   - `multipleOf` 必须为正数
   - 字符串/数组/对象约束必须为 `None`

5. **布尔类型 (`boolean`)**：
   - 所有其他约束类型必须为 `None`

这些验证规则确保您的工具模式格式良好，并与标准 JSON Schema 规范兼容。

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
