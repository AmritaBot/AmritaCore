# EmbeddingChunk

## Overview

The `EmbeddingChunk` class represents a single embedding vector returned by an embedding adapter. It provides a standardized structure for embedding results that maintains compatibility with OpenAI's embedding response format while adding type safety.

## Class Definition

```python
class EmbeddingChunk(BaseModel):
    embedding: Sequence[float]
    index: int
```

## Attributes

### `embedding`

- **Type**: `Sequence[float]`
- **Description**: The embedding vector as a sequence of floating-point numbers. This represents the semantic representation of the input text in vector space.

### `index`

- **Type**: `int`
- **Description**: The original index of the corresponding text in the input sequence. This allows mapping embeddings back to their source texts when processing multiple inputs.

## Usage Example

```python
from amrita_core.types import EmbeddingChunk

# Create an embedding chunk
chunk = EmbeddingChunk(
    embedding=[0.1, -0.5, 0.8, 0.3],
    index=0
)

print(f"Vector: {chunk.embedding}")
print(f"Original index: {chunk.index}")

# When processing multiple texts
texts = ["Hello", "World"]
embeddings: list[EmbeddingChunk] = await call_completion(preset=embedding_preset, messages=texts)

for chunk in embeddings:
    print(f"Text '{texts[chunk.index]}' -> Embedding length: {len(chunk.embedding)}")
```

## Related Components

- [`ModelAdapter.call_embed()`](ModelAdapter.md#call_embed): Method that returns `EmbeddingChunk` instances
- [`ADAPTER_TYPE`](ADAPTER_TYPE.md): Enumeration that includes `"embed"` type
- [`call_completion()`](../functions/call_completion.md): Function that handles embedding adapter calls

## Version Information

- **Added in**: Version 0.8.0
- **Purpose**: Standardized embedding result format for type-safe embedding operations
