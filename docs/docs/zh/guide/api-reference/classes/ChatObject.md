# ChatObject

ChatObject 类是与 AI 进行对话的主要接口。它继承自 `SuspendObjectStream[RESPONSE_TYPE]`，提供内置的挂起/恢复功能和流式响应处理。

## 属性

- `stream_id` (str): 聊天对象 ID
- `timestamp` (str): 时间戳
- `time` (datetime): 时间
- `end_at` (datetime | None): 结束时间
- `data` (Memory): 记忆文件
- `user_input` (USER_INPUT): 用户输入
- `user_message` (Message[USER_INPUT]): 用户消息
- `context_wrap` (SendMessageWrap): 上下文包装器
- `train` (dict[str, str]): 训练/提示数据
- `last_call` (datetime): 最后一次内部函数调用时间
- `session_id` (str): 会话 ID
- `response` (UniResponse[str, None]): 响应
- `extra_usage` (UniResponseUsage[int]): 来自内存限制和其他操作的额外使用统计
- `_is_running` (bool): 是否正在运行
- `_is_done` (bool): 是否已完成
- `_task` (Task[None]): 任务
- `_err` (BaseException | None): 错误
- `_q_tout` (float | None): 队列超时设置
- `_hook_kwargs` (dict[str, Any]): 事件处理器的关键字参数
- `_hook_args` (tuple[Any, ...]): 事件处理器的位置参数

## 构造函数参数

- `context` ([MemoryModel](MemoryModel.md)): 对话的内存上下文
- `session_id` (str): 会话的唯一标识符
- `user_input` (str): 用户输入消息
- `train` (dict): AI的训练/提示数据
- `callback` (RESPONSE_CALLBACK_TYPE): 可选的回调函数，用于直接处理响应（适用于Web场景）
- `config` (AmritaConfig): 聊天的配置设置，覆盖全局配置
- `preset` (ModelPreset): 聊天的模型预设
- `auto_create_session` (bool): 如果会话不存在是否自动创建（默认：False）
- `train_template` (Template): 用于格式化系统消息的Jinja2模板（默认：DEFAULT_TEMPLATE）
- `jinja2_vars` (dict[str, Any] | None): 传递给模板系统的变量，用于自定义模板变量（默认：None）。**重要**：此字典中的键不能与内置变量名（`train`、`memory`、`chatobj`、`config`）匹配，否则会导致TypeError，因为函数调用中不允许重复的关键字参数。
- `agent_strategy` (type[AgentStrategy]): 用于执行的Agent策略（默认：ReActAgentStrategy）
- `hook_args` (tuple[Any, ...]): 触发事件时传递给事件处理器的位置参数（默认：空元组）
- `hook_kwargs` (dict[str, Any] | None): 触发事件时传递给事件处理器的关键字参数（默认：None）
- `exception_ignored` (tuple[type[BaseException], ...]): 在事件处理器中应该被忽略并再次抛出的异常类型（默认：空元组）
- `queue_size` (int): 响应流缓冲区大小（默认：**45**）
- `queue_timeout` (float | None): 队列操作超时时间（秒）（默认：**10.0**）

## 方法

- `begin()`: 执行对话
- `get_response_generator()`: 返回用于流式响应的异步生成器（继承自 SuspendObjectStream）
- `full_response()`: 返回完整响应（继承自 SuspendObjectStream）
- `set_callback_func(func: RESPONSE_CALLBACK_TYPE)`: 设置响应处理的回调函数（继承自 SuspendObjectStream）
- `yield_response(response: RESPONSE_TYPE)`: 将响应推送到队列或回调函数（继承自 SuspendObjectStream）
- `wait_to_suspend(*tags: str, timeout: float | None = None)`: **(高级)** 等待挂起信号，可选择标签匹配（继承自 SuspendObjectStream）
- `resume()`: **(高级)** 恢复挂起的执行流程（继承自 SuspendObjectStream）
- `_wait_for_continue(tag: str | None = None)`: **(高级)** 与外部控制器配合使用的手动挂起点（继承自 SuspendObjectStream）

### 挂起与恢复方法详情

#### `wait_to_suspend(*tags: str, timeout: float | None = None)`

从外部独立任务中调用此方法，当`ChatObject`到达下一个挂起点时暂停执行。

**参数:**

