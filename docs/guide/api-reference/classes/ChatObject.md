# ChatObject

The ChatObject class is the primary interface for conversations with the AI.

## Properties

- `stream_id` (str): Chat object ID
- `timestamp` (str): Timestamp
- `time` (datetime): Time
- `end_at` (datetime | None): End time
- `data` (Memory): Memory file
- `user_input` (USER_INPUT): User input
- `user_message` (Message[USER_INPUT]): User message
- `context_wrap` (SendMessageWrap): Context wrapper
- `train` (dict[str, str]): Training/prompt data
- `last_call` (datetime): Time of last internal function call
- `session_id` (str): Session ID
- `response` (UniResponse[str, None]): Response
- `_response_queue` (asyncio.Queue[Any]): Response queue
- `_overflow_queue` (asyncio.Queue[Any]): Overflow queue
- `_is_running` (bool): Whether it is running
- `_is_done` (bool): Whether it is completed
- `_task` (Task[None]): Task
- `_has_task` (bool): Whether there is a task
- `_err` (BaseException | None): Error
- `_wait` (bool): Whether to wait
- `_queue_done` (bool): Whether queue is done
- `_callback_fun` (RESPONSE_CALLBACK_TYPE): Callback function for handling responses
- `_callback_lock` (Lock): Lock for thread-safe callback execution

## Constructor Parameters

- `context` ([MemoryModel](MemoryModel.md)): Memory context for the conversation
- `session_id` (str): Unique identifier for the session
- `user_input` (str): The user's input message
- `train` (dict): Training/prompt data for the AI
- `callback` (RESPONSE_CALLBACK_TYPE): Optional callback function for direct response handling (useful for web scenarios)
- `config` (AmritaConfig): configuration settings for the chat that overrides the global configuration.
- `preset` (ModelPreset): model preset for the chat.
- `auto_create_session` (bool): Whether to automatically create a session if it does not exist (default: False)
- `train_template` (Template): Jinja2 template used to format system message (default: DEFAULT_TEMPLATE)
- `jinja2_vars` (dict[str, Any] | None): Variables to be passed to the template system for custom template variables (default: None). **Important**: Keys in this dictionary must NOT match built-in variable names (`train`, `memory`, `chatobj`, `config`) as this would cause a TypeError due to duplicate keyword arguments.
- `agent_strategy` (type[AgentStrategy]): Agent strategy to be used for execution (default: ReActAgentStrategy)
- `hook_args` (tuple[Any, ...]): Positional arguments passed to event handlers when events are triggered (default: empty tuple)
- `hook_kwargs` (dict[str, Any] | None): Keyword arguments passed to event handlers when events are triggered (default: None)
- `exception_ignored` (tuple[type[BaseException], ...]): Exception types that should be ignored and raised again in event handlers (default: empty tuple)
- `queue_size` (int): Size of the primary response queue (default: **45**)
- `overflow_queue_size` (int): Size of the overflow queue (default: **15**)

## Methods

- `begin()`: Execute the conversation
- `get_response_generator()`: Returns an async generator for streaming responses
- `full_response()`: Returns the complete response
- `set_callback_func(func: RESPONSE_CALLBACK_TYPE)`: Set a callback function for response handling
- `yield_response(response: RESPONSE_TYPE)`: Yield response to queue or callback function
- `wait_to_suspend(timeout: float = 5.0, tag: str | None = None)`: **(Advanced)** Wait for suspend signal with optional tag matching
- `resume()`: **(Advanced)** Resume suspended execution flow
- `_wait_for_continue(tag: str | None = None)`: **(Advanced)** Manual suspend point for use with external controllers

### Suspend & Resume Methods Details

#### `wait_to_suspend(timeout: float = 5.0, tag: str | None = None)`

Call this method from an external independent task to pause `ChatObject` execution when it reaches the next suspend point.

**Parameters:**

