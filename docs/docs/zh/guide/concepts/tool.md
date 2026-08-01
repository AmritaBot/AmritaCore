# 工具系统

## 工具集成框架

AmritaCore 提供了一个完备的框架用于集成外部工具和服务。工具可以注册并供 agent 在对话期间使用。

有三种主要的工具注册方式：

1. **`@simple_tool` 装饰器**：一种简单的自动注册方法，从函数签名和文档字符串推断 schema。以此方式注册的工具将添加到全局容器中，对所有会话可用。

2. **`@on_tools` 装饰器**：一种细粒度的注册方法，允许使用 `FunctionDefinitionSchema` 显式控制工具 schema 定义。

3. **直接操作 `ToolsManager`/`MultiToolsManager`**：最精细的方法，允许在运行时以编程方式注册、修改和删除工具，包括会话特定的工具管理。

> **重要提示**：像 `@simple_tool` 和 `@on_tools` 这样的装饰器在**模块加载期间**将工具注册到全局容器中，此时还没有创建任何会话。这是因为会话仅在对话开始时的运行时才被实例化。对于会话特定的工具管理，请使用直接的 `ToolsManager` 操作。

## @simple_tool 装饰器注册

`@simple_tool` 装饰器将函数注册为简单工具：

```python
from amrita_core import simple_tool

@simple_tool
def add(a: int, b: int) -> int:
    """将两个数字相加
    Args:
        a (int): 第一个数字
        b (int): 第二个数字

    Returns:
        int: 两个数的和
    """
```

### 说明

`@simple_tool` 装饰器通过从函数类型注解和 Google 风格文档字符串自动推断工具 schema，提供了一种简单的工具注册方式。

#### 支持的类型

`@simple_tool` 装饰器现在支持丰富的参数类型：

- **基本类型**：`str`、`int`、`float`、`bool`
- **Literal 类型**：`Literal["a", "b", "c"]` → 自动生成为带 `enum` 约束的 `string` 类型；`Literal[1, 2, 3]` 同样支持 `integer` 枚举。异构 Literal（如 `Literal["a", 1]`）会抛出错误
- **Pydantic BaseModel 类**：用于复杂的嵌套对象结构
- **容器类型**：`List[T]`，其中 T 是受支持的类型（仅单层容器）
- **Optional 类型**：`Optional[T]` 或 `T | None`（等同于 Union[T, None]）

#### Pydantic 模型最佳实践

当使用 Pydantic `BaseModel` 类作为参数时，类文档字符串（`__doc__`）会自动用作 JSON Schema 对象的描述。字段描述应使用 Pydantic 的 `Field` 函数提供。

**重要提示**：Pydantic 模型的类级文档字符串优先于函数文档字符串中的参数描述。这意味着当你定义 Pydantic 模型参数时，其类文档字符串将用作 JSON Schema 中的对象描述，无论你在函数的 Args 部分写了什么。

**正确示例**：

```python
from typing import Optional
from pydantic import BaseModel, Field

class UserAddress(BaseModel):
    """表示用户的物理地址，包含街道、城市和国家信息。"""

    street: str = Field(..., description="包含门牌号的街道地址")
    city: str = Field(..., description="城市名称")
    country: str = Field(..., description="ISO 3166-1 alpha-2 国家代码", min_length=2, max_length=2)
    postal_code: Optional[str] = Field(None, description="邮政编码")

@simple_tool
def process_address(address: UserAddress) -> str:
    """处理用户地址对象。

    Args:
        address (UserAddress): 此描述将被**忽略**，因为 UserAddress 类有自己的文档字符串。
    """
    return f"已处理 {address.city}, {address.country} 的地址"
```

#### 不支持的类型（会抛出 ValueError）

- **Dict 类型**：请改用 Pydantic 模型表示对象结构
- **嵌套容器**：如 `List[List[str]]`、`Dict[str, List[int]]`
- **包含多个非 None 类型的 Union 类型**：如 `Union[str, int]` 或 `str | int`
- **Any 或 object 类型**：出于类型安全考虑明确拒绝

