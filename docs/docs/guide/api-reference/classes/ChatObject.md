# ChatObject

The ChatObject class is the primary interface for conversations with the AI. It uses a `SuspendObjectStream[RESPONSE_TYPE]` via the `io_stream` attribute (composition instead of inheritance since v0.9.1) for suspend/resume capabilities and streaming response handling.

## Properties

### Identity

- `stream_id` (str): Chat object ID
- `session_id` (str): Session ID

### Timing

- `timestamp` (str): Timestamp (for LLM)
- `time` (datetime): Creation time
- `end_at` (datetime | None): End time
- `last_call` (datetime): Time of last internal function call
- `now_calling` (str | None): Currently calling function name

### Config & Preset

- `config` (AmritaConfig): Configuration used in this call
- `preset` (ModelPreset): Model preset used in this call
- `strategy` (type[AgentStrategy] | StrategyLikedObject): Agent strategy

### Input / Data

- `user_input` (USER_INPUT): User input
- `user_message` (Message[USER_INPUT]): User message
- `data` (Memory): Memory file
- `train` (Message[str]): System message
- `template` (Template): Jinja2 template
- `jinja2_vars` (dict[str, Any]): Variables passed to template system

### IO-Stream

- `io_stream` (SuspendObjectStream[RESPONSE_TYPE]): Streaming interface for responses

### Context

- `context_wrap` (SendMessageWrap): Context message wrapper

### Response

- `response` (UniResponse[str, None]): Response from LLM
- `extra_usage` (UniResponseUsage[int]): Additional usage statistics from memory limiting and other operations

## Constructor Parameters

- `context` ([MemoryModel](MemoryModel.md)): Memory context for the conversation
- `session_id` (str): Unique identifier for the session
- `user_input` (str): The user's input message
- `train` (dict): Training/prompt data for the AI
- `io_stream` (SuspendObjectStream[RESPONSE_TYPE] | None): External SuspendObjectStream instance to use. If None, a new one is created automatically (default: None)
- `config` (AmritaConfig): configuration settings for the chat that overrides the global configuration.
- `preset` (ModelPreset): model preset for the chat.
- `auto_create_session` (bool): Whether to automatically create a session if it does not exist (default: False)
- `train_template` (Template): Jinja2 template used to format system message (default: DEFAULT_TEMPLATE)
- `jinja2_vars` (dict[str, Any] | None): Variables to be passed to the template system for custom template variables (default: None). **Important**: Keys in this dictionary must NOT match built-in variable names (`train`, `memory`, `chatobj`, `config`) as this would cause a TypeError due to duplicate keyword arguments.
- `agent_strategy` (type[AgentStrategy] | [StrategyLikedObject](StrategyLikedObject.md)): Agent strategy to be used for execution. Accepts either a strategy **class** (`type[AgentStrategy]`) or a pre-initialised strategy **instance** (`StrategyLikedObject`). The latter enables stateful strategies with internal state machines (default: ReActAgentStrategy)
- `hook_args` (tuple[Any, ...]): Positional arguments passed to event handlers when events are triggered (default: empty tuple)
- `hook_kwargs` (dict[str, Any] | None): Keyword arguments passed to event handlers when events are triggered (default: None)
- `exception_ignored` (tuple[type[BaseException], ...]): Exception types that should be ignored and raised again in event handlers (default: empty tuple)
- `middleware` (Callable[[Self], Awaitable[Any]] | None): Async middleware function that wraps the entire workflow execution. When set, the workflow engine delegates execution to the middleware instead of running the default pipeline. Useful for custom orchestration, monitoring, or cross-cutting concerns (default: None)
- `archived_nodes` (SubprogramStorage | None): Additional node subprograms to append at the end of the workflow pipeline. Allows extending the ChatObject execution with custom steps after the standard pipeline completes. When `None`, defaults to `ARCHIVED_NODES` from `amrita_sense.instructions` (default: None)

## Methods

### Core Methods

