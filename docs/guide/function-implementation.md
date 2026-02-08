# Function Implementation

## 4.1 Initialization and Loading

### 4.1.1 init() Initialization Function

The `init()` function initializes AmritaCore's core components and must be called before any other operations:

```python
from amrita_core import init

# Initialize AmritaCore
init()
```

This function performs several key tasks:

- Sets up internal logging
- Initializes Jieba for text processing (if available)
- Loads built-in modules
- Prepares the core framework for use

### 4.1.2 load_amrita() Asynchronous Loading

The `load_amrita()` function asynchronously loads AmritaCore components, especially when MCP client functionality is enabled:

```python
import asyncio
from amrita_core import load_amrita

async def main():
    # Load AmritaCore components
    await load_amrita()

asyncio.run(main())
```

### 4.1.3 Configuration Setting and Retrieval

#### 4.1.3.1 set_config() Setting Configuration

The `set_config()` function applies a configuration to AmritaCore:

```python
from amrita_core.config import AmritaConfig, set_config

# Create and set a configuration
config = AmritaConfig()
set_config(config)
```

#### 4.1.3.2 get_config() Retrieving Configuration

The `get_config()` function retrieves the current AmritaCore configuration:

```python
from amrita_core.config import get_config

# Retrieve current configuration
current_config = get_config()
print(current_config.function_config.use_minimal_context)
```

### 4.1.4 Initialization Process Details

The initialization process involves:

1. Calling `init()` to prepare the core components
2. Setting the desired configuration with `set_config()`
3. Loading additional components with `load_amrita()`

```python
from amrita_core import init, load_amrita
from amrita_core.config import AmritaConfig, set_config

# Step 1: Initialize core components
init()

# Step 2: Set configuration
config = AmritaConfig()
set_config(config)

# Step 3: Load additional components
import asyncio
asyncio.run(load_amrita())
```

## 4.2 Conversation Interaction Flow

### 4.2.1 Creating ChatObject Conversation Objects

The [ChatObject](../api-reference/classes/ChatObject.md) class is the primary interface for conversations:

```python
from amrita_core import ChatObject
from amrita_core.types import MemoryModel, Message

# Create a memory context
context = MemoryModel()

# Create a system message
train = Message(content="You are a helpful assistant.", role="system")

# Create a ChatObject
chat = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello, how are you?",
    train=train.model_dump()
)
```

### 4.2.2 begin() Executing Conversations

#### Basic Usage

The `begin()` method executes the conversation and processes the input:

```python
# Execute the conversation
await chat.begin()

```

#### Use as Context Manager(Recommended)

```python

# We prefer to use context manager as this:
async with chat.begin():
    ...

```

### 4.2.3 full_response() Obtaining Complete Response

The `full_response()` method retrieves the complete response from the conversation:

```python
# Get the full response
response = await chat.full_response()
print(response)
```

### 4.2.4 Streaming Response Processing

AmritaCore supports streaming responses for real-time interaction:

```python
# Process streaming responses
async for message in chat.get_response_generator():
    content = message if isinstance(message, str) else message.get_content()
    print(content, end="")
```

### 4.2.5 Response Callback

AmritaCore supports response callbacks for real-time interaction:

```python
async def response_callback(message):
    print(message)

chat.set_callback_func(response_callback)
await chat.begin()
```

::: warning

The `get_response_generator()` or `full_response()` is a one-time operation. That means that you can only call `full_response()` or `get_response_generator()` once, or it will raise a `RuntimeError`.

:::

### 4.2.5 Conversation Lifecycle

The typical conversation lifecycle includes:

1. Creating a memory context
2. Defining system instructions
3. Creating a ChatObject
4. Executing the conversation
5. Processing responses
6. Updating the context for subsequent interactions

```python
# Complete conversation lifecycle
context = MemoryModel()
train = Message(content="You are a helpful assistant.", role="system")

async with ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump()
).begin() as chat:
    async for message in chat.get_response_generator():
        print(message, end="")

# Update context for next interaction
context = chat.data
```

## 4.3 Event Processing Implementation

### 4.3.1 @on_event Event Listeners

Event listeners are created using the `@on_event` decorator:

```python
from amrita_core.hook.on import on_event

@on_event()
def my_event_handler(event):
    print(f"Event received: {event}")

```

### 4.3.2 @on_precompletion Pre-Completion Hooks

Pre-completion hooks are executed before sending the request to the LLM:

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion()
async def preprocess_request(event: PreCompletionEvent):
    # Modify the messages before sending to LLM
    event.messages.append(Message(role="system", content="Be concise in your response"))

```

### 4.3.3 @on_completion Post-Completion Hooks

Post-completion hooks are executed after receiving the response from the LLM:

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion()
async def postprocess_response(event: CompletionEvent):
    # Process the response before returning to user
    print(f"Response received: {event.response[:50]}...")

```

### 4.3.4 Event Processing Best Practices

- Use pre-completion hooks to modify messages before LLM processing
- Use post-completion hooks to process or log responses
- Ensure event handlers are async when performing async operations
- Return the event object from handlers to continue the chain

## 4.4 Tool Calling Implementation

### 4.4.1 Tool Registration Example

Registering tools for use by the agent:

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

# First define the function schema
weather_func = FunctionDefinitionSchema(
    name="get_current_weather",
    description="Get the current weather in a given location",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "location": FunctionPropertySchema(
                type="string",
                description="The city and state, e.g. San Francisco, CA"
            ),
            "unit": FunctionPropertySchema(
                type="string",
                enum=["celsius", "fahrenheit"],
                description="The unit of temperature"
            )
        },
        required=["location"]
    )
)

