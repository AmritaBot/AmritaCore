# Data Types and Conversation Management

## 3.2.1 Message Message Type

The [Message](../api-reference/classes/Message.md) class represents a single message in the conversation:

```python
from amrita_core.types import Message

# Create a system message
system_msg = Message(content="You are a helpful assistant.", role="system")

# Create a user message
user_msg = Message(content="Hello, how are you?", role="user")

# Create an assistant message
assistant_msg = Message(content="I'm doing well, thank you!", role="assistant")
```

## 3.2.2 MemoryModel Memory Model

The [MemoryModel](../api-reference/classes/MemoryModel.md) class stores conversation history and context:

```python
from amrita_core.types import MemoryModel

# Create a new memory context
memory = MemoryModel()

# Add messages to memory
memory.messages.append(system_msg)
memory.messages.append(user_msg)
memory.messages.append(assistant_msg)
```

## 3.2.3 ModelConfig Model Configuration

The [ModelConfig](../api-reference/classes/ModelConfig.md) class holds model-specific settings:

```python
from amrita_core.types import ModelConfig

# Configure streaming and other model options
model_config = ModelConfig(stream=True)
```

## 3.2.4 ModelPreset Model Presets

The [ModelPreset](../api-reference/classes/ModelPreset.md) class defines a complete configuration for a specific model:

```python
from amrita_core.types import ModelPreset

# Define a model preset
preset = ModelPreset(
    model="gpt-3.5-turbo",
    base_url="https://api.openai.com/v1",
    api_key="your-api-key",
    config=ModelConfig(stream=True)
)
```

## 3.2.5 PresetManager Preset Management (Recommended Practice)

**The recommended approach is to use [PresetManager](../api-reference/classes/PresetManager.md) to manage all your presets.** PresetManager provides centralized management, validation, and automatic fallback mechanisms.

### Why Use PresetManager?

1. **Centralized Management**: All presets stored in one place
2. **Automatic Fallback**: If no preset is selected, automatically uses a default preset
3. **Validation**: Prevents duplicate names and validates configurations
4. **Testing**: Built-in testing to verify preset functionality
5. **Singleton Pattern**: Ensures consistent state across your application

### Basic Usage

```python
from amrita_core.preset import PresetManager
from amrita_core.types import ModelPreset, ModelConfig

# Initialize manager (singleton)
manager = PresetManager()

# Add presets
manager.add_preset(ModelPreset(
    model="gpt-3.5-turbo",
    name="fast",
    api_key="sk-xxx",
    config=ModelConfig(stream=True)
))

manager.add_preset(ModelPreset(
    model="gpt-4",
    name="smart",
    api_key="sk-xxx"
))

# Set default preset (optional but recommended)
manager.set_default_preset("fast")

# Get preset - will auto-fallback to default if not specified
preset = manager.get_preset("smart")  # Specific preset
default = manager.get_default_preset()  # Default preset (auto-fallback)
```

### Automatic Fallback Behavior

When you call `get_default_preset()` without setting a default:

- If a default was set via `set_default_preset()`, returns that preset
- If **no default was set**, automatically selects a random preset from available presets
- This ensures your application never fails due to missing preset configuration

```python
manager = PresetManager()
manager.add_preset(preset1)
manager.add_preset(preset2)

# No default set - will auto-fallback to random preset
default = manager.get_default_preset()  # Returns either preset1 or preset2
```

For complete API reference, see [PresetManager](../api-reference/classes/PresetManager.md).

## 3.2.6 TextContent Text Content

The [TextContent](../api-reference/classes/TextContent.md) class represents text content within messages:

```python
from amrita_core.types import TextContent

# Create text content
content = TextContent(text="This is the actual message text")
```

## 3.2.7 UniResponse Unified Response

The [UniResponse](../api-reference/classes/UniResponse.md) class provides a unified format for responses:

```python
from amrita_core.types import UniResponse

# Process a unified response
response = UniResponse(content="Response content", usage=...)
```

## 3.2.8 Conversation State Management

Conversation state is managed through the MemoryModel and ChatObject classes:

```python
# Create a new conversation context
context = MemoryModel()

# Add initial system message
train = Message(content="You are a helpful assistant.", role="system")

# Create a ChatObject for interaction
chat = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump()
)

# Process the interaction
async with chat.begin():
    ...

# Update context with the new state
updated_context = chat.data
```

## 3.2.9 Session Isolation

Please see [Security Controls](../security-mechanisms.md) Chapter 6.3 for session isolation.

## 3.2.10 Embedding Support

AmritaCore provides built-in support for embedding generation through the adapter system.

### Adapter Types

AmritaCore adapters support multiple types through the `ADAPTER_TYPE` type definition:

- **`"text-gen"`**: Traditional text generation/completion (default)
- **`"embed"`**: Embedding vector generation
- **`"rerank"`**: Reranking functionality (planned for future versions)

### Embedding Adapter Implementation

To create an embedding adapter, extend `ModelAdapter` and implement the required methods:

```python
from collections.abc import Iterable, Sequence
from amrita_core.protocol import ModelAdapter
from amrita_core.types import EmbeddingChunk, ModelPreset

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

**Note**:
- `get_adapter_protocol()` is a required abstract method that returns the adapter protocol name
- `get_type()` returns the adapter type, defaulting to `"text-gen"`, embedding adapters should return `"embed"`
- `call_embed()` method receives a list of texts and returns a sequence of `EmbeddingChunk` objects

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

The `EmbeddingChunk` class represents a single embedding result:

```python
from amrita_core.types import EmbeddingChunk

# EmbeddingChunk contains two fields:
# - embedding: Sequence[float] - The embedding vector as a sequence of floats
# - index: int - The original index of the text in the input sequence
```

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
