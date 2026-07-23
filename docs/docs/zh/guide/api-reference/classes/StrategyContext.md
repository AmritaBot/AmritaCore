# StrategyContext

StrategyContext 类为 agent 策略提供执行上下文。

这个数据类包含 agent 策略执行其工作流所需的所有必要信息，包括用户输入、消息上下文和 DI（依赖注入）资源字段。

> **v0.12.6**：DI 资源字段（`preset`、`config`、`tools_manager`、`io_stream`、`train_content`、`stream_id`、`resp_extra_usage`）现在可直接在 `StrategyContext` 上使用。策略应优先使用这些字段，而非通过 `chat_object` 间接访问。`chat_object` 字段已**弃用**，将在未来版本中移除。

## 属性

### 核心字段

- `user_input` (USER_INPUT): 来自用户的输入
- `original_context` (SendMessageWrap): 包含系统消息、记忆和用户查询的原始消息上下文

### DI 资源字段（自 v0.12.6 起推荐使用）

- `preset` ([ModelPreset](ModelPreset.md) \| None): 模型预设（默认：`None`）
- `config` ([AmritaConfig](AmritaConfig.md) \| None): 配置设置（默认：`None`）
- `tools_manager` ([ToolsManager](ToolsManager.md) \| None): 可用工具管理器（默认：`None`）
- `io_stream` (SuspendObjectStream \| None): 用于生成响应的流式 I/O 接口（默认：`None`）
- `train_content` (str \| None): 系统/训练提示内容字符串（默认：`None`）
- `stream_id` (str \| None): 唯一流标识符（默认：`None`）
- `resp_extra_usage` ([UniResponseUsage](UniResponseUsage.md) \| None): 响应用量统计累加器（默认：`None`）

### 遗留字段（已弃用）

- `chat_object` ([ChatObject](ChatObject.md) \| None): **（已弃用）** 聊天对象的遗留引用。请改用上述 DI 资源字段。在新式 DI 工作流中默认为 `None`。

## 构造函数参数

- `user_input` (USER_INPUT): 来自用户的输入
- `original_context` (SendMessageWrap): 原始消息上下文
- `chat_object` ([ChatObject](ChatObject.md) \| None, 可选): **（已弃用）** 聊天对象引用。在新式工作流中设为 `None`，DI 字段直接提供。（默认：`None`）
- `preset` ([ModelPreset](ModelPreset.md) \| None, 可选): 模型预设（默认：`None`）
- `config` ([AmritaConfig](AmritaConfig.md) \| None, 可选): 配置（默认：`None`）
- `tools_manager` ([ToolsManager](ToolsManager.md) \| None, 可选): 工具管理器（默认：`None`）
- `io_stream` (SuspendObjectStream \| None, 可选): I/O 流（默认：`None`）
- `train_content` (str \| None, 可选): 训练内容（默认：`None`）
- `stream_id` (str \| None, 可选): 流 ID（默认：`None`）
- `resp_extra_usage` ([UniResponseUsage](UniResponseUsage.md) \| None, 可选): 额外用量累加器（默认：`None`）

## 方法

### get_original_context()

获取原始消息上下文。

**返回**: [SendMessageWrap](SendMessageWrap.md) - 原始消息上下文

### get_user_input()

获取用户输入。

**返回**: USER_INPUT - 用户输入

## 使用示例

### 新式用法（自 v0.12.6 起推荐）

```python
from amrita_core.agent.context import StrategyContext

# DI 资源直接注入 — 无需 chat_object
ctx = StrategyContext(
    user_input="你能做什么？",
    original_context=message_context,
    preset=model_preset,
    config=amrita_config,
    tools_manager=tools_mgr,
    io_stream=stream,
    train_content="你是一个有用的助手。",
    stream_id="session_abc123",
    resp_extra_usage=usage_tracker,
)

# 策略通过 _StrategyBase 便利属性访问 DI 字段：
#   self.preset, self.config, self.io_stream 等
# （详见 agent-strategy 文档）

user_msg = ctx.get_user_input()
message_context = ctx.get_original_context()
```

### 遗留用法（仍支持）

```python
from amrita_core.agent.context import StrategyContext

# 遗留路径 — chat_object 仍然可用但已弃用
ctx = StrategyContext(
    user_input="你能做什么？",
    original_context=message_context,
    chat_object=chat_obj
)

user_msg = ctx.get_user_input()
message_context = ctx.get_original_context()
```
