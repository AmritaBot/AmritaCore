# Function Implementation

## 4.1 Initialization and Loading

### 4.1.1 load_amrita() Asynchronous Loading

The `load_amrita()` function asynchronously loads AmritaCore components, especially when MCP client functionality is enabled:

```python
import asyncio
from amrita_core import load_amrita

async def main():
    # Load AmritaCore components
    await load_amrita()

asyncio.run(main())
```

### 4.1.2 Configuration Setting and Retrieval

#### 4.1.2.1 set_config() Setting Configuration

The `set_config()` function applies a configuration to AmritaCore:

```python
from amrita_core.config import AmritaConfig, set_config

# Create and set a configuration
config = AmritaConfig()
set_config(config)
```

#### 4.1.2.2 get_config() Retrieving Configuration

The `get_config()` function retrieves the current AmritaCore configuration:

```python
from amrita_core.config import get_config

# Retrieve current configuration
current_config = get_config()
print(current_config.function_config.use_minimal_context)
```

### 4.1.4 Initialization Process Details

Since v0.9.0rc1, the initialization process has been simplified:

1. _(Optional)_ Set the desired configuration with `set_config()`
2. Load additional components with `load_amrita()` (required when MCP is enabled)

```python
from amrita_core import load_amrita
from amrita_core.config import AmritaConfig, set_config

# Step 1: (Optional) Set configuration
config = AmritaConfig()
set_config(config)

# Step 3: Load additional components
import asyncio
asyncio.run(load_amrita())
```

## 4.2 Agent Strategy Lifecycle Methods

Agent strategies in AmritaCore implement several lifecycle methods that are called at different points during execution.

### 4.2.1 on_post_process() Post-Process Hook

The `on_post_process()` method is a **post-execution hook** that is called after all agent steps complete successfully. This hook is invoked for **all strategy categories** (`"agent"`, `"rag"`, `"workflow"`, `"agent-mixed"`).

**Purpose**: This hook allows strategies to perform final context modifications, add completion instructions, or perform cleanup operations before the final response is generated.

**Usage Example**:

```python
async def on_post_process(self) -> None:
    """Called after successful agent execution"""
    if self.call_count >= 2:  # Only if tools were actually called
        self.ctx.message.append(
            Message(
                role="user",
                content="<END_OF_PROCESS>\nPlease answer me directly based on the information we got before.\n<END_OF_PROCESS>"
            )
        )
```

**Key Characteristics**:

- Called only on successful execution (no exceptions occurred)
- Available for **all strategy categories**
- Can modify the conversation context before final completion
- Useful for adding final instructions or context summarization

### 4.2.2 Other Lifecycle Methods

- **`run()`**: Main execution method for `"workflow"` and `"rag"` categories
- **`single_execute()`**: Single-step execution method for `"agent"` and `"agent-mixed"` categories
- **`on_exception(exc: BaseException)`**: Called when an exception occurs during execution. The default implementation does nothing (passes silently) instead of raising `NoExceptionHandler`. Custom strategies should override this method to implement specific error handling logic.

#### Exception Handling Best Practices

The default `on_exception()` method in [AgentStrategy](../api-reference/classes/AgentStrategy.md) no longer raises exceptions by default. This change provides more flexibility for custom error handling:

```python
from amrita_core.agent.strategy import AgentStrategy

class CustomAgentStrategy(AgentStrategy):
    async def on_exception(self, exc: BaseException) -> None:
        """Custom exception handling logic"""
        # Log the exception
        logger.error(f"Agent execution failed: {exc}")

        # Optionally re-raise specific exceptions
        if isinstance(exc, ValueError):
            raise exc

        # Or handle gracefully and continue
        self.ctx.message.append(
            Message(
                role="user",
                content="An error occurred during processing. Please try again."
            )
        )
```

**Important Notes**:

- The default behavior is now **silent failure handling** - exceptions are caught but not re-raised
- Custom strategies should implement their own error handling logic in `on_exception()`
- If you need the old behavior (re-raising exceptions), explicitly call `raise exc` in your custom implementation
- This change improves robustness for production environments where graceful error handling is preferred

