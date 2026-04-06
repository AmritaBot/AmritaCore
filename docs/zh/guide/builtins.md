# AmritaCore的内置能力

## 9.1 内置工具

AmritaCore 提供了几种内置工具，以支持智能体的核心行为。这些工具是框架内部定义的，在使用Agent策略时自动可用。

### 9.1.1 STOP_TOOL (停止工具)

`STOP_TOOL` 是一个内置工具，用于表示Agent已经收集到足够的信息，准备形成最终答案。当调用此工具时，Agent应该不再调用其他工具，而是直接提供完成的结果。

- **名称**: `agent_stop`
- **描述**: 调用此工具表示您已收集到足够的信息并准备向用户生成最终答案。调用后，您不应再调用任何其他工具，而应直接提供完成结果。
- **参数**:
  - `result` (可选): 简要说明在聊天任务中完成了什么。

### 9.1.2 REASONING_TOOL (推理工具)

`REASONING_TOOL` 用于思考下一步应该做什么，通常在完成工具调用后调用此工具进行思考。这个工具对于实现智能体的自主决策至关重要。

- **名称**: `think_and_reason`
- **描述**: 思考下一步应该做什么，完成工具调用后始终调用此工具进行思考。
- **参数**:
  - `content`: 描述接下来要做的事情（必需）。

### 9.1.3 PROCESS_MESSAGE (处理消息工具)

`PROCESS_MESSAGE` 用于描述Agent当前正在执行的操作，并向用户表达Agent的内部想法。当需要向用户传达当前操作或内部推理时使用此工具，而不是用于一般性的完成。

- **名称**: `processing_message`
- **描述**: 描述Agent当前正在执行的操作并向用户表达内部想法。当需要向用户传达当前操作或内部推理时使用此工具，而不是用于一般性的完成。
- **参数**:
  - `content`: 消息内容，以系统指令的语气描述正在执行的操作或与用户的交互（必需）。

### 9.1.4 内置工具配置

内置工具根据Agent配置自动启用：

- **Agent模式**: 当 `config.builtin.tool_calling_mode == "agent"` 时，`STOP_TOOL` 和 `REASONING_TOOL` 均可用。
- **思维模式**: 只有当 `config.builtin.agent_thought_mode` 以"reasoning"开头时，`REASONING_TOOL` 才可用。
- **处理消息**: 当 `config.function_config.agent_middle_message` 为True时，`PROCESS_MESSAGE` 工具被启用。

## 9.2 内置适配器

AmritaCore 提供了多个LLM提供商的内置适配器，实现了 `ModelAdapter` 接口。

### 9.2.1 OpenAIAdapter

`OpenAIAdapter` 是主要的模型适配器，实现了与OpenAI API及兼容端点的通信协议。

**功能特性**：

- **API调用**: 异步调用OpenAI兼容API以获取聊天响应
- **流式响应**: 支持流式响应，实现实时内容输出和使用统计
- **工具调用**: 完全支持OpenAI的函数调用功能，具有适当的工具选择处理
- **使用统计**: 跟踪API调用使用信息，包括令牌计数
- **错误处理**: 具有可配置重试逻辑的健壮错误处理

**支持的协议**: `"openai"`, `"__main__"`

### 9.2.2 AnthropicAdapter (实验性)

`AnthropicAdapter` 为Anthropic的Claude模型提供实验性支持。

**功能特性**：

- **API调用**: 异步调用Anthropic API
- **流式响应**: 支持带有消息流处理的流式响应
- **令牌跟踪**: 为Anthropic的使用模型提供适当的输入/输出令牌跟踪
- **消息过滤**: 自动过滤无效消息（content=None的assistant消息和所有tool消息），以符合Anthropic API要求

**支持的协议**: `"anthropic"`, `"claude"`

**注意**: 此适配器为实验性，与OpenAI适配器相比可能功能有限。

## 9.3 内置Agent系统

AmritaCore包含一个全面的智能Agent系统，能够自主使用工具完成任务。该系统通过**模板方法模式**架构得到了显著增强，提供了统一的执行流程，同时允许策略特定的自定义。

### 9.3.1 BaseReActAgentStrategy (抽象基类)

`BaseReActAgentStrategy` 是实现ReAct风格Agent模板方法模式的抽象基类。它提供共享功能包括：

- **工具调用编排**和执行流程控制
- **推理消息生成**和处理
- **循环检测和恢复机制**（检测过多的重复推理调用）
- **工具调用通知处理**，具有可配置的用户通知
- **通用错误处理模式**，具有适当的异常管理
- **统一的停止状态管理**，通过 `_suggested_stop` 标志

这个抽象类定义了所有ReAct风格策略继承的通用执行框架，确保行为一致性，同时通过抽象方法允许自定义。

### 9.3.2 ReActAgentStrategy

`ReActAgentStrategy` 是标准实现，继承自 `BaseReActAgentStrategy` 并实现 `"agent-mixed"` 类别，支持在同一执行框架内同时进行检索增强生成（RAG）和迭代工具调用。