- `begin()`: Start the chat object task (returns Self)
- `terminate()`: Terminate task execution
- `full_response()`: Return full response from the queue as a single string
- `get_exception()`: Get exceptions that occurred during task execution
- `is_running()`: Check if the task is running
- `is_done()`: Check if the task has completed
- `get_snapshot()`: Get a snapshot of the chat object as `ChatObjectMeta`

### Deprecated Streaming Methods (removed in 0.10.0)

> **Since v0.9.1**: All streaming/suspend methods have moved to `io_stream`. The following methods are deprecated forwarding wrappers that will be removed in v0.10.0:

- `get_response_generator()` → use `io_stream.get_response_generator()`
- `set_callback_func(func)` → use `io_stream.set_callback_func(func)`
- `set_callback_fun_sending(func)` → use `io_stream.set_callback_fun_sending(func)`
- `yield_response(response)` → use `io_stream.yield_response(response)`
- `yield_response_iteration(iterator)` → use `io_stream.yield_response_iteration(iterator)`
- `push_object(obj)` → use `io_stream.push_object(obj)`
- `queue_closed()` → use `io_stream.queue_closed()`
- `set_queue_done()` → use `io_stream.set_queue_done()`
- `wait_to_suspend(*tags, timeout)` → use `io_stream.wait_to_suspend(*tags, timeout)`
- `resume()` → use `io_stream.resume()`

### Suspend & Resume Methods Details

> **Since v0.9.1**: Use `io_stream.wait_to_suspend()` and `io_stream.resume()` instead. The methods on `ChatObject` are deprecated forwarding wrappers.

#### `io_stream.wait_to_suspend(*tags: str, timeout: float | None = None)`

Call this method from an external independent task to pause `ChatObject` execution when it reaches the next suspend point.

**Parameters:**

- `*tags` (str): Optional tag filter (passed as positional arguments)
  - No tags (default): Matches all methods decorated with `@suspend`
  - Single tag string: Only matches methods decorated with `@SuspendObjectStream.suspend_with_tag(tag)`
  - **Standard tags**: Use [SuspendEnum](SuspendEnum.md) values for built-in breakpoints:
    - `SuspendEnum.MEMORY.value`: Before memory summarization
    - `SuspendEnum.SINGLE_TOOL.value`: Before each tool call
    - `SuspendEnum.PRECOMPLE.value`: Before model completion
    - `SuspendEnum.COMPLE.value`: After model completion
- `timeout` (float | None): Timeout in seconds, prevents infinite blocking. If None, waits indefinitely.

**Exceptions:**

- `asyncio.TimeoutError`: Raised if suspend is not triggered within the specified timeout
- `RuntimeError`: Raised if already waiting for suspend

**Example:**

```python
from amrita_core import SuspendEnum

# Wait for any suspend point
await chat.io_stream.wait_to_suspend(timeout=3.0)

# Wait for a specific standardized suspend point
await chat.io_stream.wait_to_suspend(SuspendEnum.SINGLE_TOOL.value, timeout=5.0)

# Wait for custom tag
await chat.io_stream.wait_to_suspend("custom_tag", timeout=2.0)
```

#### `io_stream.resume()`

Resumes the suspended execution flow. Continues execution until the next suspend point or completes the current operation.

**Example:**

```python
async def controller(chat_obj):
    await chat_obj.io_stream.wait_to_suspend("checkpoint")
    print("Suspended, inspecting state...")
    # Perform inspection or modification
    chat_obj.io_stream.resume()  # Resume execution
```

#### `io_stream._wait_for_continue(tag: str | None = None)`

Manual suspend point, typically used inside custom functions to enable fine-grained flow control with external controllers.

**Parameters:**

- `tag` (str | None): Optional tag for precise matching with external controller's `wait_to_suspend(...)` call

**Behavior:**

- Returns immediately without blocking if no external `wait_to_suspend()` call is pending or tags don't match
- Blocks until `resume()` is called if external controller is waiting for a matching tag

**Example:**

```python
from amrita_core import SuspendObjectStream

class MyProcessor:
    @SuspendObjectStream.suspend_with_tag("before_process")
    async def process_data(self, chat_obj: ChatObject, data: dict):
        result = await self.do_processing(data)
        return result
```

