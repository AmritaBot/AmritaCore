# ToolFunctionSchema

ToolFunctionSchema 类验证工具调用的完整函数字段结构。

## 属性

- `function` (FunctionDefinitionSchema)：函数定义（名称、描述、参数）
- `type` (Literal["function"])：默认 `"function"`。固定类型标记
- `strict` (bool)：默认 `False`。是否处于严格模式

## 描述

ToolFunctionSchema 类继承自 BaseModel，表示发送给模型的完整函数调用模式结构。它用 `type` 标记和严格模式标志包装 [FunctionDefinitionSchema](FunctionDefinitionSchema.md)。

注意：`ToolChoice` 是定义为 `Literal["none", "auto", "required"] | ToolFunctionSchema` 的类型别名。

## 示例

```python
from amrita_core.tools.models import ToolFunctionSchema, FunctionDefinitionSchema

schema = ToolFunctionSchema(
    function=FunctionDefinitionSchema(
        name="search",
        description="搜索网页",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    ),
    strict=False,
)
```
