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

## 3.4.4 嵌入向量支持

AmritaCore通过适配器系统提供内置的嵌入向量生成功能。

### 适配器类型

AmritaCore适配器现在通过 [`ADAPTER_TYPE`](../api-reference/classes/ADAPTER_TYPE.md) 枚举支持多种类型：

- **`"text-gen"`**: 传统的文本生成/完成（默认）
- **`"embed"`**: 嵌入向量生成
- **`"rerank"`**: 重排序功能（计划在未来版本中实现）

### 嵌入适配器实现

要创建嵌入适配器，请继承 [`ModelAdapter`](../api-reference/classes/ModelAdapter.md) 并实现所需方法：

```python
from amrita_core.protocol import ModelAdapter
from amrita_core.types import EmbeddingChunk

class MyEmbeddingAdapter(ModelAdapter):
    @staticmethod
    def get_adapter_protocol() -> str:
        return "my-embedding-protocol"

    @staticmethod
    def get_type() -> str:
        return "embed"

    async def call_embed(self, texts: Iterable[str], **kwargs) -> Sequence[EmbeddingChunk]:
        """为给定文本生成嵌入向量"""
        embeddings = []
        for idx, text in enumerate(texts):
            # 您的嵌入逻辑在这里
            embedding_vector = self._generate_embedding(text)
            embeddings.append(
                EmbeddingChunk(embedding=embedding_vector, index=idx)
            )
        return embeddings

    def _generate_embedding(self, text: str) -> list[float]:
        # 实现您的嵌入生成逻辑
        pass
```

### 使用嵌入适配器

嵌入适配器可以通过标准预设系统使用：

```python
from amrita_core.preset import PresetManager, ModelPreset
from amrita_core.libchat import call_completion

# 为嵌入适配器创建预设
preset = ModelPreset(
    protocol="my-embedding-protocol",
    model="embedding-model-v1",
    # ... 其他配置
)

# 注册预设
PresetManager().register_preset("embedding-preset", preset)

# 使用嵌入适配器
texts = ["Hello world", "How are you?"]
embeddings = await call_completion(preset=preset, messages=texts)
```

**注意**：`call_completion` 函数会自动检测适配器类型并调用适当的方法（`"text-gen"` 调用 `call_api`，`"embed"` 调用 `call_embed`）。

### EmbeddingChunk 结构

[`EmbeddingChunk`](../api-reference/classes/EmbeddingChunk.md) 类表示单个嵌入结果：

- **`embedding`**: `Sequence[float]` - 作为浮点数序列的嵌入向量
- **`index`**: `int` - 文本在输入序列中的原始索引

此结构保持与OpenAI嵌入响应格式的兼容性，同时提供类型安全性。

### 类型安全和验证

AmritaCore包含适配器使用的自动类型验证：

```python
# 如果适配器不支持 "text-gen"，这将引发 RuntimeError
response = await call_completion(preset=text_gen_preset, messages=["Hello"])

# 这将与嵌入适配器正常工作
embeddings = await call_completion(preset=embedding_preset, messages=["Hello"])
```

框架验证适配器类型是否与预期用途匹配，防止意外误用嵌入适配器进行文本生成，反之亦然。
