# SuspendObjectStream

`SuspendObjectStream` is a generic base class that provides suspend/resume capabilities and streaming response handling for objects that need to produce items asynchronously to a single consumer.

This class implements a producer-to-single-consumer architecture using AnyIO's memory object streams, providing built-in backpressure handling and flow control.

## Class Definition

```python
class SuspendObjectStream(Generic[ObjectTypeT])
```

## Constructor

```python
def __init__(
    self,
    /,
    queue_size: int = 45,
    queue_timeout: float | None = 10.0,
    callback: CALLBACK_TYPE | None = None,
) -> None
```

### Parameters

- `queue_size` (int): Maximum buffer size for the response stream. Defaults to `45`.
- `queue_timeout` (float | None): Timeout for queue operations in seconds. If `None`, operations will wait indefinitely. Defaults to `10.0`.
- `callback` (CALLBACK_TYPE | None): Async callback function that receives response chunks as they are generated. Defaults to `None`.

## Properties

- `_send_stream` (ObjectSendStream): AnyIO send stream for producing items
- `_receive_stream` (ObjectReceiveStream): AnyIO receive stream for consuming items
- `_callback_fun` (CALLBACK_TYPE | None): Callback function for direct response handling
- `_callback_lock` (aiologic.Lock): Lock for thread-safe callback execution
- `_queue_done` (bool): Whether the response queue is closed
- `_has_consumer` (bool): Whether a consumer is already reading from the stream
- `_q_tout` (float | None): Queue timeout setting
- `_suspend_tags` (tuple[str, ...] | None): Current suspend tags filter
- `__suspend_signal` (asyncio.Future | None): Signal for suspend requests
- `__resume_signal` (asyncio.Future | None): Signal for resume requests

## Methods

### Static Methods

#### `suspend(func: Callable[..., Any], tag: str | None = None) -> Callable[..., Any]`

Decorator for suspend functionality. Automatically detects suspend signals before executing the decorated function.

**Parameters**:

- `func`: The coroutine function to decorate
- `tag` (str | None): Optional tag for precise breakpoint matching

**Returns**: Decorated function that supports suspend/resume

**Raises**: `TypeError` if the function is not a coroutine function

#### `suspend_with_tag(tag: str)`

Decorator factory for tagged suspend points.

**Parameters**:

- `tag` (str): Tag for breakpoint identification

**Returns**: Decorator that applies `@suspend` with the specified tag

### Instance Methods

#### `wait_to_suspend(*tags: str, timeout: float | None = None)`

Tell the stream to suspend and wait for it.

**Parameters**:

- `*tags` (str): Tags to wait for (filter break points)
- `timeout` (float | None): Timeout for waiting. Defaults to None (infinite wait)

**Raises**: `RuntimeError` if already waiting for suspend

#### `resume() -> None`

Resume execution when suspended.

#### `_wait_for_continue(tag: str | None = None) -> bool`

Break point for suspend mechanism.

**Parameters**:

- `tag` (str | None): Tag for break point filtering

**Returns**: `True` if actually waited during running, `False` if not

#### `yield_response(response: ObjectTypeT) -> None`

Send response to the queue or callback function.

**Parameters**:

- `response`: Item to send to the consumer

**Raises**: `RuntimeError` if queue is closed

#### `set_callback_func(func: CALLBACK_TYPE) -> None`

Set a callback function to be executed when a response is yielded.

**Parameters**:

- `func` (CALLBACK_TYPE): Function to be executed when a response is yielded

**Raises**: `RuntimeError` if a callback function is already set

#### `yield_response_iteration(iterator: AsyncGenerator[ObjectTypeT, None])`

Send responses from an async generator to the queue or callback.

**Parameters**:

- `iterator`: Async generator yielding response items

#### `get_response_generator() -> AsyncGenerator[ObjectTypeT, None]`

Return an async generator to iterate over responses from the queue.

**Yields**: Items from the response queue

**Raises**: `RuntimeError` if response is already being consumed

#### `queue_closed() -> bool`

Check if the response queue is closed.

**Returns**: `True` if the queue is closed, `False` otherwise

#### `set_queue_done() -> None`

Mark the response queue as done by putting the done marker.

## Usage Examples

### Basic Streaming

```python
from amrita_core.streaming import SuspendObjectStream

class MyStream(SuspendObjectStream[str]):
    pass

stream = MyStream()
await stream.yield_response("Hello")
await stream.yield_response("World")
await stream.set_queue_done()

async for item in stream.get_response_generator():
    print(item)  # Prints "Hello", then "World"
```

### With Callback

```python
async def my_callback(item: str):
    print(f"Received: {item}")

stream = MyStream(callback=my_callback)
await stream.yield_response("Hello")  # Immediately calls my_callback("Hello")
```

### Suspend/Resume Control

```python
import asyncio

class Processor(SuspendObjectStream[str]):
    @SuspendObjectStream.suspend
    async def process_step(self, data: str):
        return f"Processed: {data}"

processor = Processor()

# External controller
async def controller():
    await processor.wait_to_suspend(timeout=5.0)
    print("Suspended!")
    processor.resume()

async def main():
    controller_task = asyncio.create_task(controller())

    result = await processor.process_step("test")
    print(result)  # "Processed: test"

    controller_task.cancel()

asyncio.run(main())
```

### Tagged Breakpoints

```python
class AdvancedProcessor(SuspendObjectStream[str]):
    @SuspendObjectStream.suspend_with_tag("before_process")
    async def preprocess(self, data: str):
        return f"Preprocessed: {data}"

    @SuspendObjectStream.suspend_with_tag("after_process")
    async def postprocess(self, data: str):
        return f"Postprocessed: {data}"

processor = AdvancedProcessor()

# Wait for specific tagged breakpoint
await processor.wait_to_suspend("before_process", timeout=5.0)
# Execution will pause at preprocess method
```

## Integration with ChatObject

`ChatObject` inherits from `SuspendObjectStream[RESPONSE_TYPE]`, so all methods are available on ChatObject instances:

```python
from amrita_core import ChatObject

chat = ChatObject(...)

# Use suspend/resume methods directly
await chat.wait_to_suspend("custom_tag")
chat.resume()

# Stream responses
async for response in chat.get_response_generator():
    print(response)
```

## Key Features

- **Generic Typing**: Supports any response type through generic parameterization
- **Built-in Backpressure**: Uses AnyIO memory object streams for automatic flow control
- **Thread Safety**: Callback execution is protected by aiologic locks
- **Flexible Suspend Points**: Supports both tagged and untagged suspend points
- **Producer-Consumer Pattern**: Clean separation between producer and consumer logic
- **Timeout Safety**: All blocking operations respect timeout parameters

## Type Definitions

- `CALLBACK_TYPE = Callable[[ObjectTypeT], Awaitable[Any]]`
- `ObjectTypeT = TypeVar("ObjectTypeT")`
