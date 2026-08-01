# ToolFunctionSchema

The ToolFunctionSchema class validates the complete function field structure for tool calling.

## Properties

- `function` (FunctionDefinitionSchema): Function definition (name, description, parameters)
- `type` (Literal["function"]): Default `"function"`. Fixed type marker
- `strict` (bool): Default `False`. Whether in strict mode

## Description

The ToolFunctionSchema class inherits from BaseModel and represents the full function-calling schema structure sent to the model. It wraps a [FunctionDefinitionSchema](FunctionDefinitionSchema.md) with the `type` marker and strict-mode flag.

Note: `ToolChoice` is a type alias defined as `Literal["none", "auto", "required"] | ToolFunctionSchema`.

## Example

```python
from amrita_core.tools.models import ToolFunctionSchema, FunctionDefinitionSchema

schema = ToolFunctionSchema(
    function=FunctionDefinitionSchema(
        name="search",
        description="Search the web",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    ),
    strict=False,
)
```
