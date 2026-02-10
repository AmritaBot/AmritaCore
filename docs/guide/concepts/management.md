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

## 3.2.5 TextContent Text Content

The [TextContent](../api-reference/classes/TextContent.md) class represents text content within messages:

```python
from amrita_core.types import TextContent

# Create text content
content = TextContent(text="This is the actual message text")
```

## 3.2.6 UniResponse Unified Response

The [UniResponse](../api-reference/classes/UniResponse.md) class provides a unified format for responses:

```python
from amrita_core.types import UniResponse

# Process a unified response
response = UniResponse(content="Response content", usage=...)
```

## 3.2.7 Conversation State Management

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

## 3.2.8 Session Isolation

Please see [Security Controls](../security-mechanisms.md) Chapter 6.3 for session isolation.