- `*tags` (str): 可选的标签过滤器（作为位置参数传递）
  - 无标签（默认）: 匹配所有使用`@suspend`装饰的方法
  - 单个标签字符串: 仅匹配使用`@SuspendObjectStream.suspend_with_tag(tag)`装饰的方法
  - **标准标签**: 使用[SuspendEnum](SuspendEnum.md)值来指定内置断点：
    - `SuspendEnum.MEMORY.value`: 内存摘要前
    - `SuspendEnum.SINGLE_TOOL.value`: 每次工具调用前
    - `SuspendEnum.PRECOMPLE.value`: 模型完成前
    - `SuspendEnum.COMPLE.value`: 模型完成后
- `timeout` (float | None): 超时时间（秒），防止无限阻塞。如果为None，则无限等待。

**异常:**

- `asyncio.TimeoutError`: 如果在指定超时时间内未触发挂起，则抛出此异常
- `RuntimeError`: 如果已经在等待挂起，则抛出此异常

**示例:**

```python
from amrita_core import SuspendEnum

# 等待任意挂起点
await chat.wait_to_suspend(timeout=3.0)

# 等待特定的标准挂起点
await chat.wait_to_suspend(SuspendEnum.SINGLE_TOOL.value, timeout=5.0)

# 等待自定义标签
await chat.wait_to_suspend("custom_tag", timeout=2.0)
```

#### `resume()`

恢复挂起的`ChatObject`执行流程。继续执行直到下一个挂起点或完成当前操作。

**示例:**

```python
async def controller(chat_obj):
    await chat_obj.wait_to_suspend("checkpoint")
    print("已挂起，正在检查状态...")
    # 执行检查或修改
    chat_obj.resume()  # 恢复执行
```

#### `_wait_for_continue(tag: str | None = None)`

与外部控制器配合使用的手动挂起点，通常在自定义函数内部使用以实现细粒度的流程控制。

**参数:**

- `tag` (str | None): 可选的标签，用于精确匹配外部控制器的`wait_to_suspend(...)`调用

**行为:**

- 如果没有外部`wait_to_suspend()`调用等待或标签不匹配，则立即返回而不阻塞
- 如果外部控制器正在等待匹配的标签，则阻塞直到调用`resume()`

**示例:**

```python
from amrita_core import SuspendObjectStream

class MyProcessor:
    @SuspendObjectStream.suspend_with_tag("before_process")
    async def process_data(self, chat_obj: ChatObject, data: dict):
        result = await self.do_processing(data)
        return result
```

**详细说明请参阅**：[挂起与恢复机制](../concepts/suspend.md)

## 示例

```python
from amrita_core import ChatObject
from amrita_core.types import MemoryModel, Message

context = MemoryModel()
train = Message(content="You are a helpful assistant.", role="system")

# 带回调的示例（推荐用于 Web 场景）
async def callback_handler(message):
    print("Received:", message)

chat_with_callback = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump(),
    callback=callback_handler,
    queue_size=20,
    queue_timeout=10.0
)

# 替代方案：创建后设置回调
chat_without_callback = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump()
)
chat_without_callback.set_callback_func(callback_handler)

# 带自定义事件参数的示例
chat_with_event_params = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump(),
    hook_args=("custom_arg1", "custom_arg2"),
    hook_kwargs={"custom_key": "custom_value"},
    exception_ignored=(ValueError, TypeError)
)

# 带自定义 Jinja2 变量的示例
chat_with_jinja2_vars = ChatObject(
    context=context,
    session_id="session_123",
    user_input="Hello!",
    train=train.model_dump(),
    jinja2_vars={"custom_role": "AI expert", "company_name": "Amrita Corp"}
)

# ❌ 无效 - 这将导致 TypeError：
# chat_with_override = ChatObject(
#     context=context,
#     session_id="session_123",
#     user_input="Hello!",
#     train=train.model_dump(),
#     jinja2_vars={"config": {"custom_setting": "value"}}  # 错误：'config' 是内置参数
# )
```

## 描述

ChatObject 类负责处理单个聊天会话，包括消息接收、上下文管理、模型调用和响应发送。它是 AmritaCore 框架中处理对话的核心类之一。

### 回调机制

回调机制继承自 SuspendObjectStream，工作方式如下：

