# AgentStrategy

AgentStrategy 抽象基类定义了 agent 应如何执行其工作流。

## 策略类别

- **'agent'**：使用 `single_execute()` 方法进行逐步工具调用，由框架管理
- **'rag'**：使用 `run()` 方法，仅使用最小上下文
- **'workflow'**：使用 `run()` 方法，完全手动控制工具调用和上下文管理
- **'agent-mixed'**：使用 `single_execute()` 方法，可动态处理 RAG 和 Agent 模式

## 属性

- `session` (SessionData | None)：当前聊天会话关联的会话数据
- `tools_manager` (MultiToolsManager)：管理当前上下文中可用工具的管理器
- `chat_object` (ChatObject)：用于生成响应和管理对话流的聊天对象
- `ctx` (StrategyContext)：包含执行参数和配置的策略上下文

## 抽象方法

### get_category()

获取 agent 策略的类别。

**返回**：Literal["agent", "workflow", "rag", "agent-mixed"]

## 方法

### single_execute()

为 'agent' 和 'agent-mixed' 类别策略执行单步 agent 操作。框架处理循环管理、调用计数和终止条件。

**返回**：bool - 是否继续下一次执行

### run()

为 'rag' 和 'workflow' 类别策略运行完整的 agent 策略。

### call_tool(tool_call)

执行单个工具调用，不修改 agent 上下文。

**参数**：

- `tool_call` ([ToolCall](ToolCall.md))：包含函数名和参数的 ToolCall 对象

**返回**：str - 工具执行的字符串响应

### on_limited()

处理 agent 达到工具调用限制时的事件。

### on_exception(exc)

处理策略执行期间发生的异常。
