# ChatObject

ChatObject 类是与 AI 进行对话的主要接口。它通过 `io_stream` 属性使用 `SuspendObjectStream[RESPONSE_TYPE]`（自 v0.9.1 起采用组合方式替代继承），提供挂起/恢复功能和流式响应处理。

## 属性

### 标识

- `stream_id` (str): 聊天对象 ID（委托给 `_di_session`）
- `session_id` (str): 会话 ID（运行时从 `_di_session.session_id` 计算）

### 状态与后端

- `slot` ([BackendSlots](BackendSlots.md)): 提供记忆和能力后端的后端插槽（委托给 `_di_ability.slot`）
- `state` ([StateContext](StateContext.md)): 运行时状态上下文，包含记忆、能力和会话 ID。
  > **v0.12.0**: 现在是一个**兼容属性**——如果通过 setter 设置了 `StateContext`，则直接返回该实例；否则从 DI 组件（`_di_session`、`_di_memory`、`_di_ability`）合成一个新的对象。

### 时间

- `timestamp` (str): 时间戳（供 LLM 使用，委托给 `_di_session`）
- `time` (datetime): 创建时间（委托给 `_di_session`）
- `end_at` (datetime | None): 结束时间
- `last_call` (datetime): 最后一次内部函数调用时间
- `now_calling` (str | None): 当前调用的函数名

### 配置与预设

- `config` (AmritaConfig): 本次调用使用的配置（委托给 `_di_ability.config`，可写）
- `preset` (ModelPreset): 本次调用使用的模型预设（委托给 `_di_ability.preset`，可写）
- `strategy` (type[AgentStrategy] | StrategyLikedObject): Agent 策略（委托给 `_di_agent.strategy`，可写）

### 输入/数据

- `user_input` (USER_INPUT): 用户输入（委托给 `_di_input`）
- `data` ([MemoryModel](MemoryModel.md)): 记忆模型（运行时从 `_di_memory.memory` 计算，可写）
- `train` (Message[str]): 系统消息（委托给 `_di_input.train`，可写）
- `template` (Template): Jinja2 模板（委托给 `_di_input`）
- `jinja2_vars` (dict[str, Any]): 传递给模板系统的变量（委托给 `_di_input`）

### IO-Stream

- `io_stream` (SuspendObjectStream[RESPONSE_TYPE]): 响应的流式接口

> **v0.12.0 变更**：以下字段已从 ChatObject 直接属性中移除，转而通过 DI 上下文对象管理：
>
> - `user_message` — 已移除，使用 `Message(role="user", content=chat_obj.user_input)` 构造
> - `context_wrap` — 移至 `_di_working.context_wrap`（内部）
> - `response` — 移至 `_di_resp.response`（内部）
> - `extra_usage` — 移至 `_di_resp.extra_usage`（内部）
> - `_bke_opt` — 移至 `_di_opt`（内部）

## 构造函数参数

- `train` (dict[str, str] | [Message](Message.md)[str]): AI 的训练/提示数据（系统提示）
- `user_input` (str | Sequence[Content] | None): 用户输入消息
- `context` ([StateContext](StateContext.md) | None, 可选): 预构建的状态上下文。如果提供，则不能同时提供 `session_id`（互斥）。当两者都为 None 时，ChatObject 需要 `session_id` 在运行时创建新的 StateContext（默认：None）
- `session_id` (str | None, 可选): 会话的唯一标识符。如果提供，则不能同时提供 `context`（互斥）。会话 ID 由 Backend 用于加载/保存记忆和能力状态（默认：None）
- `preset` ([ModelPreset](ModelPreset.md) | None, 可选): 聊天的模型预设（默认：None，运行时解析）
- `backend` ([BackendSlots](BackendSlots.md) | None, 可选): 提供记忆和能力后端的后端插槽。如果为 None，则两个插槽都使用 `LegacyBackend`（默认：None）
- `config` ([AmritaConfig](AmritaConfig.md) | None, 可选): 聊天的配置设置，覆盖全局配置（默认：None）
- `io_stream` (SuspendObjectStream[RESPONSE_TYPE] | None, 可选): 外部 SuspendObjectStream 实例。如果为 None，则自动创建一个新的（默认：None）
- `agent_strategy` (type[AgentStrategy] | [StrategyLikedObject](StrategyLikedObject.md), 可选): 用于执行的 Agent 策略。接受策略**类**（`type[AgentStrategy]`）或预初始化的策略**实例**（`StrategyLikedObject`），后者支持有状态的策略（默认：ReActAgentStrategy）
- `train_template` (Template | str, 可选): 用于格式化系统消息的 Jinja2 模板（默认：DEFAULT_TEMPLATE）
- `jinja2_vars` (dict[str, Any] | None, 可选): 传递给模板系统的变量，用于自定义模板变量（默认：None）。**重要**：此字典中的键不能与内置变量名（`train`、`memory`、`chatobj`、`config`）匹配，否则会导致 TypeError，因为函数调用中不允许重复的关键字参数。
- `hook_args` (tuple[Any, ...], 可选): 触发事件时传递给事件处理器的位置参数（默认：空元组）
- `hook_kwargs` (dict[str, Any] | None, 可选): 触发事件时传递给事件处理器的关键字参数（默认：None）
- `exception_ignored` (tuple[type[BaseException], ...], 可选): 在事件处理器中应该被忽略并再次抛出的异常类型（默认：空元组）
- `middleware` (Callable[[Self], Awaitable[Any]] | None, 可选): 异步中间件函数，包装整个工作流执行。设置后，工作流引擎将执行委托给中间件而不是运行默认流水线。用于自定义编排、监控或横切关注点（默认：None）
- `archived_nodes` (SubprogramStorage | None, 可选): 附加到工作流流水线末尾的额外节点子程序。允许在标准流水线完成后使用自定义步骤扩展 ChatObject 执行。当为 `None` 时，默认为 `amrita_sense.instructions` 中的 `ARCHIVED_NODES`（默认：None）
- `backend_options` ([DatabackendOptions](DatabackendOptions.md) | None, 可选): 控制后端获取和提交行为的选项。允许选择性地跳过记忆获取、工具获取、MCP 获取、预设获取、能力额外设置和记忆提交（默认：None）
- `workflow` (NodeComposeRendered | None, 可选): 预渲染的工作流，用于替代默认流水线。提供后，ChatObject 使用此外部工作流图而非内置流水线。**不可与 `archived_nodes` 同时使用**——如果两者同时提供，将抛出 `ValueError`。支持的预组合工作流可在 `amrita_core.builtins.workflows` 中找到（如 `SIMPLE_REACT`、`REACT_ONLY`、`SIMPLE_CHAT`）。（默认：None）

