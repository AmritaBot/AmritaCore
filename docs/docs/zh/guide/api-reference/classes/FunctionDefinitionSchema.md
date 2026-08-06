# FunctionDefinitionSchema

FunctionDefinitionSchema 类是函数参数的模式定义。

## 属性

- `name` (str)：函数名
- `description` (str)：函数描述
- `parameters` ([FunctionParametersSchema](FunctionParametersSchema.md))：函数参数定义，包含参数 `type`、`properties` 和 `required` 列表

## 描述

FunctionDefinitionSchema 类用于定义函数参数的结构和类型信息。通常用于描述工具函数的参数，以便 AI 模型能够正确理解并调用这些函数。

## 示例

```python
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

tool = FunctionDefinitionSchema(
    name="calculate_math",
    description="计算数学表达式的结果",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "expression": FunctionPropertySchema(
                type="string",
                description="要计算的数学表达式",
            ),
        },
        required=["expression"],
    ),
)
```
