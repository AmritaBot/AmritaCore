# SuspendObjectStream

`SuspendObjectStream` 是一个泛型基类，为需要异步向单个消费者产生项目的对象提供挂起/恢复功能和流式响应处理。

该类使用 AnyIO 的内存对象流实现生产者到单个消费者的架构，提供内置的背压处理和流控制。

## 类定义

```python
class SuspendObjectStream(Generic[ObjectTypeT])
```

## 构造函数

```python
def __init__(
    self,
    /,
    queue_size: int = 45,
    queue_timeout: float | None = 10.0,
    callback: CALLBACK_TYPE | None = None,
) -> None
```

### 参数

- `queue_size` (int): 响应流的最大缓冲区大小。默认为 `45`。
- `queue_timeout` (float | None): 队列操作的超时时间（秒）。如果为 `None`，操作将无限等待。默认为 `10.0`。
- `callback` (CALLBACK_TYPE | None): 异步回调函数，在生成响应块时接收它们。默认为 `None`。

## 属性

- `_send_stream` (ObjectSendStream): AnyIO 发送流，用于产生项目
- `_receive_stream` (ObjectReceiveStream): AnyIO 接收流，用于消费项目
- `_callback_fun` (CALLBACK_TYPE | None): 用于直接响应处理的回调函数
- `_callback_lock` (aiologic.Lock): 用于线程安全回调执行的锁
- `_queue_done` (bool): 响应队列是否已关闭
- `_has_consumer` (bool): 是否已有消费者从流中读取
- `_q_tout` (float | None): 队列超时设置
- `_suspend_tags` (tuple[str, ...] | None): 当前挂起标签过滤器
- `__suspend_signal` (asyncio.Future | None): 挂起请求信号
- `__resume_signal` (asyncio.Future | None): 恢复信号

## 方法

### 静态方法

#### `suspend(func: Callable[..., Any], tag: str | None = None) -> Callable[..., Any]`

挂起功能的装饰器。在执行装饰的函数之前自动检测挂起信号。

**参数**:

- `func`: 要装饰的协程函数
- `tag` (str | None): 可选的标签，用于精确断点匹配

**返回值**: 支持挂起/恢复的装饰函数

**异常**: 如果函数不是协程函数，则抛出 `TypeError`

#### `suspend_with_tag(tag: str)`

带标签挂起点的装饰器工厂。

**参数**:

- `tag` (str): 用于断点识别的标签

**返回值**: 应用带有指定标签的 `@suspend` 装饰器的装饰器

### 实例方法

#### `wait_to_suspend(*tags: str, timeout: float | None = None)`

告诉流挂起并等待它。

**参数**:

- `*tags` (str): 要等待的标签（过滤断点）
- `timeout` (float | None): 等待超时时间。默认为 None（无限等待）

**异常**: 如果已经在等待挂起，则抛出 `RuntimeError`

#### `resume() -> None`

在挂起时恢复执行。

#### `_wait_for_continue(tag: str | None = None) -> bool`

挂起机制的断点。

**参数**:

- `tag` (str | None): 用于断点过滤的标签

**返回值**: 如果在运行期间实际等待了则返回 `True`，否则返回 `False`

#### `yield_response(response: ObjectTypeT) -> None`

将响应发送到队列或回调函数。

**参数**:

- `response`: 要发送给消费者的数据项

**异常**: 如果队列已关闭，则抛出 `RuntimeError`

#### `set_callback_func(func: CALLBACK_TYPE) -> None`

设置在产生响应时要执行的回调函数。

**参数**:

- `func` (CALLBACK_TYPE): 在产生响应时要执行的函数

**异常**: 如果已经设置了回调函数，则抛出 `RuntimeError`

#### `yield_response_iteration(iterator: AsyncGenerator[ObjectTypeT, None])`

将来自异步生成器的响应发送到队列或回调。

**参数**:

- `iterator`: 产生响应项的异步生成器

#### `get_response_generator() -> AsyncGenerator[ObjectTypeT, None]`

返回一个异步生成器，用于迭代队列中的响应。

**Yields**: 来自响应队列的数据项

**异常**: 如果响应已经被消费，则抛出 `RuntimeError`

#### `queue_closed() -> bool`

检查响应队列是否已关闭。

**返回值**: 如果队列已关闭则返回 `True`，否则返回 `False`

#### `set_queue_done() -> None`

通过放置完成标记来标记响应队列已完成。

## 使用示例

### 基本流式传输

```python
from amrita_core.streaming import SuspendObjectStream

class MyStream(SuspendObjectStream[str]):
    pass

stream = MyStream()
await stream.yield_response("Hello")
await stream.yield_response("World")
await stream.set_queue_done()

async for item in stream.get_response_generator():
    print(item)  # 打印 "Hello"，然后 "World"
```

### 带回调

```python
async def my_callback(item: str):
    print(f"收到: {item}")

stream = MyStream(callback=my_callback)
await stream.yield_response("Hello")  # 立即调用 my_callback("Hello")
```

### 挂起/恢复控制

```python
import asyncio

class Processor(SuspendObjectStream[str]):
    @SuspendObjectStream.suspend
    async def process_step(self, data: str):
        return f"已处理: {data}"

processor = Processor()

# 外部控制器
async def controller():
    await processor.wait_to_suspend(timeout=5.0)
    print("已挂起！")
    processor.resume()

async def main():
    controller_task = asyncio.create_task(controller())

    result = await processor.process_step("test")
    print(result)  # "已处理: test"

    controller_task.cancel()

asyncio.run(main())
```

### 带标签的断点

```python
class AdvancedProcessor(SuspendObjectStream[str]):
    @SuspendObjectStream.suspend_with_tag("before_process")
    async def preprocess(self, data: str):
        return f"预处理: {data}"

    @SuspendObjectStream.suspend_with_tag("after_process")
    async def postprocess(self, data: str):
        return f"后处理: {data}"

processor = AdvancedProcessor()

# 等待特定的带标签断点
await processor.wait_to_suspend("before_process", timeout=5.0)
# 执行将在 preprocess 方法处暂停
```

## 与 ChatObject 集成

`ChatObject` 继承自 `SuspendObjectStream[RESPONSE_TYPE]`，因此所有方法都可在 ChatObject 实例上使用：

```python
from amrita_core import ChatObject

chat = ChatObject(...)

# 直接使用挂起/恢复方法
await chat.wait_to_suspend("custom_tag")
chat.resume()

# 流式传输响应
async for response in chat.get_response_generator():
    print(response)
```

## 主要特性

- **泛型类型**: 通过泛型参数化支持任何响应类型
- **内置背压**: 使用 AnyIO 内存对象流进行自动流控制
- **线程安全**: 回调执行受 aiologic 锁保护
- **灵活的挂起点**: 支持带标签和不带标签的挂起点
- **生产者-消费者模式**: 生产者和消费者逻辑的清晰分离
- **超时安全**: 所有阻塞操作都遵循超时参数

## 类型定义

- `CALLBACK_TYPE = Callable[[ObjectTypeT], Awaitable[Any]]`
- `ObjectTypeT = TypeVar("ObjectTypeT")`
