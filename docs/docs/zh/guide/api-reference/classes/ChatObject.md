# ChatObject

ChatObject 类是与 AI 对话的主要接口。它通过 `io_stream` 属性使用 `SuspendObjectStream[RESPONSE_TYPE]`（自 v0.9.1 起使用组合而非继承）来实现挂起/恢复和流式响应处理。

## 属性

### 身份标识

- `stream_id` (str)：聊天对象 ID（委托到 `_di_session`）
- `session_id` (str)：会话 ID（运行时由 `_di_session.session_id` 计算得出）

### 状态与后端

- `slot` ([BackendSlots](BackendSlots.md))：提供记忆和能力后端的后端槽位（委托到 `_di_ability.slot`）

### 时间

- `timestamp` (str)：时间戳（用于 LLM，委托到 `_di_session`）
- `time` (datetime)：创建时间（委托到 `_di_session`）
- `end_at` (datetime | None)：结束时间
- `last_call` (datetime)：上次内部函数调用时间
- `now_calling` (str | None)：当前正在调用的函数名

### 配置与预设

- `config` (AmritaConfig)：此调用中使用的配置（委托到 `_di_ability.config`，可设置）
- `preset` (ModelPreset)：此调用中使用的模型预设（委托到 `_di_ability.preset`，可设置）
- `strategy` (type[AgentStrategy] | StrategyLikedObject)：Agent 策略（委托到 `_di_agent.strategy`，可设置）

### 输入/数据

- `user_input` (USER_INPUT)：用户输入（委托到 `_di_input`）
- `data` ([MemoryModel](MemoryModel.md))：记忆模型（运行时由 `_di_memory.memory` 计算得出，可设置）
- `train` (Message[str])：系统消息（委托到 `_di_input.train`，可设置）
- `template` (Template)：Jinja2 模板（委托到 `_di_input`）
- `jinja2_vars` (dict[str, Any])：传递给模板系统的变量（委托到 `_di_input`）

### IO 流

- `io_stream` (SuspendObjectStream[RESPONSE_TYPE])：响应的流式接口

> **v0.12.0 变更**：以下字段已不再是 ChatObject 的直接属性，改由 DI 上下文对象管理：
>
> - `user_message` — 已移除；改用 `Message(role="user", content=chat_obj.user_input)`
> - `context_wrap` — 移至 `_di_working.context_wrap`（内部）
> - `response` — 移至 `_di_resp.response`（内部）
> - `extra_usage` — 移至 `_di_resp.extra_usage`（内部）
> - `_bke_opt` — 移至 `_di_opt`（内部）

## 构造函数参数

`train`、`user_input`、`session_id`、`config`、`preset` 为位置或关键字参数；`preset` 之后的全部参数为仅关键字参数。

- `train` (dict[str, str] | [Message](Message.md)[str])：给 AI 的训练/提示数据（系统提示词）
- `user_input` (str | Sequence[Content] | None)：用户输入消息
- `session_id` (str | None，可选)：会话唯一标识。**必填**：不带该参数构造 `ChatObject` 会抛出 `ValueError`。会话 ID 由后端用于加载/保存记忆与能力状态（默认：None）
- `config` ([AmritaConfig](AmritaConfig.md) | None，可选)：覆盖全局配置的本调用配置（默认：None）
- `preset` ([ModelPreset](ModelPreset.md) | None，可选)：本调用的模型预设（默认：None，运行时解析）
- `backend` ([BackendSlots](BackendSlots.md) | None，可选)：提供记忆和能力后端的后端槽位。为 None 时两个槽位都使用 `LegacyBackend`（默认：None）
- `chat_man` ([ChatManager](ChatManager.md) | None，可选)：本对象绑定的 `ChatManager`，默认为全局 `ChatManager`（默认：None）
- `train_template` (Template | str，可选)：用于格式化系统消息的 Jinja2 模板（默认：DEFAULT_TEMPLATE）
- `io_stream` (SuspendObjectStream[RESPONSE_TYPE] | None，可选)：外部 SuspendObjectStream 实例。为 None 时自动新建（默认：None）
- `jinja2_vars` (dict[str, Any] | None，可选)：传给模板系统的自定义变量（默认：None）。**注意**：字典中的键不得与内置变量名（`train`、`memory`、`chatobj`、`config`）冲突，否则会因重复关键字参数而抛出 TypeError
- `agent_strategy` (type[AgentStrategy] | `StrategyLikedObject`，可选)：执行所用的 Agent 策略。可传策略**类**（`type[AgentStrategy]`）或已初始化的策略**实例**（`StrategyLikedObject`），后者支持带内部状态机的有状态策略（默认：ReActAgentStrategy）
- `hook_args` (tuple[Any, ...]，可选)：触发事件时传给事件处理函数的位置参数（默认：空元组）
- `hook_kwargs` (dict[str, Any] | None，可选)：触发事件时传给事件处理函数的关键字参数（默认：None）
- `exception_ignored` (tuple[type[BaseException], ...]，可选)：在事件处理函数中应被忽略并重新抛出的异常类型（默认：空元组）
- `middleware` (Callable[[Self], Awaitable[Any]] | None，可选)：包裹整个工作流执行的异步中间件。设置后工作流引擎会改为委托给该中间件，而不是运行默认流水线。适合自定义编排、监控或横切关注点（默认：None）
- `archived_nodes` (SubprogramStorage | None，可选)：追加到工作流流水线末尾的额外节点子程序。用于在标准流水线完成后扩展自定义步骤。为 `None` 时默认使用 `amrita_sense.instructions` 的 `ARCHIVED_NODES`（默认：None）
- `backend_options` ([DatabackendOptions](DatabackendOptions.md) | None，可选)：控制后端拉取与提交行为的选项。可分别跳过记忆拉取、工具拉取、MCP 拉取、预设拉取、能力额外设置、记忆提交与计费提交（默认：None）
- `workflow` (NodeComposeRendered | None，可选)：用于替代默认流水线的预渲染工作流。提供后 ChatObject 使用此外部工作流图，而非构建内置流水线。**不能与 `archived_nodes` 同时使用**——同时提供会抛出 `ValueError`。可用的预组合工作流位于 `amrita_core.builtins.workflows`（如 `SIMPLE_REACT`、`REACT_ONLY`、`SIMPLE_CHAT`）。（默认：None）

