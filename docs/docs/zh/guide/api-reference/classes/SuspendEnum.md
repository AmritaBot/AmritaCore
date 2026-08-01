# SuspendEnum

> **v0.12.0 迁移**：`SuspendEnum` 和 `BuiltinName` 已从 `amrita_core.chatmanager.enums` 移至 `amrita_core.enums`。

`SuspendEnum` 类为 AmritaCore 中的挂起/恢复机制提供标准化的断点标签。

## 枚举值

### `LOAD_STATE`

- **值**：`"ChatObject::load_state"`
- **描述**：从后端加载运行时状态时触发

### `ENTRY_POINT`

- **值**：`"ChatObject::_entry"`
- **描述**：ChatObject 执行开始时触发

### `TRAIN_RENDER`

- **值**：`"ChatObject::render_train_template"`
- **描述**：渲染 Jinja2 训练/提示词模板时触发

### `MEMORY`

- **值**：`"ChatObject::memory_limiting"`
- **描述**：上下文超出 token 限制时，在记忆摘要之前触发

### `MESSAGES_PREPARED`

- **值**：`"ChatObject::prepare_send_messages"`
- **描述**：消息列表准备完成但运行预完成匹配器之前触发

### `PRECOMPLE`

- **值**：`"matcher_call::pre_completion"`
- **描述**：发送消息给 LLM 完成之前触发

### `STRATEGY_START`

- **值**：`"ChatObject::run_strategy_start"`
- **描述**：agent 策略执行开始时触发

### `LLM_CALL`

- **值**：`"ChatObject::call_llm"`
- **描述**：实际 LLM API 调用期间触发
