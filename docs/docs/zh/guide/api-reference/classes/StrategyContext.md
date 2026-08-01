# StrategyContext

StrategyContext 类为 agent 策略提供执行上下文。

> **v0.12.6**：DI 资源字段（`preset`、`config`、`tools_manager`、`io_stream`、`train_content`、`stream_id`、`resp_extra_usage`）现在可直接在 `StrategyContext` 上使用。`chat_object` 字段已**弃用**。

## 属性

### 核心字段

- `user_input` (USER_INPUT)：用户的输入
- `original_context` (SendMessageWrap)：原始消息上下文

### DI 资源字段（自 v0.12.6 起推荐）

- `preset` ([ModelPreset](ModelPreset.md) | None)：模型预设
- `config` ([AmritaConfig](AmritaConfig.md) | None)：配置设置
- `tools_manager` ([ToolsManager](ToolsManager.md) | None)：可用工具管理器
- `io_stream` (SuspendObjectStream | None)：流式 I/O 接口
- `train_content` (str | None)：系统/训练提示词内容
- `stream_id` (str | None)：唯一流标识符
- `resp_extra_usage` ([UniResponseUsage](UniResponseUsage.md) | None)：响应使用统计累加器

### 旧版字段（已弃用）

- `chat_object` ([ChatObject](ChatObject.md) | None)：**（已弃用）** 使用上面的 DI 资源字段代替。
