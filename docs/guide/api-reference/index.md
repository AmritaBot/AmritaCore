# API Reference

## 7.1 Core API Functions

### 7.1.1 init() - Initialization

The `init()` function initializes AmritaCore's core components and must be called before any other operations.

```python
from amrita_core import init

# Initialize AmritaCore
init()
```

**Purpose**: Prepares the internal components of AmritaCore, initializes Jieba for text processing, loads built-in modules, and sets up the core framework.

**Usage Notes**:

- Must be called before any other AmritaCore functions
- Thread-safe and can be called multiple times (subsequent calls are no-ops)
- Sets up logging and internal state

### 7.1.2 load_amrita() - Loading Framework

The `load_amrita()` function asynchronously loads AmritaCore components, particularly when MCP client functionality is enabled.

```python
import asyncio
from amrita_core import load_amrita

async def main():
    await load_amrita()

asyncio.run(main())
```

**Purpose**: Loads additional AmritaCore components, especially MCP clients if configured.

**Usage Notes**:

- Must be called after `init()` and `set_config()`
- Should be awaited as it's an async function
- Only required when using MCP functionality

### 7.1.3 set_config() - Setting Configuration

The `set_config()` function applies a configuration to AmritaCore.

```python
from amrita_core.config import AmritaConfig, set_config

config = AmritaConfig()
set_config(config)
```

**Purpose**: Sets the active configuration for AmritaCore.

**Parameters**:

- `config` ([AmritaConfig](classes/AmritaConfig.md)): The configuration object to set

**Usage Notes**:

- Must be called after `init()` but before `load_amrita()`
- Configuration affects all subsequent operations

### 7.1.4 get_config() - Getting Configuration

The `get_config()` function retrieves the current AmritaCore configuration.

```python
from amrita_core.config import get_config

config = get_config()
print(config.function_config.use_minimal_context)
```

**Returns**: [AmritaConfig](classes/AmritaConfig.md) - The current configuration object

**Usage Notes**:

- Throws RuntimeError if AmritaCore is not initialized
- Safe to call after initialization

## 7.2 Classes and Interfaces Documentation

### 7.2.1 ChatObject - Conversation Object

The [ChatObject](classes/ChatObject.md) class is the primary interface for conversations with the AI.

```python
from amrita_core import ChatObject
from amrita_core.types import MemoryModel, Message

context = MemoryModel()
train = Message(content="You are a helpful assistant.", role="system")

chat = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump()
)
```

**Constructor Parameters**:

- `context` ([MemoryModel](classes/MemoryModel.md)): Memory context for the conversation
- `session_id` (str): Unique identifier for the session
- `user_input` (str): The user's input message
- `train` (dict): Training/prompt data for the AI

**Methods**:

- `call()`: Executes the conversation
- `get_response_generator()`: Returns an async generator for streaming responses
- `full_response()`: Returns the complete response

### 7.2.2 Message - Message Class

The [Message](classes/Message.md) class represents a single message in the conversation.

```python
from amrita_core.types import Message

# Create different types of messages
system_msg = Message(content="You are a helpful assistant.", role="system")
user_msg = Message(content="Hello, how are you?", role="user")
assistant_msg = Message(content="I'm doing well, thank you!", role="assistant")
```

**Constructor Parameters**:

- `content` (str): The message content
- `role` (str): The role of the message ('system', 'user', or 'assistant')

### 7.2.3 MemoryModel - Memory Model

The [MemoryModel](classes/MemoryModel.md) class stores conversation history and context.

```python
from amrita_core.types import MemoryModel, Message

memory = MemoryModel()
memory.messages.append(Message(content="Hello", role="user"))
memory.messages.append(Message(content="Hi there", role="assistant"))
```

**Properties**:

- `messages` (list): List of messages in the conversation

### 7.2.4 AmritaConfig - Configuration Class

The [AmritaConfig](classes/AmritaConfig.md) class is the central configuration object for AmritaCore.

```python
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig, CookieConfig

config = AmritaConfig(
    function_config=FunctionConfig(
        use_minimal_context=False,
        tool_calling_mode="agent"
    ),
    llm=LLMConfig(
        enable_memory_abstract=True
    ),
    cookie=CookieConfig(
        enable_cookie=True
    )
)
```

