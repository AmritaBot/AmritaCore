# ChatObject

ChatObject 类是与 AI 进行对话的主要接口。

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
- `_response_queue` (asyncio.Queue[Any]): 响应队列
- `_overflow_queue` (asyncio.Queue[Any]): 溢出队列
- `_is_running` (bool): 是否正在运行
- `_is_done` (bool): 是否已完成
- `_task` (Task[None]): 任务
- `_has_task` (bool): 是否有任务
- `_err` (BaseException | None): 错误
- `_wait` (bool): 是否等待
- `_queue_done` (bool): 队列是否完成
- `_callback_fun` (RESPONSE_CALLBACK_TYPE): 用于处理响应的回调函数
- `_callback_lock` (Lock): 用于线程安全回调执行的锁

## 构造函数参数

- `context` ([MemoryModel](MemoryModel.md)): 对话的记忆上下文
- `session_id` (str): 会话的唯一标识符
- `user_input` (str): 用户的输入消息
- `train` (dict): AI 的训练/提示数据
- `callback` (RESPONSE_CALLBACK_TYPE): 可选的回调函数，用于直接处理响应（适用于 Web 场景）
- `config` (AmritaConfig): 覆盖全局配置的聊天配置设置
- `preset` (ModelPreset): 聊天的模型预设
- `auto_create_session` (bool): 如果会话不存在，是否自动创建（默认：False）
- `train_template` (Template): 用于格式化系统消息的 Jinja2 模板（默认：DEFAULT_TEMPLATE）
- `jinja2_vars` (dict[str, Any] | None): 传递给模板系统的变量，用于自定义模板变量（默认：None）。**重要**：此字典中的键必须 NOT 与内置变量名（`train`、`memory`、`chatobj`、`config`）匹配，否则会导致 TypeError，因为重复的关键字参数在 Python 中是不允许的。
- `agent_strategy` (type[AgentStrategy]): 用于执行的 Agent 策略（默认：ReActAgentStrategy）
- `hook_args` (tuple[Any, ...]): 触发事件时传递给事件处理器的位置参数（默认：空元组）
- `hook_kwargs` (dict[str, Any] | None): 触发事件时传递给事件处理器的关键字参数（默认：None）
- `exception_ignored` (tuple[type[BaseException], ...]): 在事件处理器中应该被忽略并重新抛出的异常类型（默认：空元组）
- `queue_size` (int): 主响应队列的大小（默认：25）
- `overflow_queue_size` (int): 溢出队列的大小（默认：45）

## 方法

- `begin()`: 执行对话
- `get_response_generator()`: 返回用于流式响应的异步生成器
- `full_response()`: 返回完整响应
- `set_callback_func(func: RESPONSE_CALLBACK_TYPE)`: 设置用于响应处理的回调函数
- `yield_response(response: RESPONSE_TYPE)`: 将响应发送到队列或回调函数

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
    overflow_queue_size=40
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

新的回调机制旨在防止在消费者可能跟不上生产者的情况下（例如 Web 应用程序）发生队列溢出。当提供回调函数时：

1. 响应直接传递给回调函数，而不是排队
2. 这可以防止内存堆积和潜在的溢出问题
3. 回调函数以异步方式执行，并具有适当的锁定以确保线程安全

当未提供回调时，使用传统的基于队列的流式机制，同时使用主队列和溢出队列来处理临时的消费者延迟。

### 事件参数注入

`hook_args`、`hook_kwargs` 和 `exception_ignored` 参数允许向事件处理器注入自定义参数。当触发 `PreCompletionEvent` 或 `CompletionEvent` 等事件时，这些参数会传递给注册的事件处理器，使它们能够访问额外的上下文信息，并根据特定聊天会话的需求自定义其行为。

### Jinja2 模板变量

`jinja2_vars` 参数允许您向 Jinja2 模板系统传递自定义变量。这些变量在模板渲染期间**直接解包**（使用 `**self.jinja2_vars`），这意味着：

1. **直接变量访问**：`jinja2_vars` 字典中的键可以直接作为模板变量访问（例如，`{"role": "expert"}` 使得 `role` 在模板中可用）
2. **无变量覆盖**：**重要**：您不能在 `jinja2_vars` 中使用与内置变量名（`train`、`memory`、`chatobj`、`config`）匹配的键。这样做会导致 `TypeError`，因为 Python 不允许在函数调用中使用重复的关键字参数。
3. **保留关键字**：键 `'self'` 是保留关键字，不能在 `jinja2_vars` 中使用

这种设计为模板自定义提供了最大的灵活性，同时通过防止与内置变量的意外冲突来保持安全性。
