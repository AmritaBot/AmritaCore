# FunctionDefinitionSchema

The FunctionDefinitionSchema class is the schema definition for function parameters.

## Properties

- `name` (str): Function name
- `description` (str): Function description
- `parameters` ([FunctionParametersSchema](FunctionParametersSchema.md)): Function parameter definition, containing the parameter `type`, `properties`, and `required` list

## Description

The FunctionDefinitionSchema class is used to define the structure and type information of function parameters. It is typically used to describe the parameters of tool functions so that the AI model can correctly understand and call these functions.

This class inherits from BaseModel, thus possessing all features of Pydantic models, including data validation and serialization functions. It allows developers to define function parameter names, types, default values, and descriptions.

## Purpose

- Define parameter schemas for tool functions
- Validate parameters passed to functions
- Provide structure information of function parameters to AI models
- Ensure correctness of parameters during function calls

## Example

```python
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

# Define a tool function schema with parameter validation
tool = FunctionDefinitionSchema(
    name="calculate_math",
    description="Calculate the result of a mathematical expression",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "expression": FunctionPropertySchema(
                type="string",
                description="Mathematical expression to evaluate",
            ),
        },
        required=["expression"],
    ),
)
```