**Properties**:

- `function_config` ([FunctionConfig](classes/FunctionConfig.md)): Functional behavior configuration
- `llm` ([LLMConfig](classes/LLMConfig.md)): Language model configuration
- `cookie` ([CookieConfig](classes/CookieConfig.md)): Security configuration

## 7.3 Decorator References

### 7.3.1 @on_tools - Tool Registration

The `@on_tools` decorator registers functions as callable tools for the agent.

```python
from amrita_core.tools.manager import on_tools
from amrita_core.types import Function

schema = FunctionDefinitionSchema(
    name="get_time",
    description="Get the current time in a given timezone",
    parameters=...
)

@on_tools(
    data=schema,
    custom_run=True,
    enable_if=lambda: get_config().function_config.agent_middle_message,
)
async def get_weather(city: str) -> str:
    """Get the weather for a given city."""
    # Implementation here
    return f"Weather for {city}: Sunny"
```

**Purpose**: Registers a function as an available tool that the agent can call.

**Usage Notes**:

- Function must have proper type hints for parameters
- Function docstring becomes the tool description
- Registered tools are automatically available to the agent

### 7.3.2 @on_event - Event Listener

The `@on_event` decorator registers functions as event handlers.

```python
from amrita_core.hook.on import on_event

@on_event()
def my_event_handler(event):
    # Handle custom events
    pass
```

**Purpose**: Registers a function to handle specific events during the processing pipeline.

### 7.3.3 @on_precompletion - Pre-Completion Hook

The `@on_precompletion` decorator registers functions to run before the completion request is sent to the LLM.

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion()
async def preprocess_request(event: PreCompletionEvent):
    # Modify the messages before sending to LLM
    print(event)
```

**Purpose**: Runs before sending the request to the LLM, allowing modification of messages or other preprocessing.

### 7.3.4 @on_completion - Post-Completion Hook

The `@on_completion` decorator registers functions to run after receiving the completion from the LLM.

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion()
async def postprocess_response(event: CompletionEvent):
    # Process the response after receiving from LLM
    print(event)
```

**Purpose**: Runs after receiving the response from the LLM, allowing post-processing of the response.

## 7.4 Type Definitions and Exceptions

### 7.4.1 Predefined Types

AmritaCore provides several predefined types for consistency:

- [BaseModel](classes/BaseModel.md): Base class for all data models
- [Function](classes/Function.md): Represents a callable function in the tool system
- [FunctionDefinitionSchema](classes/FunctionDefinitionSchema.md): Schema for function parameters
- [MemoryModel](classes/MemoryModel.md): Stores conversation history
- [ModelConfig](classes/ModelConfig.md): Model-specific configuration
- [ModelPreset](classes/ModelPreset.md): Complete configuration for a specific model
- [TextContent](classes/TextContent.md): Represents text content within messages
- [ToolCall](classes/ToolCall.md): Represents an invocation of a tool
- [ToolContext](classes/ToolContext.md): Provides context for tool execution
- [ToolResult](classes/ToolResult.md): Represents the result of a tool invocation
- [ToolsManager](classes/ToolsManager.md): Manages registered tools
- [UniResponse](classes/UniResponse.md): Unified format for responses
- [UniResponseUsage](classes/UniResponseUsage.md): Usage statistics for responses

### 7.4.2 Exception Types

AmritaCore may raise the following exceptions:

- `RuntimeError`: Raised when accessing configuration before initialization
- `ValueError`: Raised when invalid values are provided to functions
- `TypeError`: Raised when incorrect types are passed to functions

### 7.4.3 Type Checking

AmritaCore uses Pydantic models extensively for type validation. When creating custom components, ensure proper type annotations:

```python
from typing import Optional
from amrita_core.types import BaseModel

class CustomConfig(BaseModel):
    param1: str
    param2: Optional[int] = None
    param3: list[str] = []
```

This API reference provides a comprehensive overview of the core AmritaCore interfaces, classes, and decorators. Each component is designed to work together to provide a flexible and powerful framework for building AI agents.