函数签名中的 Args 被视为函数的参数。其类型从类型注解推断，其描述从应按 **Google Python 文档字符串格式**编写的文档字符串推断。

## @on_tools 装饰器注册

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
    name="数字相加",
    description="将两个数字相加",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "a": FunctionPropertySchema(type="number", description="第一个数字"),
            "b": FunctionPropertySchema(type="number", description="第二个数字"),
        },
        required=["a", "b"],
    ),
)

@on_tools(DEFINITION)
async def add(data: dict[str, Any]) -> str:
    """将两个数字相加"""
    return str(data["a"] + data["b"])
```

### 高级 FunctionPropertySchema 用法

`FunctionPropertySchema` 支持全面的 JSON Schema 校验，具有特定类型的约束：

#### 数字类型约束

```python
temperature = FunctionPropertySchema(
    type="number",
    description="摄氏温度",
    minimum=-273.15,      # 绝对零度
    maximum=1000.0,       # 合理的上限
    multipleOf=0.1,       # 精度到 0.1 度
    exclusiveMinimum=False, # 最小值是包含的
    exclusiveMaximum=False  # 最大值是包含的
)
```

#### 字符串类型约束

```python
email = FunctionPropertySchema(
    type="string",
    description="用户邮箱地址",
    minLength=5,          # 最小邮箱长度
    maxLength=254,        # 按 RFC 标准的最大邮箱长度
    pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", # 邮箱正则
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
    minItems=1,           # 至少需要一个标签
    maxItems=10,          # 最多 10 个标签
    uniqueItems=True      # 不允许重复标签
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

# 常量值（必须完全相等）
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

> **注意**：`FunctionPropertySchema` 中的联合类型（手动 schema 定义）可以使用 `type=["string", "number"]` 来接受多种类型，但此功能**不适用于** `@simple_tool` 装饰器，后者仅支持 `Optional[T]` 模式。

```python
# 接受多种类型（仅手动 schema 定义可用）
flexible_input = FunctionPropertySchema(
    type=["string", "number"],  # 可以是字符串或数字
    description="灵活的输入参数"
)
```

### 校验规则

`FunctionPropertySchema` 执行严格的类型特定校验规则：

1. **对象类型（`object`）**：
   - 必须定义 `properties`
   - 如果未提供 `required`，默认为空列表
   - 数组约束（`items`、`minItems` 等）必须为 `None`
   - 字符串/数字约束必须为 `None`

2. **数组类型（`array`）**：
   - 必须定义 `items`
   - 如果未提供 `uniqueItems`，默认为 `False`
   - 字符串/数字/对象约束必须为 `None`
   - `minItems` 和 `maxItems` 必须为非负数，且 `minItems <= maxItems`

3. **字符串类型（`string`）**：
   - `minLength` 和 `maxLength` 必须为非负数，且 `minLength <= maxLength`
   - 数字/数组/对象约束必须为 `None`

4. **数字类型（`number`/`integer`）**：
   - 必须满足 `minimum <= maximum`
   - `multipleOf` 必须为正数
   - 字符串/数组/对象约束必须为 `None`

5. **布尔类型（`boolean`）**：
   - 所有其他约束类型必须为 `None`

这些校验规则确保你的工具 schema 规范且兼容标准 JSON Schema 规范。

## FunctionDefinitionSchema 函数 Schema

[FunctionDefinitionSchema](../api-reference/classes/FunctionDefinitionSchema.md) 类定义了函数参数的 schema：

```python
from amrita_core.tools.models import FunctionDefinitionSchema

schema = FunctionDefinitionSchema(
    name="get_time",
    description="获取给定时区的当前时间",
    parameters=...
)
```

## ToolsManager 工具管理器

[ToolsManager](../api-reference/classes/ToolsManager.md) 类管理已注册的工具：

```python
from amrita_core.tools.manager import ToolsManager

manager = ToolsManager()
# 获取可用工具
registered_tools = manager.get_tools()
```

## 动态工具发现

工具在模块导入时自动被发现和注册：

```python
# 当你导入包含 @on_tools 装饰函数的模块时
from . import my_tools  # 工具自动注册；确保每个模块只导入一次
```
