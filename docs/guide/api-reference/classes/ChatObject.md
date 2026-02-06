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
- `response_queue` (asyncio.Queue[Any]): Response queue
- `overflow_queue` (asyncio.Queue[Any]): Overflow queue
- `_is_running` (bool): Whether it is running
- `_is_done` (bool): Whether it is completed
- `_task` (Task[None]): Task
- `_has_task` (bool): Whether there is a task
- `_err` (BaseException | None): Error
- `_wait` (bool): Whether to wait
- `_queue_done` (bool): Whether queue is done

## Constructor Parameters

- `context` ([MemoryModel](MemoryModel.md)): Memory context for the conversation
- `session_id` (str): Unique identifier for the session
- `user_input` (str): The user's input message
- `train` (dict): Training/prompt data for the AI

## Methods

- `begin()`: Executes the conversation
- `get_response_generator()`: Returns an async generator for streaming responses
- `full_response()`: Returns the complete response

## Example

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

## Description

The ChatObject class is responsible for processing a single chat session, including message receiving, context management, model calling, and response sending. It is one of the core classes in the AmritaCore framework for handling conversations.