## 4.3 Conversation Interaction Flow

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

#### Using Pre-composed Workflows (v0.12.6+)

You can pass a pre-composed workflow to replace the default pipeline:

```python
from amrita_core import ChatObject
from amrita_core.builtins.workflows import SIMPLE_REACT, SIMPLE_CHAT

# Full ReAct agent pipeline
chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Search for the latest AI news.",
    session_id="session_123",
    workflow=SIMPLE_REACT,
)

# Plain chat — no agent, no tool calling
chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Hello!",
    session_id="session_456",
    workflow=SIMPLE_CHAT,
)
```

> See [`builtins.workflows`](../guide/builtins#_9-6-built-in-workflows-v0-12-6) for all available workflows.

### 4.2.2 begin() Executing Conversations

#### Basic Usage

The `begin()` method executes the conversation and processes the input:

```python
# Execute the conversation (this is recommended when you are using a callback function)
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

AmritaCore uses **AnyIO memory object streams** for streaming responses, which provides built-in backpressure handling:

```python
# Process streaming responses
async for message in chat.io_stream.get_response_generator():
    content = message if isinstance(message, str) else message.get_content()
    print(content, end="")
```

**Backpressure Mechanism Changes**:

- Uses single AnyIO memory object stream with automatic backpressure

The `_put_to_queue()` method now uses AnyIO's `send()` method with timeout:

```python
await asyncio.wait_for(self._send_stream.send(item), timeout=self._q_tout)
```

When the buffer is full, the producer automatically waits until space becomes available, eliminating the need for complex overflow logic.

### 4.2.5 Response Callback

AmritaCore supports response callbacks for real-time interaction:

```python
async def response_callback(message):
    print(message)

chat.io_stream.set_callback_func(response_callback)
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
    async for message in chat.io_stream.get_response_generator():
        print(message, end="")

# Update context for next interaction
context = chat.data
```

## 4.4 Event Processing Implementation

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

@on_precompletion().handle()
async def preprocess_request(event: PreCompletionEvent):
    # Modify the messages before sending to LLM
    event.messages.append(Message(role="system", content="Be concise in your response"))

```

### 4.3.3 @on_completion Post-Completion Hooks

Post-completion hooks are executed after receiving the response from the LLM:

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion().handle()
async def postprocess_response(event: CompletionEvent):
    # Process the response before returning to user
    print(f"Response received: {event.response[:50]}...")

```

### 4.3.4 Event Processing Best Practices

- Use pre-completion hooks to modify messages before LLM processing
- Use post-completion hooks to process or log responses
- Ensure event handlers are async when performing async operations
- Return the event object from handlers to continue the chain

## 4.5 Tool Calling Implementation

### 4.4.1 Tool Registration Example

Registering tools for use by the agent with comprehensive validation:

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

# Define function schema with advanced validation
weather_func = FunctionDefinitionSchema(
    name="get_current_weather",
    description="Get the current weather in a given location",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "location": FunctionPropertySchema(
                type="string",
                description="The city and state, e.g. San Francisco, CA",
                minLength=2,           # Minimum location length
                maxLength=100,         # Maximum reasonable length
                pattern=r"^[a-zA-Z\s,-]+$"  # Only letters, spaces, commas, hyphens
            ),
            "unit": FunctionPropertySchema(
                type="string",
                enum=["celsius", "fahrenheit"],
                description="The unit of temperature"
            ),
            "forecast_days": FunctionPropertySchema(
                type="integer",
                description="Number of days to forecast (0 for current only)",
                minimum=0,
                maximum=7,
                default=0
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
    forecast_days = data.get("forecast_days", 0)

    # Simulate weather lookup with validation
    if forecast_days == 0:
        return f"The current weather in {location} is sunny, temperature is 22 degrees {unit}."
    else:
        return f"Weather forecast for {location} ({forecast_days} days): Sunny with temperatures ranging from 18-25 degrees {unit}."
```

### Enhanced Validation Features

`FunctionPropertySchema` supports comprehensive JSON Schema validation:

- **Numeric Constraints**: `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`
- **String Constraints**: `minLength`, `maxLength`, `pattern`, `format`
- **Array Constraints**: `items`, `minItems`, `maxItems`, `uniqueItems`
- **Object Constraints**: `properties`, `required`, `additionalProperties`
- **Special Values**: `enum`, `const`, `default`
- **Union Types**: `type` can be a list of allowed types

These constraints are automatically validated when the LLM generates tool calls, ensuring that only valid parameter values are passed to your tool functions.

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
    await ctx.ctx.chat_object.yield_response(f"{content}\n")

    # Return processed result
    return f"Sent a message to user:\n\n```text\n{content}\n```\n"
````

In custom run mode:

- The function receives a [ToolContext](../api-reference/classes/ToolContext.md) object instead of raw arguments
- The [ToolContext](../api-reference/classes/ToolContext.md) contains:
  - `ctx.data`: The arguments passed to the tool
  - `ctx.ctx`: The [StrategyContext](../api-reference/classes/StrategyContext.md) containing the current execution context, including access to the chat object
- Functions can be synchronous or asynchronous
- Return type can be `str` or `None`

## 4.6 Memory Management

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
    memory_abstract_proportion=0.15  # Summarize a portion of the conversation when reaching the token limit.
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

## 4.7 Logging and Debugging

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

### 4.6.2 get_last_response() Getting Last Response

Retrieve the last response from a conversation generator. This function supports streaming intermediate chunks to a target stream while extracting the final response.

```python
from amrita_core.libchat import get_last_response
from amrita_core.streaming import SuspendObjectStream

# Basic usage - get only the last response
last_resp = await get_last_response(chat_object)

# Advanced usage - stream intermediate chunks while getting the last response
class ResponseStream(SuspendObjectStream[str]):
    pass

response_stream = ResponseStream()
last_resp = await get_last_response(
    chat_object,
    yield_to=response_stream,
    yield_to_wrapper=lambda chunk: f"[STREAMING] {chunk}"
)
```

**Function Signature**:

```python
async def get_last_response(
    generator: AsyncGenerator[RESPONSE_TYPE | UniResponse[str, None], None],
    yield_to: SuspendObjectStream[RESPONSE_TYPE] | None = None,
    yield_to_wrapper: Callable[[RESPONSE_TYPE], RESPONSE_TYPE] | None = None,
) -> UniResponse[str, None]
```

**Parameters**:

- `generator`: Async generator yielding response parts (strings, MessageContent, or UniResponse objects)
- `yield_to` (optional): Target stream to send intermediate chunks to. If provided, all non-UniResponse chunks will be yielded to this stream.
- `yield_to_wrapper` (optional): Function to transform chunks before yielding them to the target stream.

**Returns**:

- The last `UniResponse` object from the generator

**Raises**:

- `RuntimeError`: If no response is found in the generator

**Use Cases**:

1. **Basic Response Extraction**: When you only need the final response metadata (usage, tool calls, etc.)
2. **Streaming with Final Response**: When you want to stream intermediate content to users while also capturing the final response for processing
3. **Response Transformation**: When you need to transform streamed content (e.g., adding prefixes, formatting, filtering)

**Example with ChatObject**:

```python
from amrita_core import ChatObject
from amrita_core.libchat import get_last_response

# Create chat object
chat = ChatObject(
    context=context,
    session_id="session_123",
    user_input="What's the weather like?",
    train=train.model_dump()
)

# Stream responses while capturing final response
async with chat.begin():
    final_response = await get_last_response(
        chat.io_stream.get_response_generator(),
        yield_to=your_websocket_stream,
        yield_to_wrapper=lambda chunk: {"type": "stream", "content": str(chunk)}
    )

    # Now you have both streamed content and final response metadata
    print(f"Total tokens used: {final_response.usage.total_tokens}")
    print(f"Tool calls made: {len(final_response.tool_calls or [])}")
```

### 4.6.3 Debugging Tips

- Enable debug logging during development
- Monitor token usage to prevent exceeding limits
- Use streaming responses for real-time feedback
- Implement proper error handling for robust applications
