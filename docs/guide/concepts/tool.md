# Tool System

## 3.4.1 Tool Integration Framework

AmritaCore provides a comprehensive framework for integrating external tools and services. Tools can be registered and made available to the agent for use during conversations.

There are three main approaches to tool registration:

1. **`@simple_tool` decorator**: A simple, automatic registration method that infers schema from function signatures and docstrings. Tools registered this way are added to the global container and are available to all sessions.

2. **`@on_tools` decorator**: A fine-grained registration method that allows explicit control over the tool schema definition using `FunctionDefinitionSchema`.

3. **Direct `ToolsManager`/`MultiToolsManager` manipulation**: The most granular approach, allowing programmatic tool registration, modification, and removal at runtime, including session-specific tool management.

> **Important Note**: Decorators like `@simple_tool` and `@on_tools` register tools to the **global container** during module loading time, before any session is created. This is because sessions are only instantiated at runtime when conversations begin. For session-specific tool management, use direct `ToolsManager` operations.

## 3.4.2 @simple_tool Decorator Registration

The `@simple_tool` decorator registers functions as simple tools:

```python
from amrita_core import simple_tool

@simple_tool
def add(a: int, b: int) -> int:
    """Adds two numbers
    Args:
        a (int): The first number
        b (int): The second number

    Returns:
        int: The sum of the two numbers
    """

```

### Description

The `@simple_tool` decorator provides a simple way to register tools by automatically inferring the tool schema from function type annotations and Google-style docstrings.

#### Supported Types

The `@simple_tool` decorator now supports a rich set of parameter types:

- **Basic types**: `str`, `int`, `float`, `bool`
- **Pydantic BaseModel classes**: For complex nested object structures
- **Container types**: `List[T]` where T is a supported type (single-level containers only)
- **Optional types**: `Optional[T]` or `T | None` (equivalent to Union[T, None])

#### Pydantic Model Best Practices

When using Pydantic `BaseModel` classes as parameters, the class docstring (`__doc__`) is automatically used as the description for the JSON Schema object. Field descriptions should be provided using Pydantic's `Field` function.

**Important Note**: The class-level docstring of a Pydantic model takes precedence over any parameter descriptions in the function's docstring. This means that when you define a Pydantic model parameter, its class docstring will be used as the object description in the JSON Schema, regardless of what you write in the function's Args section.

**Correct Example**:

```python
from typing import Optional
from pydantic import BaseModel, Field

class UserAddress(BaseModel):
    """Represents a user's physical address with street, city, and country information."""

    street: str = Field(..., description="The street address including house number")
    city: str = Field(..., description="The city name")
    country: str = Field(..., description="ISO 3166-1 alpha-2 country code", min_length=2, max_length=2)
    postal_code: Optional[str] = Field(None, description="Postal or ZIP code")

@simple_tool
def process_address(address: UserAddress) -> str:
    """Process a user address object.

    Args:
        address (UserAddress): This description will be IGNORED because the UserAddress class has its own docstring.
    """
    return f"Processed address for {address.city}, {address.country}"
```

In this example:

- The class docstring `"Represents a user's physical address..."` becomes the JSON Schema object description
- Each field uses `Field(..., description="...")` to provide field-level descriptions
- Type constraints like `min_length=2, max_length=2` are properly applied to the `country` field
- The parameter description in the function's docstring (`"This description will be IGNORED..."`) is **ignored** because the Pydantic model class already has a docstring

#### Unsupported Types (will raise ValueError)

- **Dict types**: Use Pydantic models instead for object structures
- **Nested containers**: e.g., `List[List[str]]`, `Dict[str, List[int]]`
- **Union types with multiple non-None types**: e.g., `Union[str, int]` or `str | int`
- **Any or object types**: These are explicitly rejected for type safety

Args in the function signature are considered arguments to the function. Their types are inferred from the type annotations, and their descriptions are inferred from the docstring which should be written as **Google's Python Docstring format**.

## 3.4.3 @on_tools Decorator Registration

The `@on_tools` decorator registers functions as callable tools and provides a more advanced usage:

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

### Advanced FunctionPropertySchema Usage

`FunctionPropertySchema` supports comprehensive JSON Schema validation with type-specific constraints:

#### Numeric Type Constraints

