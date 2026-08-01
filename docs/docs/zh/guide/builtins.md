# AmritaCore 内置能力

## 内置工具

AmritaCore 提供了多个内置工具以支持智能代理的核心行为。这些工具在框架内部定义，使用代理策略时自动可用。

### STOP_TOOL（停止工具）

`STOP_TOOL` 是一个内置工具，用于指示代理已收集到足够的信息，可以形成最终答案。调用此工具后，代理不应调用其他工具，而应直接提供完成结果。

- **名称**：`agent_stop`
- **描述**：调用此工具表示你已收集到足够的信息，准备向用户制定最终答案。调用后不应再调用其他工具，直接提供完成结果。
- **参数**：
  - `result`（可选）：简要说明在聊天任务期间完成了什么。

### REASONING_TOOL（推理工具）

`REASONING_TOOL` 用于思考接下来应该做什么，通常在完成工具调用后调用以反思下一步。

- **名称**：`think_and_reason`
- **描述**：思考接下来应该做什么，完成工具调用后始终调用此工具进行思考。
- **参数**：
  - `last_step`：你上一步做了什么（如果没有之前的步骤，请留空）。
  - `summary`：你在思考什么——当前关注点或意图的简要总结。

### PROCESS_MESSAGE（处理消息工具）

`PROCESS_MESSAGE` 用于向用户描述代理当前正在做什么，表达代理的内部想法。

- **名称**：`processing_message`
- **描述**：向用户描述代理当前正在做什么，表达代理的内部想法。
- **参数**：
  - `content`：消息内容，以系统指令的语气描述正在做什么。

### 内置工具配置

内置工具根据代理配置自动启用：

- **Agent 模式**：`config.builtin.tool_calling_mode == "agent"` 时，`STOP_TOOL` 和 `REASONING_TOOL` 均可用。
- **思考模式**：`REASONING_TOOL` 仅在 `config.builtin.agent_thought_mode` 以 "reasoning" 开头时可用。

## 内置元数据类型

> **自 v0.9.1 起**：新的 `amrita_core.builtins.types` 模块提供了类型化的元数据类（基于 `MessageMetadataPayload`），用于代理和钩子工作流中的结构化元数据。

| 类                                      | 用途                                     |
| --------------------------------------- | ---------------------------------------- |
| `AgentReasoningMetadata`                | 预解析推理摘要（`last_step`、`summary`） |
| `AgentToolCallMetadata`                 | 工具调用通知                             |
| `AgentLoopErrorMetadata`                | 循环检测错误                             |
| `AgentStructuredReasoningChunkMetadata` | 每步结构化 CoT 推理元数据                |
| `AgentReflectionMetadata`               | 推理后自我反思结果                       |
| `AgentToolPredictionMetadata`           | 结构化推理期间的工具预测                 |

## 内置适配器

AmritaCore 为多个 LLM 提供商提供内置适配器，实现 `amrita_core.base.adapter` 中的 `ModelAdapter` 接口。

### OpenAIAdapter

`OpenAIAdapter` 是实现与 OpenAI API 及兼容端点通信的主要模型适配器。

**功能**：异步 API 调用、流式响应、工具调用支持、使用统计跟踪、错误处理与可配置重试逻辑、推理/思考支持（通过 `ThinkingConfig`）、嵌入 API（`call_embed()`）。

**支持的协议**：`"openai"`、`"__main__"`

### AnthropicAdapter

> **可选依赖**：自 v0.9.0rc1 起，Anthropic SDK 为可选依赖。使用 `pip install amrita_core[anthropic]` 安装。

**功能**：异步 Anthropic API 调用、流式响应、token 跟踪、消息过滤（自动过滤无效消息以符合 Anthropic API 要求）、工具调用支持、扩展思考功能（通过 `ThinkingConfig`）。

**支持的协议**：`"anthropic"`、`"claude"`

## 内置代理系统

### BaseReActAgentStrategy（抽象基类）

`BaseReActAgentStrategy` 是实现了 ReAct 风格代理的模板方法模式的抽象基类。提供共享功能包括：

- 工具调用编排和执行流控制
- 推理消息生成和处理
- 循环检测与恢复机制
- 工具调用通知处理
- 通用错误处理模式

### ReActAgentStrategy

标准实现，继承自 `BaseReActAgentStrategy`，实现 `"agent-mixed"` 类别。

**关键特性**：动态模式切换、内置工具集成、标准 ToolCall-ToolResult 配对、推理支持、错误处理、会话管理。

### HybridReActAgentStrategy

针对**混合专家（MoE）架构模型**优化的专用策略。使用 `<TOOL_CALL>` 和 `<TOOL_RESULT>` XML 标签表示工具交互。

### NoActionAgentStrategy

简单的工作流策略，不执行任何操作。类别：`"workflow"`。

## 内置事件钩子

### Cookie 安全钩子

当 `config.cookie.enable_cookie = True` 时启用，自动检测模型响应中是否出现敏感 cookie 值，并终止会话以防止数据泄露。

### 后处理钩子

`on_post_process()` 钩子在策略成功执行后调用，可用于最终上下文修改或清理操作。适用于**所有策略类别**。

## 内置工作流（v0.12.6+）

AmritaCore 在 `amrita_core.builtins.workflows` 中提供预组合的工作流管道。

| 工作流         | 描述                                                                                                              |
| -------------- | ----------------------------------------------------------------------------------------------------------------- |
| `REACT_BLOCK`  | ReAct 循环块                                                                                                      |
| `SIMPLE_REACT` | 完整 ReAct 管道：`LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> REACT_BLOCK >> LLM_COMPLETION >> COMMIT_MEMORY` |
| `REACT_ONLY`   | 不含最终 LLM 调用的 ReAct 管道                                                                                    |
| `SIMPLE_CHAT`  | 纯聊天（无 agent）：`LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> LLM_COMPLETION >> COMMIT_MEMORY`             |

```python
from amrita_core import ChatObject
from amrita_core.builtins.workflows import SIMPLE_REACT, SIMPLE_CHAT

# 完整 ReAct agent 管道
chat = ChatObject(
    train={"role": "system", "content": "你是一个乐于助人的助手。"},
    user_input="今天天气怎么样？",
    session_id="session_123",
    workflow=SIMPLE_REACT,
)
```

> **重要**：`workflow` 和 `archived_nodes` 互斥——同时提供两者会引发 `ValueError`。两者都不提供时，使用内置的默认管道。
