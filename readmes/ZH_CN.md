# AmritaCore - Proj.Amrita 智能体核心模块

## 项目概述

AmritaCore 是 Proj.Amrita 的智能体（Agent）核心模块，是一个轻量级的 Python 库，专注于提供可扩展、可维护的智能体核心实现。它作为项目的核心Agent组件，承担主要的逻辑或控制功能，为各种智能体应用场景提供坚实的基础。

## Why AmritaCore?

AmritaCore 旨在解决现代 AI 应用开发中的几个关键挑战：

1. **简化智能体开发**: 提供高级API如 `create_agent()` 工厂函数用于快速开发，同时通过 `AgentRuntime` 类保持完全控制。

2. **灵活的Agent策略架构**: 支持四种不同的执行策略：
   - **Agent模式**: 带有推理能力的标准迭代工具调用
   - **RAG模式**: 用于知识密集型任务的检索增强生成
   - **Workflow模式**: 用于结构化流程的顺序工作流执行
   - **Agent-Mixed模式**: 根据上下文需求动态适应的混合方法

3. **可扩展的架构**: 设计注重可扩展性，支持工具集成、事件钩子和协议适配器，允许开发者按需扩展智能体能力。

4. **高效的上下文管理**: 内置智能记忆摘要功能，自动管理长对话历史，平衡上下文完整性和Token消耗。

5. **原生异步流式处理**: 所有输出都设计为异步流式（"Every is a stream"），支持实时响应处理和更好的用户体验。

6. **供应商无关设计**: 抽象的数据类型和对话管理，可在不同LLM提供商之间工作，避免供应商锁定。

7. **全面的安全性**: 内置Cookie安全检测、会话隔离和内容过滤机制，防止提示注入和数据泄露。

8. **原生挂起/恢复支持**: 内置机制可在任意时刻暂停和恢复Agent执行流程，支持具有实时用户控制的交互式应用程序

## 核心特性

### Agent策略系统

AmritaCore 实现了灵活的Agent策略架构，包含四种执行类别：

#### Agent策略 (`"agent"`)

- 带内置推理支持的迭代工具调用
- 自动工具调用限制，防止无限循环
- 执行循环和终止的完整框架管理

#### RAG策略 (`"rag"`)

- 最小上下文，专注于系统消息 + 用户查询
- 针对外部知识检索场景优化
- 默认无历史对话上下文

#### Workflow策略 (`"workflow"`)

- 对执行流程的完全手动控制
- 适用于具有自定义编排的复杂多步骤工作流
- 具有手动管理的完整对话历史

#### Agent-Mixed策略 (`"agent-mixed"`)

- 基于上下文需求的动态模式切换
- 结合RAG和迭代工具调用能力
- 由内置的 `ReActAgentStrategy` 实现

### 配置系统

AmritaCore 通过模块化系统提供全面配置：

#### FunctionConfig - 功能配置

- 可配置的工具调用模式：`"agent"`、`"rag"`、`"workflow"`、`"none"`
- 推理模式：`"reasoning"`、`"reasoning-required"` 等
- 内置工具配置：停止工具、推理工具、处理消息工具
- MCP客户端集成，用于外部工具扩展
- 会话隔离和内存管理设置

#### LLMConfig - 大语言模型配置

- 具有自动摘要的智能记忆抽象
- 可配置的令牌计数和窗口管理
- 具有回退预设支持的自动重试逻辑
- 具有用法统计的流式响应配置
- 供应商无关的模型预设系统

### 核心API函数

AmritaCore 提供高级和低级API：

#### create_agent() 工厂函数

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
    # 使用 agent.get_chatobject() 进行交互
```

#### AgentRuntime 类

- 对Agent配置和生命周期的完全控制
- 具有持久内存的会话管理
- 策略自定义和动态切换
- 用于生产环境的高级配置选项

### 内置工具

AmritaCore 包含三个 essential 内置工具：

- **STOP_TOOL** (`agent_stop`): 表示任务完成并准备提供最终答案
- **REASONING_TOOL** (`think_and_reason`): 为自主决策生成推理步骤
- **PROCESS_MESSAGE** (`processing_message`): 向用户传达内部想法和当前操作

这些工具根据配置自动启用，为智能体行为提供基础。

### 协议适配器

AmritaCore 通过协议适配器支持多个LLM提供商：

- **OpenAIAdapter**: 对OpenAI兼容API的完全支持，包括流式处理、工具调用和用量跟踪
- **AnthropicAdapter** (实验性): 对Anthropic Claude模型的支持，具有适当的令牌处理

### 事件系统

全面的事件驱动架构，具有多个钩子点：

- **PreCompletionEvent**: 在向LLM发送前修改消息
- **CompletionEvent**: 在从LLM接收后处理响应
- **FallbackContext**: 处理LLM请求失败，具有自动重试逻辑
- **自定义事件**: 用于自定义集成的可扩展事件系统

### 工具系统

强大的外部工具集成系统：

- **装饰器注册**: 使用 `@on_tools` 装饰器注册工具，具有完整的模式定义
- **Custom Run模式**: 高级工具执行，通过 `ctx.ctx.chat_object` 直接访问聊天对象
- **动态发现**: 自动工具元数据收集和运行时发现
- **条件启用**: 基于运行时条件启用/禁用工具
- **类型安全**: 工具参数和返回值的完整类型检查

### 安全机制

多层安全架构：

- **Cookie安全检测**: 通过Cookie泄露自动检测提示注入尝试
- **会话隔离**: 用户会话之间的完全隔离，具有独立的状态管理
- **内容过滤**: 可配置的输入和输出内容过滤
- **访问控制**: 基于角色的访问控制和速率限制支持

## 适用场景

AmritaCore 适用于需要智能体能力的各种场景：

- **智能聊天机器人**: 具有工具调用和推理能力的对话代理
- **自动化工作流**: 具有错误处理的多步骤流程自动化
- **研究助手**: 具有RAG能力的知识密集型任务
- **决策支持系统**: 具有推理轨迹的复杂决策制定
- **客户服务自动化**: 具有安全性和合规性的企业级客户服务
- **个性化推荐引擎**: 具有上下文感知的推荐系统

## 快速开始

安装 AmritaCore:

```bash
pip install amrita-core
```

基本用法:

```python
import asyncio
from amrita_core import create_agent, minimal_init

async def main():
    await minimal_init()
    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="your-openai-key",
        model="gpt-4"
    )

    chat = agent.get_chatobject("你好！What can you do?")
    async with chat.begin():
        response = await chat.full_response()
        print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

## 文档链接

请点击[官方文档](https://core.amritabot.com)查看完整的指南、API参考和示例。