```python
temperature = FunctionPropertySchema(
    type="number",
    description="Temperature in Celsius",
    minimum=-273.15,      # Absolute zero
    maximum=1000.0,       # Reasonable upper limit
    multipleOf=0.1,       # Precision to 0.1 degrees
    exclusiveMinimum=False, # Minimum is inclusive
    exclusiveMaximum=False  # Maximum is inclusive
)
```

#### String Type Constraints

```python
email = FunctionPropertySchema(
    type="string",
    description="User email address",
    minLength=5,          # Minimum email length
    maxLength=254,        # Maximum email length per RFC
    pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", # Email regex
    format="email"        # Standard email format
)

password = FunctionPropertySchema(
    type="string",
    description="User password",
    minLength=8,          # Minimum password strength
    maxLength=128,        # Maximum reasonable length
    pattern=r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).*$"  # Must contain lowercase, uppercase, and digit
)
```

#### Array Type Constraints

```python
tags = FunctionPropertySchema(
    type="array",
    description="List of tags",
    items=FunctionPropertySchema(type="string", minLength=1, maxLength=50),
    minItems=1,           # At least one tag required
    maxItems=10,          # Maximum 10 tags
    uniqueItems=True      # No duplicate tags allowed
)
```

#### Object Type Constraints

```python
address = FunctionPropertySchema(
    type="object",
    description="User address",
    properties={
        "street": FunctionPropertySchema(type="string", minLength=1),
        "city": FunctionPropertySchema(type="string", minLength=1),
        "country": FunctionPropertySchema(type="string", minLength=2, maxLength=2), # ISO country code
    },
    required=["street", "city", "country"],
    additionalProperties=False  # No extra properties allowed
)
```

#### Enum and Constant Values

```python
# Enumerate allowed values
unit = FunctionPropertySchema(
    type="string",
    description="Temperature unit",
    enum=["celsius", "fahrenheit", "kelvin"]
)

# Constant value (must equal exactly)
api_version = FunctionPropertySchema(
    type="string",
    description="API version",
    const="v1.0"
)

# Default values
optional_note = FunctionPropertySchema(
    type="string",
    description="Optional note",
    default="No note provided"
)
```

#### Union Types

> **Note**: Union types in `FunctionPropertySchema` (manual schema definition) can accept multiple types using `type=["string", "number"]`, but this capability is **not available** through the `@simple_tool` decorator, which only supports `Optional[T]` patterns.

```python
# Accept multiple types (only available with manual schema definition)
flexible_input = FunctionPropertySchema(
    type=["string", "number"],  # Can be either string or number
    description="Flexible input parameter"
)
```

### Validation Rules

`FunctionPropertySchema` enforces strict type-specific validation rules:

1. **Object Type (`object`)**:
   - `properties` must be defined
   - `required` defaults to empty list if not provided
   - Array constraints (`items`, `minItems`, etc.) must be `None`
   - String/numeric constraints must be `None`

2. **Array Type (`array`)**:
   - `items` must be defined
   - `uniqueItems` defaults to `False` if not provided
   - String/numeric/object constraints must be `None`
   - `minItems` and `maxItems` must be non-negative, with `minItems <= maxItems`

3. **String Type (`string`)**:
   - `minLength` and `maxLength` must be non-negative, with `minLength <= maxLength`
   - Numeric/array/object constraints must be `None`

4. **Numeric Types (`number`/`integer`)**:
   - `minimum <= maximum` must hold
   - `multipleOf` must be positive
   - String/array/object constraints must be `None`

5. **Boolean Type (`boolean`)**:
   - All other constraint types must be `None`

These validation rules ensure that your tool schemas are well-formed and compatible with standard JSON Schema specifications.

## 3.4.4 FunctionDefinitionSchema Function Schema

The [FunctionDefinitionSchema](../api-reference/classes/FunctionDefinitionSchema.md) class defines the schema for function parameters:

```python
from amrita_core.tools.models import FunctionDefinitionSchema

schema = FunctionDefinitionSchema(
    name="get_time",
    description="Get the current time in a given timezone",
    parameters=...
)
```

## 3.4.5 ToolsManager Tool Manager

The [ToolsManager](../api-reference/classes/ToolsManager.md) class manages registered tools:

```python
from amrita_core.tools.manager import ToolsManager

manager = ToolsManager()
# Get available tools
registered_tools = manager.get_tools()
```

## 3.4.6 Dynamic Tool Discovery

Tools are automatically discovered and registered when modules are imported:

```python
# When you import modules containing @on_tools decorated functions
from . import my_tools  # Tools are automatically registered; make sure they are only imported once.
```
