# ModelAdapter

`ModelAdapter` is a dataclass that serves as the base class for model protocol adapters in AmritaCore.

## Overview

The `ModelAdapter` class provides a unified interface for integrating different AI model providers (such as OpenAI, Anthropic, etc.) into the AmritaCore framework. Adapters handle the communication with external APIs, process responses, and convert them into a standardized format that the framework can use.

Adapters are automatically registered with the [`AdapterManager`](#adaptermanager) when defined, unless marked as abstract or explicitly disabled from registration.

> **Note**: The `ModelAdapter` base class has been moved from `amrita_core.protocol` to `amrita_core.base.adapter`. The `amrita_core.protocol` compatibility endpoint was removed in v0.10.x+; import from `amrita_core.base.adapter`.

## Class Definition

```python
from dataclasses import dataclass, field
from amrita_core.base.adapter import ModelAdapter
from amrita_core.types import ModelPreset
from amrita_core.config import AmritaConfig

@dataclass
class ModelAdapter:
    preset: ModelPreset
    config: AmritaConfig = field(default_factory=get_config)
    __override__: bool = False
```

## Attributes

### `preset`

- **Type**: [`ModelPreset`](ModelPreset.md)
- **Description**: The model preset configuration containing model name, API key, base URL, and other settings.

### `config`

- **Type**: [`AmritaConfig`](AmritaConfig.md)
- **Description**: Global configuration for the adapter, including timeout settings, retry policies, and token limits.
- **Default**: Obtained from `get_config()` function.

### `__override__`

- **Type**: `bool`
- **Description**: Whether to allow overriding existing adapters with the same protocol. Set to `True` to replace an already registered adapter.
- **Default**: `False`

## Methods

### get*adapter_protocol()*(Abstract)

Get the protocol identifier(s) for this adapter.

This is an abstract static method that **must** be implemented by all concrete adapter subclasses. It returns the protocol name(s) that this adapter supports.

**Returns**: `str | tuple[str, ...]` - A single protocol string or a tuple of multiple protocol strings.

**Example**:

```python
class MyAdapter(ModelAdapter):
    @staticmethod
    def get_adapter_protocol() -> str:
        return "my-custom-protocol"

# Or support multiple protocols
class MultiProtocolAdapter(ModelAdapter):
    @staticmethod
    def get_adapter_protocol() -> tuple[str, str]:
        return ("openai", "azure-openai")
```

### get_type()

Get the adapter type indicating its primary functionality.

**Returns**: `ADAPTER_TYPE | tuple[ADAPTER_TYPE, ...]` - The adapter type, which can be:

- `"text-gen"`: Text generation/completion (default)
- `"embed"`: Embedding vector generation
- `"rerank"`: Reranking (planned for future)

**Default**: `"text-gen"`

**Example**:

```python
class EmbeddingAdapter(ModelAdapter):
    @staticmethod
    def get_type() -> str:
        return "embed"
```

### call_api()

Call the model API to generate text completions.

This method should be overridden to implement the actual API call logic for text generation. It yields response chunks as they arrive, supporting both streaming and non-streaming modes.

**Parameters**:

- `messages` (`Iterable`): List of messages to send to the model
- `**kwargs`: Additional keyword arguments

**Returns**: `AsyncGenerator[COMPLETION_RETURNING, None]` - An async generator yielding:

- `str`: Text chunks (in streaming mode)
- [`MessageContent`](../protocol.md#messagecontent): Custom message content objects
- [`UniResponse`](UniResponse.md): Final response with complete content and usage information

**Raises**: `NotImplementedError` - If not implemented by subclass

**Example**:

```python
async def call_api(self, messages: Iterable, **kwargs):
    # Implement your API call logic
    async for chunk in self._stream_response(messages):
        yield chunk

    # Yield final response
    yield UniResponse(content=full_response, usage=usage_info)
```

### call_tools()

Execute tool calls using the model's function calling capability.

This method sends messages to the model with available tools and retrieves the model's tool call decisions.

**Parameters**:

- `messages` (`Iterable`): List of messages to send to the model
- `tools` (`list[ToolFunctionSchema]`): List of available tool schemas
- `tool_choice` ([`ToolChoice`](../models.md#toolchoice) | `None`, optional): How the model should select tools. Defaults to `None` (auto selection).

**Returns**: [`UniResponse`](UniResponse.md)`[None, list[`[ToolCall`](ToolCall.md)`] | None]` - Response containing the model's tool call decisions.

**Raises**: `NotImplementedError` - If not implemented by subclass

**Example**:

```python
async def call_tools(self, messages, tools, tool_choice=None):
    # Call model with tools
    response = await self.client.chat.completions.create(
        model=self.preset.model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice or "auto"
    )

    # Extract tool calls
    tool_calls = [
        ToolCall.model_validate(tc)
        for tc in response.choices[0].message.tool_calls
    ]

    return UniResponse(tool_calls=tool_calls, content=None)
```

### call_embed()

Generate embedding vectors for input texts.

This method should be overridden by embedding adapters to implement embedding generation logic.

**Parameters**:

- `texts` (`Iterable[str]`): List of texts to generate embeddings for
- `**kwargs`: Additional keyword arguments

**Returns**: `Sequence[EmbeddingChunk]` - Sequence of embedding chunks, each containing an embedding vector and its original index.

**Raises**: `NotImplementedError` - If not implemented by subclass

**Example**:

```python
async def call_embed(self, texts: Iterable[str], **kwargs):
    embeddings = []
    for idx, text in enumerate(texts):
        # Generate embedding vector
        vector = await self._generate_embedding(text)
        embeddings.append(
            EmbeddingChunk(embedding=vector, index=idx)
        )
    return embeddings
```

### protocol _(Property)_

Get the model protocol adapter identifier.

**Returns**: `str | tuple[str, ...]` - The protocol identifier(s) from `get_adapter_protocol()`.

## Automatic Registration

Adapters are automatically registered with the [`AdapterManager`](#adaptermanager) when the class is defined, unless:

1. The class has `__abstract__ = True` attribute
2. The class has `__no_register__ = True` attribute

**Example**:

```python
# This adapter will be automatically registered
class MyAdapter(ModelAdapter):
    @staticmethod
    def get_adapter_protocol() -> str:
        return "my-protocol"

# This adapter will NOT be automatically registered
class AbstractBaseAdapter(ModelAdapter):
    __abstract__ = True

    @staticmethod
    def get_adapter_protocol() -> str:
        return "abstract"
```

## Built-in Adapters

AmritaCore provides several built-in adapters:

### OpenAIAdapter

- **Protocols**: `"openai"`, `"__main__"`
- **Location**: `amrita_core.builtins.adapter.OpenAIAdapter`
- **Features**:
  - Supports both streaming and non-streaming modes
  - Implements tool calling via OpenAI's function calling API
  - Compatible with any OpenAI-compatible API endpoint

### AnthropicAdapter

- **Protocols**: `"anthropic"`, `"claude"`
- **Location**: `amrita_core.builtins.adapter.AnthropicAdapter`
- **Features**:
  - Supports streaming responses
  - Full tool calling support via Anthropic's tool use API
  - Optimized for Claude models with proper message format handling

## Creating Custom Adapters

To create a custom adapter:

1. Inherit from `ModelAdapter`
2. Implement `get_adapter_protocol()` (required)
3. Override `call_api()` for text generation
4. Optionally override `call_tools()` for tool calling
5. Optionally override `call_embed()` for embedding generation
6. Optionally override `get_type()` if not a text-generation adapter

**Complete Example**:

```python
from collections.abc import AsyncGenerator, Iterable
from amrita_core.base.adapter import ModelAdapter, COMPLETION_RETURNING
from amrita_core.types import ModelPreset, UniResponse, UniResponseUsage

class CustomAdapter(ModelAdapter):
    """Custom model adapter example"""

    @staticmethod
    def get_adapter_protocol() -> str:
        return "custom-api"

    async def call_api(
        self,
        messages: Iterable,
        **kwargs
    ) -> AsyncGenerator[COMPLETION_RETURNING, None]:
        # Your custom API logic here
        response_text = ""

        # Process messages and call your API
        async for chunk in self._fetch_chunks(messages):
            response_text += chunk
            yield chunk

        # Return final response
        yield UniResponse(
            content=response_text,
            usage=UniResponseUsage(
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150
            )
        )
```

## Related Components

- [`AdapterManager`](#adaptermanager): Manages adapter registration and retrieval
- [`ModelPreset`](ModelPreset.md): Configuration preset for adapters
- [`AmritaConfig`](AmritaConfig.md): Global configuration used by adapters
- [`UniResponse`](UniResponse.md): Standardized response format
- [`EmbeddingChunk`](EmbeddingChunk.md): Embedding result structure
- [`ToolCall`](ToolCall.md): Tool call representation
- [`OpenAIAdapter`](#built-in-adapters): Built-in OpenAI adapter implementation
- [`AnthropicAdapter`](#built-in-adapters): Built-in Anthropic adapter implementation

## AdapterManager

The `AdapterManager` class manages the registration and retrieval of model adapters.

### Method

#### get_adapters()

Get all registered adapters.

**Returns**: `dict[str, type[ModelAdapter]]` - Dictionary mapping protocol names to adapter classes.

#### safe_get_adapter(protocol)

Safely get an adapter by protocol name.

**Parameters**:

- `protocol` (`str`): The protocol identifier

**Returns**: `type[ModelAdapter] | None` - The adapter class if found, `None` otherwise.

#### get_adapter(protocol)

Get an adapter by protocol name.

**Parameters**:

- `protocol` (`str`): The protocol identifier

**Returns**: `type[ModelAdapter]` - The adapter class.

**Raises**: `ValueError` - If no adapter is found for the given protocol.

#### register_adapter(adapter)

Register an adapter class.

**Parameters**:

- `adapter` (`type[ModelAdapter]`): The adapter class to register.

**Raises**:

- `ValueError` - If an adapter with the same protocol is already registered and `__override__` is `False`.
- `TypeError` - If protocol is not a string or tuple of strings.
