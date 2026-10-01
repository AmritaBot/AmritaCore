# BaseReActAgentStrategy

`BaseReActAgentStrategy` 是 ReAct agent 策略的抽象基类，实现了模板方法模式以统一执行流。

该类为 ReAct 风格 agent 提供共享功能，包括工具调用编排、推理消息生成、循环检测与通用错误处理模式。

## 继承

- 继承自：[AgentStrategy](AgentStrategy.md)
- 抽象基类：是

## 属性

- `agent_last_step` (str | None)：跟踪最后一次推理步骤或动作
- `call_count` (int)：工具调用迭代计数器
- `tools` (list[Any])：agent 可用工具的列表
- `origin_msg` (str)：原始用户消息内容
- `origin_instruction` (str)：来自训练上下文的系统指令
- `reasoning_pc` (int)：用于循环检测的推理过程计数器
- `_suggested_stop` (bool)：指示是否应将 tool_choice 切换为 auto 模式的标志

## 构造函数参数

- `ctx` ([StrategyContext](StrategyContext.md))：策略上下文，包含 chat_object、配置与消息上下文

## 模板方法模式

`BaseReActAgentStrategy` 实现了模板方法模式：通用执行流定义在 `_execute_tool_loop()`
中，而策略特有的行为委托给抽象方法：

### 抽象方法（子类必须实现）

#### `_append_tool_result_to_context()`

把工具结果追加到上下文（策略特有）。

**参数**：

- `tool_call` (`ToolCall`)：工具调用对象
- `func_response` (str)：函数执行结果
- `response_msg` (`UniResponse`)：原始响应消息

#### `_handle_error_append()`

处理向上下文追加错误消息（策略特有）。

**参数**：

- `function_name` (str)：失败函数的名称
- `error_content` (str)：要追加的格式化错误消息
- `tool_call_id` (str)：工具调用的 ID
- `original_exception` (BaseException)：用于基于类型处理的原始异常对象

#### `_append_reasoning()`

把推理内容追加到上下文（策略特有）。

**参数**：

- `response` (`UniResponse`)：来自 tools_caller 的响应，包含推理工具调用

### 具体方法（子类可覆写）

#### `_is_native_thinking_enabled()`

检查模型预设是否启用了原生思考。

原生思考（Claude Extended Thinking、OpenAI o 系列等）可能不支持强制的
`tool_choice`。启用时，`_resolve_tool_choice()` 会自动降级强制值，以避免 provider
报错。

**返回**：bool - 预设启用了原生思考则返回 True

#### `_resolve_tool_choice(desired: ToolChoice) -> ToolChoice`

解析要发给 provider 的**实际** `tool_choice`。

启用原生思考时，provider 可能拒绝强制值（`"required"` 或某个具体工具 schema）。此时
回退到 `"auto"`，转而依靠提示词指令来控制工具调用行为。

**参数**：

- `desired` (`ToolChoice`)：期望的 tool_choice 值

**返回**：ToolChoice - 要发送的实际 tool_choice 值

#### `_build_stop_response()`

构建 stop 工具响应消息。

**参数**：

- `function_args` (dict[str, Any])：传给 stop 工具的参数

**返回**：str - 用于生成最终答案的指令消息

#### `_check_and_handle_loop_reasoning()`

检查是否已超过循环推理阈值并构建提示词。

**返回**：str | None - 超过阈值时返回循环检测提示词，否则返回 None

#### `_notify_tool_calls()`

向用户发送工具调用完成通知。

**参数**：

- `result_msg_list` (list[`ToolResult`])：要通知的工具结果列表
- `function_name` (str)：被调用函数的名称
- `tool_call_id` (str)：工具调用的 ID

#### `_handle_loop_reasoning_cleanup()`

检测到循环推理时清理策略特有状态。

**参数**：

- `prompt` (str)：循环检测提示消息

#### `_build_stop_response_and_append()`

构建 stop 响应并追加到消息列表（策略特有）。

**参数**：

- `function_args` (dict[str, Any])：传给 stop 工具的参数
- `response_msg` (`UniResponse`)：原始响应消息

## 使用

该类不应直接实例化。应创建子类并实现所需的抽象方法：

```python
from amrita_core.builtins.agent import BaseReActAgentStrategy


class MyCustomReActStrategy(BaseReActAgentStrategy):
    async def _append_tool_result_to_context(
        self, tool_call, func_response, response_msg
    ):
        # 实现策略特有的工具结果处理
        pass

    async def _handle_error_append(
        self, function_name, error_content, tool_call_id, original_exception
    ):
        # 实现策略特有的错误处理
        pass

    async def _append_reasoning(self, response):
        # 实现策略特有的推理处理
        pass

    @classmethod
    def get_category(cls):
        return "agent-mixed"
```

## 内置子类

- [ReActAgentStrategy](ReActAgentStrategy.md)：标准实现，使用 OpenAI 兼容的 ToolCall-ToolResult 配对
