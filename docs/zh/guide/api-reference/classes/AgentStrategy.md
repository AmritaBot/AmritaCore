# AgentStrategy

AgentStrategy 抽象基类定义了 agent 应如何执行其工作流。

该类为不同类型的 agent 执行策略提供了统一接口，允许系统支持各种 agent 模式（基本工具调用、RAG、复杂工作流）。

## 策略类别

不同的策略类别具有不同的执行模式：

- **'agent'**: 使用 `single_execute()` 方法进行逐步工具调用，由框架管理
- **'rag'**: 使用 `run()` 方法，使用最小上下文（仅系统消息和用户查询）
- **'workflow'**: 使用 `run()` 方法，对工具调用和上下文管理具有完全手动控制
- **'agent-mixed'**: 使用 `single_execute()` 方法，但可以动态处理 RAG 和 Agent 模式

## 属性

- `session` (SessionData | None): 与当前聊天会话关联的会话数据，如果不可用则为 None
- `tools_manager` (MultiToolsManager): 用于处理当前上下文中可用工具的管理器
- `chat_object` (ChatObject): 用于生成响应和管理对话流的聊天对象
- `ctx` (StrategyContext): 包含执行参数和配置的策略上下文

## 构造函数参数

- `ctx` ([StrategyContext](StrategyContext.md)): 包含 chat_object、配置和消息上下文的策略上下文

## 抽象方法

### get_category()

获取 agent 策略的类别。

**返回**: Literal["agent", "workflow", "rag", "agent-mixed"] - 策略类别，作为指示执行模式的字面量字符串。

## 方法

### single_execute()

为 'agent' 和 'agent-mixed' 类别策略执行单个 agent 步骤。

此方法由框架调用以执行一次工具调用迭代。框架处理循环管理、调用计数和终止条件。

**返回**: bool - 如果应继续下一次执行则返回 True，否则返回 False。

**注意**: 此方法由 'agent' 和 'agent-mixed' 类别策略使用。'rag' 和 'workflow' 类别策略应实现 `run()` 方法。

### run()

为 'rag' 和 'workflow' 类别策略运行完整的 agent 策略。

此方法将完全控制权交给策略实现，用于管理工具调用迭代、上下文构建、错误处理和响应生成。

**注意**: 此方法由 'rag' 和 'workflow' 类别策略使用。'agent' 和 'agent-mixed' 类别策略应实现 `single_execute()` 方法。

### call_tool(tool_call)

执行单个工具调用而不修改 agent 的上下文。

这是一个统一的工具执行接口，用于处理给定的工具调用并返回其响应。它不会改变 agent 的内部状态或上下文，除了工具本身可能通过提供的 ToolContext 所做的操作。此方法确保 AmritaCore 在所有策略实现中的工具接口一致性。

**参数**:

- `tool_call` ([ToolCall](ToolCall.md)): 包含函数名称和参数的 ToolCall 对象

**返回**: str - 工具执行的字符串响应，如果工具返回 None 则返回默认消息

**抛出**: RuntimeError - 如果在工具管理器中找不到请求的工具

### on_limited()

处理 agent 达到其工具调用限制时的事件。

当 agent 策略达到框架配置的最大允许工具调用次数时，将调用此方法。

### on_exception(exc)

处理策略执行期间发生的异常。

**参数**:

- `exc` (BaseException): 执行期间发生的异常