**For detailed documentation, see**: [Suspend & Resume Mechanism](../concepts/suspend.md)

## Example

```python
from amrita_core import ChatObject
from amrita_core.types import MemoryModel, Message

context = MemoryModel()
train = Message(content="You are a helpful assistant.", role="system")

# Example with callback (recommended for web scenarios)
async def callback_handler(message):
    print("Received:", message)

chat = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump(),
)

# Set callback via io_stream (replaces previous `callback=` constructor parameter)
chat.io_stream.set_callback_func(callback_handler)

# Example with custom event parameters
chat_with_event_params = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump(),
    hook_args=("custom_arg1", "custom_arg2"),
    hook_kwargs={"custom_key": "custom_value"},
    exception_ignored=(ValueError, TypeError)
)

# Example with custom Jinja2 variables
chat_with_jinja2_vars = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump(),
    jinja2_vars={"custom_role": "AI expert", "company_name": "Amrita Corp"}
)

# Example with custom io_stream
from amrita_sense.streaming import SuspendObjectStream
custom_stream = SuspendObjectStream(queue_size=100, queue_timeout=30.0)
chat_with_custom_stream = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump(),
    io_stream=custom_stream,
)

# ❌ INVALID - This will cause a TypeError:
# chat_with_override = ChatObject(
#     context=context,
#     session_id="session_123",
#     user_input="Hello!",
#     train=train.model_dump(),
#     jinja2_vars={"config": {"custom_setting": "value"}}  # ERROR: 'config' is a built-in parameter
# )
```

## Description

The ChatObject class is responsible for processing a single chat session, including message receiving, context management, model calling, and response sending. It is one of the core classes in the AmritaCore framework for handling conversations.

### Callback Mechanism

The callback mechanism is provided by the `io_stream` attribute (a `SuspendObjectStream` instance) and works as follows:

1. Responses are directly passed to the callback function instead of being queued when a callback is provided
2. This prevents memory buildup and potential overflow issues
3. The callback function is executed asynchronously with proper locking for thread safety

When no callback is provided, the traditional queue-based streaming mechanism is used with AnyIO's memory object streams providing built-in backpressure handling.

### Event Parameter Injection

The `hook_args`, `hook_kwargs`, and `exception_ignored` parameters enable custom parameter injection into event handlers. When events like `PreCompletionEvent` or `CompletionEvent` are triggered, these parameters are passed to the registered event handlers, allowing them to access additional context information and customize their behavior based on the specific chat session requirements.

### Jinja2 Template Variables

The `jinja2_vars` parameter allows you to pass custom variables to the Jinja2 template system. These variables are **directly unpacked** using `**self.jinja2_vars` during template rendering, which means:

1. **Direct Variable Access**: Keys in the `jinja2_vars` dictionary become directly accessible as template variables (e.g., `{"role": "expert"}` makes `role` available in templates)
2. **No Variable Override**: **Important**: You CANNOT use keys that match built-in variable names (`train`, `memory`, `chatobj`, `config`) in `jinja2_vars`. Doing so will result in a `TypeError` because Python does not allow duplicate keyword arguments in function calls.
3. **Reserved Keyword**: The key `'self'` is reserved and cannot be used in `jinja2_vars`

This design provides maximum flexibility for template customization while maintaining safety by preventing accidental conflicts with built-in variables.

### Streaming Response Processing

AmritaCore uses **AnyIO memory object streams** for streaming responses, which provides built-in backpressure handling:

```python
# Process streaming responses
async for message in chat.io_stream.get_response_generator():
    content = message if isinstance(message, str) else message.get_content()
    print(content, end="")
```

**Key Features of AnyIO Backpressure**:

- **Automatic Flow Control**: When the consumer is slower than the producer, the producer automatically waits
- **Single Buffer**: Uses a single buffer instead of dual queues with overflow
- **Memory Efficient**: Built-in buffer size limits prevent unbounded memory growth
- **Timeout Safety**: Queue operations respect the `queue_timeout` parameter

**Note**: The previous `overflow_queue_size` parameter has been removed. All backpressure is now handled by AnyIO's single-stream mechanism.
