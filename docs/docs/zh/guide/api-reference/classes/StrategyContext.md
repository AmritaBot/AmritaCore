# StrategyContext

StrategyContext 类为 agent 策略提供执行上下文。

这个 dataclass 包含 agent 策略执行工作流所需的全部信息，包括用户输入、消息上下文
，以及 DI（依赖注入）资源字段。

> **v0.12.6**：DI 资源字段（`preset`、`config`、`tools_manager`、`io_stream`、
> `train_content`、`stream_id`、`usage`）现在可直接在 `StrategyContext` 上使用。
> 策略应优先使用这些字段，而不是穿透 `chat_object` 获取。`chat_object` 仍是该对话
> 的核心生命周期管理器句柄——它**并未弃用**。

## 属性

### 核心字段

- `user_input` (USER_INPUT)：用户的输入
- `original_context` (SendMessageWrap)：原始消息上下文，包含系统消息、记忆与用户查询

### DI 资源字段（自 v0.12.6 起为推荐路径）

- `preset` ([ModelPreset](ModelPreset.md) | None)：聊天的模型预设（默认：`None`）
- `config` ([AmritaConfig](AmritaConfig.md) | None)：配置设置（默认：`None`）
- `tools_manager` (`ToolsManager` | None)：可用工具的管理器（默认：`None`）
- `io_stream` (SuspendObjectStream | None)：用于产出响应的流式 I/O 接口（默认：`None`）
- `train_content` (str | None)：系统/训练提示词内容字符串（默认：`None`）
- `stream_id` (str | None)：唯一流标识符（默认：`None`）
- `usage` (`SessionUsageProxy` | None)：运行级用量账本（默认：`None`）

### 核心引用字段

- `chat_object` ([ChatObject](ChatObject.md) | None)：当前对话的**核心生命周期管理器句柄**——ChatObject 是一次对话的基本单元。当资源未被直接注入时，可通过它获取。（在新式 DI 工作流中默认：`None`）

### `message`

`original_context` 的属性别名，带类型校验的 setter（赋值非 `SendMessageWrap` 会抛
`TypeError`）。

## 构造函数参数

- `user_input` (USER_INPUT)：用户的输入
- `original_context` (SendMessageWrap)：原始消息上下文
- `chat_object` ([ChatObject](ChatObject.md) | None, optional)：当前对话的核心生命周期管理器句柄。资源未被注入时会回退到它。（默认：`None`）
- `preset` ([ModelPreset](ModelPreset.md) | None, optional)：模型预设（默认：`None`）
- `config` ([AmritaConfig](AmritaConfig.md) | None, optional)：配置（默认：`None`）
- `tools_manager` (`ToolsManager` | None, optional)：工具管理器（默认：`None`）
- `io_stream` (SuspendObjectStream | None, optional)：I/O 流（默认：`None`）
- `train_content` (str | None, optional)：训练内容（默认：`None`）
- `stream_id` (str | None, optional)：流 ID（默认：`None`）
- `usage` (`SessionUsageProxy` | None, optional)：运行级用量账本（默认：`None`）

## 方法

### get_original_context()

获取原始消息上下文。

**返回**：[SendMessageWrap](SendMessageWrap.md) - 原始消息上下文

### get_user_input()

获取用户输入。

**返回**：USER_INPUT - 用户输入

## 使用示例

### 新式写法（自 v0.12.6 起推荐）

```python
from amrita_core.agent.context import StrategyContext

# DI 资源直接注入——不需要 chat_object
ctx = StrategyContext(
    user_input="What can you do?",
    original_context=message_context,
    preset=model_preset,
    config=amrita_config,
    tools_manager=tools_mgr,
    io_stream=stream,
    train_content="You are a helpful assistant.",
    stream_id="session_abc123",
    usage=usage_tracker,
)

# 策略通过 _StrategyBase 的便捷属性访问 DI 字段：
#   self.preset、self.config、self.io_stream 等
# （详见 agent-strategy 文档）

user_msg = ctx.get_user_input()
message_context = ctx.get_original_context()
```

### 旧式写法（仍然支持）

```python
from amrita_core.agent.context import StrategyContext

# chat_object 是生命周期管理器句柄；DI 字段未注入时资源回退到它
ctx = StrategyContext(
    user_input="What can you do?",
    original_context=message_context,
    chat_object=chat_obj,
)

user_msg = ctx.get_user_input()
message_context = ctx.get_original_context()
```