## 方法

### 核心方法

- `begin()`: 启动聊天对象任务（返回 Self）
- `terminate()`: 终止任务执行
- `full_response()`: 以单一字符串形式返回完整响应
- `get_exception()`: 获取任务执行期间发生的异常
- `is_running()`: 检查任务是否正在运行
- `is_done()`: 检查任务是否已完成
- `get_snapshot()`: 获取聊天对象的快照（`ChatObjectMeta`）

### 挂起与恢复方法

#### `io_stream.wait_to_suspend(*tags: str, timeout: float | None = None)`

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
await chat.io_stream.wait_to_suspend(timeout=3.0)

# 等待特定的标准挂起点
await chat.io_stream.wait_to_suspend(SuspendEnum.SINGLE_TOOL.value, timeout=5.0)

# 等待自定义标签
await chat.io_stream.wait_to_suspend("custom_tag", timeout=2.0)
```

#### `io_stream.resume()`

恢复挂起的执行流程。继续执行直到下一个挂起点或完成当前操作。

**示例:**

```python
async def controller(chat_obj):
    await chat_obj.io_stream.wait_to_suspend("checkpoint")
    print("已挂起，正在检查状态...")
    # 执行检查或修改
    chat_obj.io_stream.resume()  # 恢复执行
```

#### `io_stream._wait_for_continue(tag: str | None = None)`

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
from amrita_core.types import Message

train = Message(content="You are a helpful assistant.", role="system")

# 基本用法（后端默认为 LegacyBackend）
chat = ChatObject(
    train=train.model_dump(),
    user_input="Hello!",
    session_id="session_123",
)

# 带回调的示例（推荐用于 Web 场景）
async def callback_handler(message):
    print("Received:", message)

chat_with_callback = ChatObject(
    train=train.model_dump(),
    user_input="Hello!",
    session_id="session_123",
)
chat_with_callback.io_stream.set_callback_func(callback_handler)

# 带自定义事件参数的示例
chat_with_event_params = ChatObject(
    train=train.model_dump(),
    user_input="Hello!",
    session_id="session_123",
    hook_args=("custom_arg1", "custom_arg2"),
    hook_kwargs={"custom_key": "custom_value"},
    exception_ignored=(ValueError, TypeError)
)

# 带自定义 Jinja2 变量的示例
chat_with_jinja2_vars = ChatObject(
    train=train.model_dump(),
    user_input="Hello!",
    session_id="session_123",
    jinja2_vars={"custom_role": "AI expert", "company_name": "Amrita Corp"}
)

# 带自定义 io_stream 的示例
from amrita_sense.streaming import SuspendObjectStream
custom_stream = SuspendObjectStream(queue_size=100, queue_timeout=30.0)
chat_with_custom_stream = ChatObject(
    train=train.model_dump(),
    user_input="Hello!",
    session_id="session_123",
    io_stream=custom_stream,
)

# 带预组合工作流的示例（v0.12.6+）
from amrita_core.builtins.workflows import SIMPLE_REACT

chat_with_workflow = ChatObject(
    train=train.model_dump(),
    user_input="你好！",
    session_id="session_123",
    workflow=SIMPLE_REACT,
)

# ❌ 无效 - 这将导致 TypeError：
# chat_with_override = ChatObject(
#     train=train.model_dump(),
#     user_input="Hello!",
#     session_id="session_123",
#     jinja2_vars={"config": {"custom_setting": "value"}}  # 错误：'config' 是内置参数
# )
```

## 描述

ChatObject 类负责处理单个聊天会话，包括消息接收、上下文管理、模型调用和响应发送。它是 AmritaCore 框架中处理对话的核心类之一。

### 回调机制

回调机制由 `io_stream` 属性（`SuspendObjectStream` 实例）提供，工作方式如下：

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

### 流式响应处理

AmritaCore使用**AnyIO内存对象流**进行流式响应，提供内置的背压处理：

```python
# 处理流式响应
async for message in chat.io_stream.get_response_generator():
    content = message if isinstance(message, str) else message.get_content()
    print(content, end="")
```

**AnyIO背压的关键特性**：

- **自动流量控制**：当消费者比生产者慢时，生产者会自动等待
- **单缓冲区**：使用单个缓冲区而不是带溢出的双队列
- **内存高效**：内置缓冲区大小限制防止无界内存增长
- **超时安全**：队列操作遵循 `queue_timeout` 参数

**注意**：之前的 `overflow_queue_size` 参数已被移除。所有背压现在都由AnyIO的单流机制处理。
