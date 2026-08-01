# ChatObject

ChatObject 类是与 AI 对话的主要接口。它通过 `io_stream` 属性使用 `SuspendObjectStream[RESPONSE_TYPE]`（自 v0.9.1 起使用组合而非继承）来实现挂起/恢复和流式响应处理。

## 属性

### 身份标识

- `stream_id` (str)：聊天对象 ID
- `session_id` (str)：会话 ID

### 状态与后端

- `slot` ([BackendSlots](BackendSlots.md))：提供记忆和能力后端的后端槽位
- `state` ([StateContext](StateContext.md))：运行时状态上下文

### 时间

- `timestamp` (str)：时间戳（用于 LLM）
- `time` (datetime)：创建时间
- `end_at` (datetime | None)：结束时间
- `last_call` (datetime)：上次内部函数调用时间
- `now_calling` (str | None)：当前正在调用的函数名

### 配置与预设

- `config` (AmritaConfig)：此调用中使用的配置
- `preset` (ModelPreset)：此调用中使用的模型预设
- `strategy` (type[AgentStrategy] | StrategyLikedObject)：Agent 策略

### 输入/数据

- `user_input` (USER_INPUT)：用户输入
- `data` ([MemoryModel](MemoryModel.md))：记忆模型
- `train` (Message[str])：系统消息
- `template` (Template)：Jinja2 模板
- `jinja2_vars` (dict[str, Any])：传递给模板系统的变量

### IO 流

- `io_stream` (SuspendObjectStream[RESPONSE_TYPE])：响应的流式接口

## 核心方法

- `begin()`：启动聊天对象任务（返回 Self）
- `terminate()`：终止任务执行
- `full_response()`：以单个字符串形式返回队列中的完整响应
- `get_exception()`：获取任务执行期间发生的异常
- `is_running()`：检查任务是否正在运行
- `is_done()`：检查任务是否已完成
