# Tool System

## 3.4.1 Tool Integration Framework

AmritaCore provides a comprehensive framework for integrating external tools and services. Tools can be registered and made available to the agent for use during conversations.

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

The `@simple_tool` decorator registers functions as simple tools.

Args in the function signature are considered arguments to the function.Their types are inferred from the type annotations, and their descriptions are inferred from the docstring which should be written as **Google's Python Docstring format**.

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

```python
# Accept multiple types
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

## 3.4.4 Embedding Support

AmritaCore provides built-in support for embedding generation through the adapter system.

### Adapter Types

AmritaCore adapters now support multiple types through the [`ADAPTER_TYPE`](../api-reference/classes/ADAPTER_TYPE.md) enumeration:

- **`"text-gen"`**: Traditional text generation/completion (default)
- **`"embed"`**: Embedding vector generation
- **`"rerank"`**: Reranking functionality (planned for future versions)

### Embedding Adapter Implementation

To create an embedding adapter, extend [`ModelAdapter`](../api-reference/classes/ModelAdapter.md) and implement the required methods:

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
        """Generate embeddings for the given texts"""
        embeddings = []
        for idx, text in enumerate(texts):
            # Your embedding logic here
            embedding_vector = self._generate_embedding(text)
            embeddings.append(
                EmbeddingChunk(embedding=embedding_vector, index=idx)
            )
        return embeddings

    def _generate_embedding(self, text: str) -> list[float]:
        # Implement your embedding generation logic
        pass
```

### Using Embedding Adapters

Embedding adapters can be used through the standard preset system:

```python
from amrita_core.preset import PresetManager, ModelPreset
from amrita_core.libchat import call_completion

# Create a preset for your embedding adapter
preset = ModelPreset(
    protocol="my-embedding-protocol",
    model="embedding-model-v1",
    # ... other configuration
)

# Register the preset
PresetManager().register_preset("embedding-preset", preset)

# Use the embedding adapter
texts = ["Hello world", "How are you?"]
embeddings = await call_completion(preset=preset, messages=texts)
```

**Note**: The `call_completion` function automatically detects the adapter type and calls the appropriate method (`call_api` for `"text-gen"` or `call_embed` for `"embed"`).

### EmbeddingChunk Structure

The [`EmbeddingChunk`](../api-reference/classes/EmbeddingChunk.md) class represents a single embedding result:

- **`embedding`**: `Sequence[float]` - The embedding vector as a sequence of floats
- **`index`**: `int` - The original index of the text in the input sequence

This structure maintains compatibility with OpenAI's embedding response format while providing type safety.

### Type Safety and Validation

AmritaCore includes automatic type validation for adapter usage:

```python
# This will raise a RuntimeError if the adapter doesn't support "text-gen"
response = await call_completion(preset=text_gen_preset, messages=["Hello"])

# This will work correctly with embedding adapters
embeddings = await call_completion(preset=embedding_preset, messages=["Hello"])
```

The framework validates that the adapter type matches the intended usage, preventing accidental misuse of embedding adapters for text generation and vice versa.
