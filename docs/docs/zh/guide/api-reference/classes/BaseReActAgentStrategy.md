# BaseReActAgentStrategy

`BaseReActAgentStrategy` 是一个用于ReAct Agent策略的抽象基类，为统一执行流程实现了模板方法模式。

此类为ReAct风格的Agent提供共享功能，包括工具调用编排、推理消息生成、循环检测和通用错误处理模式。

## 继承关系

- 继承自: [AgentStrategy](AgentStrategy.md)
- 抽象基类: 是

## 属性

- `agent_last_step` (str | None): 跟踪最后的推理步骤或执行的操作
- `call_count` (int): 工具调用迭代计数器
- `tools` (list[Any]): Agent可用的工具列表
- `origin_msg` (str): 原始用户消息内容
- `origin_instruction` (str): 来自训练上下文的系统指令
- `reasoning_pc` (int): 用于循环检测的推理过程计数器
- `_suggested_stop` (bool): 指示是否将tool_choice切换到自动模式的标志

## 构造函数参数

- `ctx` ([StrategyContext](StrategyContext.md)): 包含chat_object、配置和消息上下文的策略上下文

## 模板方法模式

`BaseReActAgentStrategy` 实现了模板方法模式，其中通用执行流程在 `_execute_tool_loop()` 中定义，但策略特定的行为被委托给抽象方法：

### 抽象方法（必须由子类实现）

#### \_append_tool_result_to_context()

将工具结果附加到上下文（策略特定）。

**参数**:

- `tool_call` ([ToolCall](ToolCall.md)): 工具调用对象
- `func_response` (str): 函数执行结果
- `response_msg` ([UniResponse](UniResponse.md)): 原始响应消息

#### \_handle_error_append()

处理将错误消息附加到上下文（策略特定）。

**参数**:

- `function_name` (str): 失败函数的名称
- `error_content` (str): 要附加的格式化错误消息
- `tool_call_id` (str): 工具调用的ID
- `original_exception` (BaseException): 用于类型处理的原始异常对象

#### \_append_reasoning()

将推理内容附加到上下文（策略特定）。

**参数**:

- `response` ([UniResponse](UniResponse.md)): 包含推理工具调用的来自tools_caller的响应

### 具体方法（可由子类重写）

#### \_build_stop_response()

构建停止工具响应消息。

**参数**:

- `function_args` (dict[str, Any]): 传递给停止工具的参数

**返回**: str - 用于最终答案生成的指令消息

#### \_check_and_handle_loop_reasoning()

检查是否超过循环推理阈值并构建提示。

**返回**: str | None - 如果超过阈值则返回循环检测提示，否则返回None

#### \_notify_tool_calls()

向用户发送工具调用完成通知。

**参数**:

- `result_msg_list` (list[[ToolResult](ToolResult.md)]): 要通知的工具结果列表
- `function_name` (str): 被调用函数的名称
- `tool_call_id` (str): 工具调用的ID

#### \_handle_loop_reasoning_cleanup()

在检测到循环推理时清理策略特定状态。

**参数**:

- `prompt` (str): 循环检测提示消息

#### \_build_stop_response_and_append()

构建停止响应并附加到消息列表（策略特定）。

**参数**:

- `function_args` (dict[str, Any]): 传递给停止工具的参数
- `response_msg` ([UniResponse](UniResponse.md)): 原始响应消息

## 使用方法

此类不应直接实例化。相反，应创建实现所需抽象方法的子类：

```python
from amrita_core.builtins.agent import BaseReActAgentStrategy

class MyCustomReActStrategy(BaseReActAgentStrategy):
    async def _append_tool_result_to_context(self, tool_call, func_response, response_msg):
        # 实现策略特定的工具结果处理
        pass

    async def _handle_error_append(self, function_name, error_content, tool_call_id, original_exception):
        # 实现策略特定的错误处理
        pass

    async def _append_reasoning(self, response):
        # 实现策略特定的推理处理
        pass

    @classmethod
    def get_category(cls):
        return "agent-mixed"
```

## 内置子类

- [ReActAgentStrategy](ReActAgentStrategy.md): 具有OpenAI兼容ToolCall-ToolResult配对的标准实现
- [HybridReActAgentStrategy](HybridReActAgentStrategy.md): 使用XML标签的MoE架构模型专用实现
