# AgentStrategy

AgentStrategy 抽象基类定义了 agent 应如何执行其工作流。

该类为不同类型的 agent 执行策略提供统一接口，使系统能够支持多种 agent 模式（基础
工具调用、RAG、复杂工作流）。

## 策略类别

不同策略类别有不同的执行模式：

- **'agent'**：使用 `single_execute()` 方法进行逐步工具调用，由框架管理
- **'rag'**：使用 `run()` 方法，仅使用最小上下文（只有系统消息与用户查询）
- **'workflow'**：使用 `run()` 方法，完全手动控制工具调用和上下文管理
- **'agent-mixed'**：使用 `single_execute()` 方法，可动态处理 RAG 和 Agent 模式

## 属性

- `session` (SessionData | None)：当前聊天会话关联的会话数据，不可用时为 None
- `tools_manager` (MultiToolsManager)：管理当前上下文中可用工具的管理器
- `chat_object` (ChatObject)：用于生成响应和管理对话流的聊天对象
- `ctx` (StrategyContext)：包含执行参数和配置的策略上下文

## 构造函数参数

- `ctx` ([StrategyContext](StrategyContext.md))：策略上下文，包含 chat_object、配置与消息上下文

## 抽象方法

### get_category()

获取 agent 策略的类别。

**返回**：Literal["agent", "workflow", "rag", "agent-mixed"] - 策略类别字面量，表示执行模式。

## 方法

### single_execute()

为 'agent' 和 'agent-mixed' 类别策略执行单步 agent 操作。

该方法由框架调用，用于执行一轮工具调用。框架负责循环管理、调用计数与终止条件。

**返回**：bool - 应继续下一次执行则返回 `True`，应停止则返回 `False`。

**注意**：该方法用于 'agent' 与 'agent-mixed' 类别策略。'rag' 与 'workflow' 类别
策略应改为实现 `run()`。

### run()

为 'rag' 和 'workflow' 类别策略运行完整的 agent 策略。

该方法把工具调用迭代、上下文构建、错误处理与响应生成的完整控制权交给策略实现。

**注意**：该方法用于 'rag' 与 'workflow' 类别策略。'agent' 与 'agent-mixed' 类别
策略应改为实现 `single_execute()`。

### call_tool(tool_call)

执行单个工具调用，不修改 agent 上下文。

这是工具执行的统一接口：处理给定工具调用并返回其响应。除工具本身通过传入的
ToolContext 所做的事情外，它不会改动 agent 的内部状态或上下文。该方法确保
AmritaCore 的工具接口在所有策略实现中保持一致。

**参数**：

- `tool_call` (`ToolCall`)：包含函数名和参数的 ToolCall 对象

**返回**：str - 工具执行的字符串响应；工具返回 None 时返回一条默认消息

**抛出**：RuntimeError - 在工具管理器中找不到所请求的工具时

### on_limited()

处理 agent 达到工具调用限制时的事件。

当 agent 策略达到框架配置的最大允许工具调用次数时，会调用该方法。

### on_exception(exc)

处理策略执行期间发生的异常。

**参数**：

- `exc` (BaseException)：执行期间发生的异常

### on_post_process()

执行后钩子，在所有 agent 步骤成功完成后调用。

该方法对**所有策略类别**（`"agent"`、`"rag"`、`"workflow"`、`"agent-mixed"`）
都会调用，且仅在执行无异常完成时调用。

**返回**：None

**用途**：该钩子可用于做最终的上下文修改、追加完成指令，或在生成最终响应前执行清理
操作。

```python
async def on_post_process(self) -> None:
    """成功执行 agent 后调用"""
    if self.call_count >= 2:  # 仅在确实调用过工具时
        self.ctx.message.append(
            Message(
                role="user",
                content="<END_OF_PROCESS>\nPlease answer me directly based on the information we got before.\n<END_OF_PROCESS>",
            )
        )
```