1. 当提供回调函数时，响应直接传递给回调函数而不是排队
2. 这可以防止内存堆积和潜在的溢出问题
3. 回调函数以异步方式执行，并具有适当的锁定以确保线程安全

当未提供回调时，使用传统的基于队列的流式机制，AnyIO 的内存对象流提供内置的背压处理。

### 事件参数注入

`hook_args`、`hook_kwargs` 和 `exception_ignored` 参数允许向事件处理器注入自定义参数。当触发 `PreCompletionEvent` 或 `CompletionEvent` 等事件时，这些参数会传递给注册的事件处理器，使它们能够访问额外的上下文信息，并根据特定聊天会话的需求自定义其行为。

### Jinja2 模板变量

`jinja2_vars` 参数允许您向 Jinja2 模板系统传递自定义变量。这些变量在模板渲染期间**直接解包**（使用 `**self.jinja2_vars`），这意味着：

1. **直接变量访问**：`jinja2_vars` 字典中的键可以直接作为模板变量访问（例如，`{"role": "expert"}` 使得 `role` 在模板中可用）
2. **无变量覆盖**：**重要**：您不能在 `jinja2_vars` 中使用与内置变量名（`train`、`memory`、`chatobj`、`config`）匹配的键。这样做会导致 `TypeError`，因为 Python 不允许在函数调用中使用重复的关键字参数。
3. **保留关键字**：键 `'self'` 是保留关键字，不能在 `jinja2_vars` 中使用

这种设计为模板自定义提供了最大的灵活性，同时通过防止与内置变量的意外冲突来保持安全性。

### 参数

- **`train`** (`dict[str, str] | Message[str]`): 定义Agent行为的系统消息或训练数据
- **`user_input`** (`str | list[TextContent | ImageContent]`): 用户输入消息
- **`context`** (`MemoryModel | None`): 对话内存上下文（可选）
- **`session_id`** (`str`): 对话会话的唯一标识符
- **`callback`** (`Callable[[str | MessageContent], Awaitable[Any]] | None`, 可选): 异步回调函数，在生成响应块时接收它们。默认为 `None`。
- **`config`** (`AmritaConfig | None`, 可选): 此聊天实例的配置。默认为全局配置。
- **`preset`** (`ModelPreset | None`, 可选): 模型预设配置。默认为会话或全局默认值。
- **`auto_create_session`** (`bool`, 可选): 如果会话不存在是否自动创建。默认为 `False`。
- **`train_template`** (`Template`, 可选): 用于格式化系统消息的Jinja2模板。默认为内置模板。
- **`jinja2_vars`** (`dict[str, Any] | None`, 可选): 传递给Jinja2模板系统的变量。
- **`agent_strategy`** (`type[AgentStrategy]`, 可选): Agent执行策略。默认为 `ReActAgentStrategy`。
- **`hook_args`** (`tuple[Any, ...]`, 可选): 传递给匹配器函数的参数。默认为空元组。
- **`hook_kwargs`** (`dict[str, Any] | None`, 可选): 传递给匹配器函数的关键字参数。
- **`exception_ignored`** (`tuple[type[BaseException], ...]`, 可选): 如果在匹配器函数中发生，应该重新抛出的异常类型。
- **`queue_size`** (`int`, 可选): 响应流的最大缓冲区大小。使用AnyIO的内存对象流与内置背压，而不是之前的双队列溢出机制。默认为 `45`。
- **`queue_timeout`** (`float | None`, 可选): 队列操作的超时时间（秒）。如果为 `None`，操作将无限等待。默认为 `10.0`。

### 流式响应处理

AmritaCore使用**AnyIO内存对象流**进行流式响应，提供内置的背压处理：

```python
# 处理流式响应
async for message in chat.get_response_generator():
    content = message if isinstance(message, str) else message.get_content()
    print(content, end="")
```

**AnyIO背压的关键特性**：

- **自动流量控制**：当消费者比生产者慢时，生产者会自动等待
- **单缓冲区**：使用单个缓冲区而不是带溢出的双队列
- **内存高效**：内置缓冲区大小限制防止无界内存增长
- **超时安全**：队列操作遵循 `queue_timeout` 参数

**注意**：之前的 `overflow_queue_size` 参数已被移除。所有背压现在都由AnyIO的单流机制处理。
