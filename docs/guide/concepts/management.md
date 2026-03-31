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