**主要特性**：

- **动态模式切换**: 根据配置自动在RAG和Agent模式之间适应
- **内置工具集成**: 无缝集成所有内置工具（`STOP_TOOL`、`REASONING_TOOL`、`PROCESS_MESSAGE`）
- **标准ToolCall-ToolResult配对**: 严格遵守OpenAI兼容的消息格式
- **推理支持**: 可选的推理步骤生成，用于工具执行前
- **错误处理**: 全面的错误处理，具有用户通知
- **会话管理**: 具有内存保留的完整会话状态管理

**配置选项**：

- **工具调用模式**: 通过 `config.builtin.tool_calling_mode` 配置（`"agent"`、`"rag"`、`"none"`）
- **思维模式**: 通过 `config.builtin.agent_thought_mode` 配置（`"reasoning"`、`"reasoning-required"`等）
- **工具调用限制**: 通过调用计数自动防止无限循环
- **中间消息**: 控制处理消息和推理步骤的可见性
- **错误通知**: 可配置的错误报告给用户

### 9.3.3 HybridReActAgentStrategy

`HybridReActAgentStrategy` 是一种专门针对**混合专家（MoE）架构模型**优化的Agent策略。它解决了某些MoE模型在区分工具和完成标识符时内部状态机的模糊性问题。

**关键特性**：

- **ToolCall触发**: 通过标准ToolCall机制启动工具执行
- **基于上下文的集成**: 将工具结果作为纯文本消息附加，而不是结构化的ToolResult对象，避免MoE模型状态模糊
- **XML标签格式**: 使用 `<TOOL_CALL>` 和 `<TOOL_RESULT>` XML标签表示工具交互
- **MoE特定优化**: 解决MoE模型在区分工具调用状态和完成状态时遇到的问题

**工具函数模式**：

```xml
<!-- 工具调用 -->
<TOOL_CALL name="tool">
    <PARAMS>
        <!-- 参数作为键值对传递 -->
        <PARAM name="param1">value1</PARAM>
    </PARAMS>
</TOOL_CALL>

<!-- 工具结果 -->
<TOOL_RESULT name="tool">
   工具执行结果内容
</TOOL_RESULT>
```

**已知限制和安全考虑**：

- **提示注入风险**: 将工具结果作为纯 `user` 消息附加可能会在工具输出不可信或未清理时使模型暴露于注入攻击
- **最小化清理**: 此策略仅提供基本的标签对转义，**不执行**语义级过滤或内容验证
- **安全责任**: 用户**必须**在生产环境中为工具结果实现全面的输入验证、语义分析和内容清理

### 9.3.4 NoActionAgentStrategy

`NoActionAgentStrategy` 是一个简单的工作流策略，不执行任何操作。当需要放弃工具调用过程时可以使用。

- **类别**: `"workflow"`
- **用例**: 当您需要完全跳过工具执行时
- **实现**: 空的 `run()` 方法，立即返回

### 9.3.5 Agent工作流和模板方法模式

内置Agent系统遵循使用模板方法模式的增强工作流：

1. **初始化**: 使用用户输入和对话历史创建策略上下文
2. **工具准备**: 根据配置确定可用工具
3. **推理阶段**（可选）: 如果配置了，则生成推理步骤
4. **工具执行循环**：
   - 基于模型决策调用工具
   - 根据策略特定逻辑处理结果
   - 循环检测防止无限推理循环
5. **后处理**: 调用 `on_post_process()` 钩子进行最终上下文修改
6. **完成**: 生成最终响应

模板方法模式确保步骤1-4和6在所有策略中遵循一致的流程，而步骤5（结果处理）和错误处理则根据策略实现进行自定义。

### 9.3.6 策略选择指南

根据您的用例选择合适的内置策略：

- **标准LLM提供商**（OpenAI、Anthropic等）: 使用 `ReActAgentStrategy`
- **MoE架构模型**（Mixtral、Qwen-MoE等）: 使用 `HybridReActAgentStrategy`
- **跳过工具执行**: 使用 `NoActionAgentStrategy`
- **自定义行为**: 扩展 `BaseReActAgentStrategy` 或实现您自己的 `AgentStrategy`

## 9.4 内置事件钩子

AmritaCore为常见场景提供内置事件钩子：

### 9.4.1 Cookie安全钩子

Cookie安全钩子自动检测模型响应中是否出现敏感Cookie值，并终止会话以防止数据泄露。

- **激活**: 当 `config.cookie.enable_cookie = True` 时启用
- **检测**: 扫描模型响应中的配置Cookie值
- **响应**: 检测到时终止会话并返回通用错误消息

### 9.4.2 后处理钩子

`on_post_process()` 钩子在策略执行成功后调用，可用于最终上下文修改或清理操作。

- **时机**: 在所有工具执行成功完成后调用
- **适用性**: 对**所有策略类别**（`"agent"`、`"rag"`、`"workflow"`、`"agent-mixed"`）都可用
- **用例**: 添加最终指令、上下文摘要或清理操作