## 核心方法

- `begin()`：启动聊天对象任务（返回 Self）
- `terminate()`：终止任务执行
- `full_response()`：以单个字符串形式返回队列中的完整响应
- `get_exception()`：获取任务执行期间发生的异常
- `is_running()`：检查任务是否正在运行
- `is_done()`：检查任务是否已完成
- `get_snapshot()`：以 `ChatObjectMeta` 形式获取聊天对象快照

## 挂起与恢复方法

#### `io_stream.wait_to_suspend(*tags: str, timeout: float | None = None)`

在独立的外部任务中调用此方法，可在 `ChatObject` 执行到达下一个挂起点时将其暂停。

**参数：**

- `*tags` (str)：可选的标签过滤（作为位置参数传入）
  - 不传标签（默认）：匹配所有被 `@suspend` 装饰的方法
  - 单个标签字符串：只匹配被 `@SuspendObjectStream.suspend_with_tag(tag)` 装饰的方法
  - **标准标签**：使用 [SuspendEnum](SuspendEnum.md) 值作为内置断点：
    - `SuspendEnum.MEMORY.value`：在两个记忆变更节点（`COMPACT` 与 `APPEND_RESPONSE`）
    - `SuspendEnum.SINGLE_TOOL.value`：每次工具调用之前
    - `SuspendEnum.PRECOMPLE.value`：模型完成之前
    - `SuspendEnum.COMPLE.value`：模型完成之后
- `timeout` (float | None)：超时秒数，避免无限阻塞。为 None 时无限等待。

**异常：**

- `asyncio.TimeoutError`：在指定超时内未触发挂起时抛出
- `RuntimeError`：已在等待挂起时抛出

**示例：**

```python
from amrita_core import SuspendEnum

# 等待任意挂起点
await chat.io_stream.wait_to_suspend(timeout=3.0)

# 等待特定标准挂起点
await chat.io_stream.wait_to_suspend(SuspendEnum.SINGLE_TOOL.value, timeout=5.0)

# 等待自定义标签
await chat.io_stream.wait_to_suspend("custom_tag", timeout=2.0)
```

#### `io_stream.resume()`

恢复被挂起的执行流。继续执行直到下一个挂起点，或完成当前操作。

**示例：**

```python
async def controller(chat_obj):
    await chat_obj.io_stream.wait_to_suspend("checkpoint")
    print("Suspended, inspecting state...")
    # 执行检查或修改
    chat_obj.io_stream.resume()  # 恢复执行
```

#### `io_stream._wait_for_continue(tag: str | None = None)`

手动挂起点，通常在自定义函数内部使用，以便与外部控制器配合实现细粒度的流程控制。

**参数：**

- `tag` (str | None)：可选标签，用于与外部控制器的 `wait_to_suspend(...)` 调用精确匹配

**行为：**

- 若没有待处理的外部 `wait_to_suspend()` 调用，或标签不匹配，则立即返回不阻塞
- 若外部控制器正在等待匹配的标签，则阻塞直到调用 `resume()`

**示例：**

```python
from amrita_core import SuspendObjectStream


class MyProcessor:
    @SuspendObjectStream.suspend_with_tag("before_process")
    async def process_data(self, io_stream: SuspendObjectStream, data: dict):
        result = await self.do_processing(data)
        return result
```

**详见**：[挂起与恢复机制](../../advanced/suspend.md)

## 示例

```python
from amrita_core import ChatObject
from amrita_core.types import Message

train = Message(content="You are a helpful assistant.", role="system")

# 基本用法（session_id 必填；后端默认为 LegacyBackend）
chat = ChatObject(
    train=train.model_dump(),
    user_input="Hello!",
    session_id="session_123",
)


# 使用回调的示例（Web 场景推荐）
async def callback_handler(message):
    print("Received:", message)


chat_with_callback = ChatObject(
    train=train.model_dump(),
    user_input="Hello!",
    session_id="session_123",
)
chat_with_callback.io_stream.set_callback_func(callback_handler)

# 使用自定义事件参数的示例
chat_with_event_params = ChatObject(
    train=train.model_dump(),
    user_input="Hello!",
    session_id="session_123",
    hook_args=("custom_arg1", "custom_arg2"),
    hook_kwargs={"custom_key": "custom_value"},
    exception_ignored=(ValueError, TypeError),
)
```

