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

- **API调用**: 异步调用OpenAI兼容API获取聊天回复
- **流式响应**: 支持流式响应以实现实时内容输出，并包含用量统计
- **工具调用**: 完全支持OpenAI的函数调用功能，具有适当的工具选择处理
- **用量统计**: 跟踪API调用用量信息，包括令牌计数
- **错误处理**: 具有可配置重试逻辑的健壮错误处理

**支持的协议**: `"openai"`, `"__main__"`

### 9.2.2 AnthropicAdapter (实验性)

`AnthropicAdapter` 提供对Anthropic Claude模型的实验性支持。

**功能特性**：

- **API调用**: 异步调用Anthropic API
- **流式响应**: 支持带有消息流处理的流式响应
- **令牌跟踪**: 针对Anthropic用量模型的正确输入/输出令牌跟踪

**支持的协议**: `"anthropic"`, `"claude"`

**注意**: 此适配器为实验性，与OpenAI适配器相比可能功能有限。

## 9.3 内置Agent系统

AmritaCore 包含一个全面的智能体系统，能够自主使用工具完成任务。

### 9.3.1 ReActAgentStrategy

`ReActAgentStrategy` 是内置的Agent策略，实现了 `"agent-mixed"` 类别，支持在同一执行框架内同时处理检索增强生成（RAG）和迭代工具调用。

**关键特性**：

- **动态模式切换**: 根据配置自动在RAG和Agent模式之间适应
- **内置工具集成**: 无缝集成所有内置工具（`STOP_TOOL`、`REASONING_TOOL`、`PROCESS_MESSAGE`）
- **推理支持**: 可选的推理步骤生成（在工具执行前）
- **错误处理**: 具有用户通知的全面错误处理
- **会话管理**: 具有内存保留的完整会话状态管理

**配置选项**：

- **工具调用模式**: 通过 `config.builtin.tool_calling_mode` 配置（`"agent"`、`"rag"`、`"none"`）
- **思维模式**: 通过 `config.builtin.agent_thought_mode` 配置（`"reasoning"`、`"reasoning-required"` 等）
- **工具调用限制**: 通过调用计数自动防止无限循环
- **中间消息**: 控制处理消息和推理步骤的可见性
- **错误通知**: 可配置的错误报告给用户

### 9.3.2 Agent工作流程

内置Agent系统遵循以下增强的工作流程：

1. **初始化**: 使用 `create_agent()` 或 `AgentRuntime` 创建Agent
2. **上下文设置**: 使用系统提示和内存初始化对话上下文
3. **模式检测**: 根据配置确定执行模式（RAG vs Agent）
4. **推理阶段** (可选): 如果启用了思维模式，则生成推理步骤
5. **工具选择**: 根据当前情况和可用工具选择适当的工具
6. **工具执行**: 执行选定的工具并进行适当的错误处理
7. **结果处理**: 处理工具结果并更新对话上下文
8. **迭代控制**: 管理迭代限制和终止条件
9. **结束**: 使用 `STOP_TOOL` 结束任务或提供最终响应

### 9.3.3 核心API函数

AmritaCore 提供了用于简化Agent创建的高级工厂函数：

#### create_agent()

一个工厂函数，使用最少的参数创建 `AgentRuntime` 实例：

```python
from amrita_core import create_agent, minimal_init

async def example():
    await minimal_init()
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-4",
        model_config={"temperature": 0.7}
    )
    chat = agent.get_chatobject("What can you do?")
    async with chat.begin():
        response = await chat.full_response()
    return response
```

**参数**：

- `base_url`: API端点URL
- `api_key`: 认证API密钥
- `model`: 模型名称（默认为"auto"）
- `train`: 自定义系统提示（可选）
- `model_config`: 模型配置参数
- `config`: Amrita配置对象（可选）

#### AgentRuntime

提供对Agent配置完全控制的底层运行时类：

```python
from amrita_core import AgentRuntime, minimal_init
from amrita_core.config import get_config
from amrita_core.types import ModelPreset, ModelConfig

async def advanced_example():
    await minimal_init()
    config = get_config()
    preset = ModelPreset(
        name="custom_preset",
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-4",
        config=ModelConfig(temperature=0.7, stream=True)
    )

    agent = AgentRuntime(
        config=config,
        preset=preset,
        train={"content": "你是一个乐于助人的助手。", "role": "system"}
    )

    chat = agent.get_chatobject("你好！")
    async with chat.begin():
        async for chunk in chat.get_response_generator():
            print(chunk, end="")
```

## 9.4 内置安全特性

### 9.4.1 Cookie安全检测

AmritaCore 包含内置的Cookie安全检测，以防止提示注入攻击：

- **自动Cookie生成**: 为每个会话自动生成唯一Cookie
- **泄露检测**: 监控响应中是否存在Cookie，以指示潜在的注入攻击
- **自动响应阻止**: 阻止包含Cookie的响应并返回错误消息

### 9.4.2 会话隔离

内置的会话管理确保不同用户或对话之间的完全隔离：

- **SessionsManager**: 管理会话生命周期的单例类
- **SessionData**: 每个会话的配置、工具和内存
- **自动清理**: 会话在不再需要时自动清理

## 9.5 内置事件系统

AmritaCore 提供了一个全面的事件驱动架构，具有内置的事件处理器：

### 9.5.1 PreCompletionEvent

在向LLM发送请求之前触发，允许修改消息和切换预设。

### 9.5.2 CompletionEvent

在从LLM接收响应后触发，支持响应处理和安全检查。

### 9.5.3 FallbackContext

处理LLM请求失败，具有自动重试逻辑和预设回退机制。

### 9.5.4 内置事件处理器

- **Cookie安全处理器**: 自动检查响应中的Cookie泄露
- **工具调用通知**: 提供工具执行状态的实时反馈
- **错误传播**: 确保跨执行管道的适当错误处理

这些内置功能为开发复杂的AI代理提供了坚实的基础，同时保持安全性、性能和可扩展性。
