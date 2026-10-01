# FunctionDefinitionSchema

FunctionDefinitionSchema 类是函数参数的模式定义。

## 属性

- `name` (str)：函数名
- `description` (str)：函数描述
- `parameters` (`FunctionParametersSchema`)：函数参数定义，包含参数 `type`、`properties` 和 `required` 列表

## 描述

FunctionDefinitionSchema 类用于定义函数参数的结构和类型信息。通常用于描述工具函数的参数，以便 AI 模型能够正确理解并调用这些函数。

该类继承自 BaseModel，因此具备 Pydantic 模型的全部特性，包括数据校验与序列化功能。它允许开发者定义函数参数名、类型、默认值和描述。

## 用途

- 为工具函数定义参数模式
- 校验传给函数的参数
- 向 AI 模型提供函数参数的结构信息
- 确保函数调用过程中参数的正确性

## 示例

```python
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

# 定义一个带参数校验的工具函数模式
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
