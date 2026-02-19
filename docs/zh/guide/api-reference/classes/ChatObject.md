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
- `hook_args` (tuple[Any, ...]): Positional arguments passed to event handlers when events are triggered (default: empty tuple)
- `hook_kwargs` (dict[str, Any] | None): Keyword arguments passed to event handlers when events are triggered (default: None)
- `exception_ignored` (tuple[type[BaseException], ...]): Exception types that should be ignored and raised again in event handlers (default: empty tuple)
- `queue_size` (int): Size of the primary response queue (default: 25)
- `overflow_queue_size` (int): Size of the overflow queue (default: 45)

## Methods

- `begin()`: Executes the conversation
- `get_response_generator()`: Returns an async generator for streaming responses
- `full_response()`: Returns the complete response
- `set_callback_func(func: RESPONSE_CALLBACK_TYPE)`: Sets a callback function for response handling
- `yield_response(response: RESPONSE_TYPE)`: Sends a response to the queue or callback

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