- `*tags` (str): Optional tag filter (passed as positional arguments)
  - No tags (default): Matches all methods decorated with `@suspend`
  - Single tag string: Only matches methods decorated with `@ChatObject.suspend_with_tag(tag)`
  - **Standard tags**: Use [SuspendEnum](SuspendEnum.md) values for built-in breakpoints:
    - `SuspendEnum.MEMORY.value`: Before memory summarization
    - `SuspendEnum.SINGLE_TOOL.value`: Before each tool call
    - `SuspendEnum.PRECOMPLE.value`: Before model completion
    - `SuspendEnum.COMPLE.value`: After model completion
- `timeout` (float): Timeout in seconds, prevents infinite blocking

**Exceptions:**

- `asyncio.TimeoutError`: Raised if suspend is not triggered within the specified timeout

**Example:**

```python
from amrita_core import SuspendEnum

# Wait for any suspend point
await chat.wait_to_suspend(timeout=3.0)

# Wait for a specific standardized suspend point
await chat.wait_to_suspend(SuspendEnum.SINGLE_TOOL.value, timeout=5.0)

# Wait for custom tag
await chat.wait_to_suspend("custom_tag", timeout=2.0)
```

#### `resume()`

Resumes the suspended `ChatObject` execution flow. Continues execution until the next suspend point or completes the current operation.

**Example:**

```python
async def controller(chat_obj):
    await chat_obj.wait_to_suspend("checkpoint")
    print("Suspended, inspecting state...")
    # Perform inspection or modification
    chat_obj.resume()  # Resume execution
```

#### `_wait_for_continue(tag: str | None = None)`

Manual suspend point, typically used inside custom functions to enable fine-grained flow control with external controllers.

**Parameters:**

- `tag` (str | None): Optional tag for precise matching with external controller's `wait_to_suspend(...)` call

**Behavior:**

- Returns immediately without blocking if no external `wait_to_suspend()` call is pending or tags don't match
- Blocks until `resume()` is called if external controller is waiting for a matching tag

**Example:**

```python
from amrita_core import ChatObject

class MyProcessor:
    async def process_data(self, chat_obj: ChatObject, data: dict):
        # Before processing
        await chat_obj._wait_for_continue(tag="before_process")

        result = await self.do_processing(data)

        # After processing
        await chat_obj._wait_for_continue(tag="after_process")

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

chat_with_callback = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump(),
    callback=callback_handler,
    queue_size=20,
    overflow_queue_size=40
)

# Alternative: Set callback after creation
chat_without_callback = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump()
)
chat_without_callback.set_callback_func(callback_handler)

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

The new callback mechanism is designed to prevent queue overflow in scenarios where consumers may not keep up with producers (e.g., web applications). When a callback function is provided:

1. Responses are directly passed to the callback function instead of being queued
2. This prevents memory buildup and potential overflow issues
3. The callback function is executed asynchronously with proper locking for thread safety

When no callback is provided, the traditional queue-based streaming mechanism is used with both primary and overflow queues to handle temporary consumer lag.

### Event Parameter Injection

The `hook_args`, `hook_kwargs`, and `exception_ignored` parameters enable custom parameter injection into event handlers. When events like `PreCompletionEvent` or `CompletionEvent` are triggered, these parameters are passed to the registered event handlers, allowing them to access additional context information and customize their behavior based on the specific chat session requirements.

### Jinja2 Template Variables

The `jinja2_vars` parameter allows you to pass custom variables to the Jinja2 template system. These variables are **directly unpacked** using `**self.jinja2_vars` during template rendering, which means:

1. **Direct Variable Access**: Keys in the `jinja2_vars` dictionary become directly accessible as template variables (e.g., `{"role": "expert"}` makes `role` available in templates)
2. **No Variable Override**: **Important**: You CANNOT use keys that match built-in variable names (`train`, `memory`, `chatobj`, `config`) in `jinja2_vars`. Doing so will result in a `TypeError` because Python does not allow duplicate keyword arguments in function calls.
3. **Reserved Keyword**: The key `'self'` is reserved and cannot be used in `jinja2_vars`

This design provides maximum flexibility for template customization while maintaining safety by preventing accidental conflicts with built-in variables.