@on_tools(data=weather_func)
async def get_current_weather(data: dict) -> str:
    """
    Get the current weather in a given location
    """
    location = data["location"]
    unit = data.get("unit", "celsius")  # Default to celsius if not provided

    # Simulate weather lookup
    return f"The weather in {location} is sunny, temperature is 22 degrees {unit}."
```

### 4.4.2 Tool Execution Flow

The tool execution flow includes:

1. Tool detection in LLM response
2. Parameter extraction
3. Tool execution
4. Result incorporation into conversation

### 4.4.3 Error Handling

Proper error handling in tool implementations:

```python
from typing import Any
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

# Define the function schema
divide_func = FunctionDefinitionSchema(
    name="safe_divide",
    description="Safely divide two numbers",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "dividend": FunctionPropertySchema(
                type="number",
                description="The dividend in division"
            ),
            "divisor": FunctionPropertySchema(
                type="number",
                description="The divisor in division"
            )
        },
        required=["dividend", "divisor"]
    )
)

@on_tools(data=divide_func)
async def safe_divide(data: dict) -> str:
    """
    Safely divide two numbers
    """
    try:
        dividend = data["dividend"]
        divisor = data["divisor"]

        if divisor == 0:
            return "Error: Cannot divide by zero"

        result = dividend / divisor
        return f"{dividend} divided by {divisor} equals {result}"
    except Exception as e:
        return f"Error occurred: {str(e)}"
```

### 4.4.4 Custom Run Mode

Some tools may need access to the event context or require more advanced processing. For this, the `custom_run` option can be enabled:

````python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema, ToolContext
from amrita_core.logging import logger

# Define the function schema
process_message_tool = FunctionDefinitionSchema(
    name="processing_message",
    description="Describe what the agent is currently doing and express the agent's internal thoughts to the user",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "content": FunctionPropertySchema(
                type="string",
                description="Message content describing current actions"
            )
        },
        required=["content"]
    )
)

@on_tools(data=process_message_tool, custom_run=True)
async def process_message(ctx: ToolContext) -> str | None:
    """
    Process a message and send it to the user via the chat object
    """
    content = ctx.data["content"]
    logger.debug(f"[LLM-ProcessMessage] {content}")

    # Send message directly to the chat object
    await ctx.event.chat_object.yield_response(f"{content}\n")

    # Return processed result
    return f"Sent a message to user:\n\n```text\n{content}\n```\n"
````

In custom run mode:

- The function receives a [ToolContext](../api-reference/classes/ToolContext.md) object instead of raw arguments
- The [ToolContext](../api-reference/classes/ToolContext.md) contains:
  - `ctx.data`: The arguments passed to the tool
  - `ctx.event`: The current event, allowing access to chat object
  - `ctx.matcher`: The matcher associated with the event
- Functions can be synchronous or asynchronous
- Return type can be `str` or `None`

## 4.5 Memory Management

### 4.5.1 MemoryModel Memory Structure

The [MemoryModel](../api-reference/classes/MemoryModel.md) class structure:

```python
from amrita_core.types import MemoryModel, Message

# Create and use memory model
memory = MemoryModel()
memory.messages.append(Message(role="user", content="Hello"))
memory.messages.append(Message(role="assistant", content="Hi there!"))
```

### 4.5.2 Context Window Management

Managing the context window with configuration:

```python
from amrita_core.config import LLMConfig

# Limit the number of messages in memory
llm_config = LLMConfig(
    memory_length_limit=50  # Only keep last 50 messages
)
```

### 4.5.3 Message Summary Function

Automatic message summarization:

```python
from amrita_core.config import LLMConfig

# Enable memory summarization
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # Summarize at 15% of context length
)
```

### 4.5.4 Long Conversation Handling

Handling long conversations efficiently:

```python
from amrita_core.config import FunctionConfig, LLMConfig, AmritaConfig

# Configuration for long conversations
long_convo_config = AmritaConfig(
    function_config=FunctionConfig(
        use_minimal_context=True  # Use minimal context to save tokens
    ),
    llm=LLMConfig(
        enable_memory_abstract=True,  # Enable summarization
        memory_length_limit=100       # Increase memory limit
    )
)
```

### 4.5.5 Memory Optimization Techniques

- Use minimal context when appropriate
- Enable memory summarization for long-running sessions
- Implement session cleanup strategies
- Monitor token usage regularly

## 4.6 Logging and Debugging

### 4.6.1 Logger Logging System

Using the built-in logger:

```python
from amrita_core.logging import logger

# Log informational messages
logger.info("Starting conversation...")

# Log debug information
logger.debug("Processing message: %s", user_input)

# Log errors
logger.error("Failed to process request: %s", error)
```

### 4.6.2 @debug_log Debug Logging

The `@debug_log` decorator is deprecated in favor of the standard logger:

```python
# Use logger instead of @debug_log
from amrita_core.logging import logger

def my_function(param):
    logger.debug(f"Processing parameter: {param}")
    # Function implementation
```

### 4.6.3 get_last_response() Getting Last Response

Retrieve the last response from a conversation:

```python
from amrita_core.libchat import get_last_response

# Get the last response
last_resp = get_last_response(chat_object)
print(last_resp)
```

### 4.6.4 get_tokens() Getting Token Usage

Monitor token usage:

```python
from amrita_core.libchat import get_tokens

# Get token count
tokens_used = get_tokens()
print(f"Tokens used: {tokens_used}")
```

### 4.6.5 Debugging Tips

- Enable debug logging during development
- Monitor token usage to prevent exceeding limits
- Use streaming responses for real-time feedback
- Implement proper error handling for robust applications
