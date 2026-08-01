# Agent 策略

## 理解 Agent 策略架构

AmritaCore 实现了灵活的 Agent 策略架构，允许 AI 智能体使用不同的执行模式。核心概念是将智能体行为逻辑与底层执行框架分离，使开发者能够创建自定义智能体行为，同时利用 AmritaCore 提供的健壮基础设施。

### 策略类别

AmritaCore 支持四种不同的策略类别，每种针对特定用例设计：

#### Agent 类别（`"agent"`）

- **执行方法**：`single_execute()`
- **框架控制**：框架完全管理执行循环、调用计数和终止
- **用例**：需要框架级别控制的标准工具调用智能体
- **上下文**：包含系统消息、记忆和用户查询的完整对话历史

#### RAG 类别（`"rag"`）

- **执行方法**：`run()`
- **框架控制**：仅最小上下文（系统消息 + 用户查询）
- **用例**：以外部知识检索为主的检索增强生成场景
- **上下文**：仅系统消息和用户查询，无历史对话上下文

#### Workflow 类别（`"workflow"`）

- **执行方法**：`run()`
- **框架控制**：完全手动控制一切
- **用例**：具有自定义编排逻辑的复杂多步骤工作流
- **上下文**：包含完全手动管理的完整对话历史

#### Agent-Mixed 类别（`"agent-mixed"`）

- **执行方法**：`single_execute()`
- **框架控制**：框架管理的执行，支持动态模式切换
- **用例**：需要根据上下文在 RAG 和迭代工具调用之间切换的智能体
- **上下文**：包含动态行为切换的完整对话历史

### 两种策略定义方式

AmritaCore 支持**两种互补的方式**来定义 agent 策略。根据你的策略是否需要内部状态来选择。

#### 方式一：`type[AgentStrategy]`——基于类的策略

将**类**传递给 `ChatObject`。框架为每个请求实例化一个新的副本。

- ✅ 简单、无状态——编写一次，到处运行
- ✅ 适用于大多数常见 agent 模式（ReAct、RAG 等）
- ✅ 无需管理生命周期——框架处理

```python
chat = ChatObject(
    ...,
    agent_strategy=ReActAgentStrategy,  # 传递类
)
```

#### 方式二：`StrategyLikedObject`——基于实例的策略

传递**预初始化的实例**。同一对象在整轮对话中存活，携带自己的状态机、资源和配置。

- ✅ 在 `single_execute()` / `run()` 调用之间携带内部状态
- ✅ 在创建时一次性预加载重量级资源（API 客户端、数据库连接）
- ✅ 保证对话隔离——每次对话获得自己的实例
- ✅ 适用于速率受限、需认证或多步骤有状态工作流

```python
strategy = MyStatefulStrategy(api_key="sk-...", max_calls=5)
chat = ChatObject(
    ...,
    agent_strategy=strategy,  # 传递实例
)
```

> `ChatObject.agent_strategy` 接受**两种**——`type[AgentStrategy]` **或** `StrategyLikedObject` 实例。

### 模板方法模式架构

AmritaCore 的 agent 策略系统已通过**模板方法模式**增强，提供统一的执行框架，同时允许策略特定的自定义。

`BaseReActAgentStrategy` 抽象基类定义了通用执行流程：

1. **工具调用生成**：模型根据当前上下文生成工具调用
2. **工具执行循环**：每个工具调用通过标准化流程处理
3. **结果处理**：策略特定的逻辑处理如何将结果添加到上下文
4. **循环检测**：自动检测和处理推理循环
5. **错误处理**：通用错误模式，策略特定的恢复
6. **后处理**：可选的 `on_post_process()` 钩子用于最终修改

### 统一工具接口

所有 agent 策略从基础 `AgentStrategy` 类继承 `call_tool()` 方法。这为工具执行提供了**统一接口**，确保 AmritaCore 中所有策略实现的一致性。

### 内置策略实现

#### ReActAgentStrategy

遵循 OpenAI 兼容的 ToolCall-ToolResult 配对的标准实现。保持严格的消息格式合规性，适用于大多数 LLM 提供商。

#### HybridReActAgentStrategy

针对**混合专家（MoE）架构模型**优化的专用实现。使用直接嵌入在对话上下文中的 XML 标签（`<TOOL_CALL>`、`<TOOL_RESULT>`）作为纯文本消息，而非标准的 ToolCall-ToolResult 配对。

#### NoActionAgentStrategy

最小工作流策略，不执行任何操作，适用于需要跳过工具执行的场景。

## 实现指南

### 在策略中访问 DI 资源（v0.12.6+）

Agent 策略扩展 `_StrategyBase`（通过 `AgentStrategy` 或 `StrategyLikedObject`），提供**便捷属性**来访问 DI 资源。从 v0.12.6 开始，策略应使用这些属性，而不是通过 `self.chat_object` 访问。

**可用的便捷属性：**

| 属性                    | 解析自                 | 回退（如果 ctx 字段为 None）            |
| ----------------------- | ---------------------- | --------------------------------------- |
| `self.preset`           | `ctx.preset`           | `self.chat_object.preset`               |
| `self.config`           | `ctx.config`           | `self.chat_object.config`               |
| `self.io_stream`        | `ctx.io_stream`        | `self.chat_object.io_stream`            |
| `self.train_content`    | `ctx.train_content`    | `self.chat_object.train.content`        |
| `self.stream_id`        | `ctx.stream_id`        | `self.chat_object.stream_id`            |
| `self.resp_extra_usage` | `ctx.resp_extra_usage` | `self.chat_object._di_resp.extra_usage` |

`resp_extra_usage` 属性也支持 **setter**，允许策略直接更新使用量跟踪。

**示例 — 之前（旧版）：**

```python
class MyStrategy(AgentStrategy):
    async def single_execute(self) -> bool:
        preset = self.chat_object.preset          # 通过 ChatObject 访问
        config = self.chat_object.config
        await self.chat_object.io_stream.yield_response(...)
        return True
```

**示例 — 之后（v0.12.6+）：**

```python
class MyStrategy(AgentStrategy):
    async def single_execute(self) -> bool:
        preset = self.preset                      # 使用便捷属性
        config = self.config
        await self.io_stream.yield_response(...)
        return True
```

> **工作原理**：当 `StrategyContext` DI 字段被填充时（通过 `STRATEGY_INIT` 节点或 `_run_strategy`），这些属性直接返回它们。否则回退到 `chat_object` 以保证向后兼容。

### 创建自定义 Agent 策略

要创建自定义 agent 策略，你有两种选择：

#### 选项 1：扩展 BaseReActAgentStrategy（推荐用于 ReAct 风格 Agent）

```python
from amrita_core.builtins.agent import BaseReActAgentStrategy
from typing import Literal

class MyCustomReActStrategy(BaseReActAgentStrategy):
    def __init__(self, ctx):
        super().__init__(ctx)
        # 初始化自定义状态

    async def _append_tool_result_to_context(self, tool_call, func_response, response_msg):
        # 实现工具结果如何被添加到上下文中
        pass

    async def _handle_error_append(self, function_name, error_content, tool_call_id, original_exception):
        # 实现针对你策略的特定错误处理
        pass

    async def _append_reasoning(self, response):
        # 实现推理步骤处理
        pass

    @classmethod
    def get_category(cls) -> Literal["agent-mixed"]:
        return "agent-mixed"
```

#### 选项 2：直接扩展 AgentStrategy（用于完全自定义行为）

```python
from amrita_core.agent.strategy import AgentStrategy
from typing import Literal

class MyCustomAgentStrategy(AgentStrategy):
    def __init__(self, ctx):
        super().__init__(ctx)
        # 初始化自定义状态

    async def single_execute(self) -> bool:
        # 实现单步执行逻辑
        # 返回 True 继续，False 停止
        return True

    async def on_post_process(self) -> None:
        # 可选：实现后处理逻辑
        # 在 agent/agent-mixed 模式下成功执行后调用
        pass

    @classmethod
    def get_category(cls) -> Literal["agent"]:
        return "agent"
```

### 使用内置策略

AmritaCore 为不同用例提供了多种内置策略：

```python
import asyncio
from amrita_core import create_agent, minimal_init
from amrita_core.builtins.agent import (
    ReActAgentStrategy,
    HybridReActAgentStrategy,
    NoActionAgentStrategy
)

async def use_builtin_strategies():
    # 初始化 AmritaCore
    await minimal_init()

    # 标准 ReAct 策略（推荐大多数情况使用）
    standard_agent = create_agent(
        base_url="https://api.openai.com",
        api_key="your-api-key",
        strategy=ReActAgentStrategy
    )

    # 用于 MoE 模型的混合策略
    hybrid_agent = create_agent(
        base_url="https://api.moemodel.com",
        api_key="your-api-key",
        strategy=HybridReActAgentStrategy
    )

    # 无操作策略，跳过工具执行
    no_action_agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        strategy=NoActionAgentStrategy
    )

    # 使用 agent
    chat = standard_agent.get_chatobject("你能做什么？")

    chat.begin()
    async with chat:
        async for chunk in chat.io_stream.get_response_generator():
            content = chunk if isinstance(chunk, str) else chunk.get_content()
            print(content, end="", flush=True)
        await chat  # 等待任务完成再退出
    # 退出上下文后 Chat 自动清理
```

## 使用 StrategyLikedObject 的有状态策略

> **v0.9.0rc1 新增**：`StrategyLikedObject` 通过传递预初始化的实例而非类类型来支持有状态 agent 策略。

### 动机

标准的 `AgentStrategy` 子类由框架在每次请求时实例化。这对无状态策略有效，但限制了：

- **状态机**：需要在多次调用之间跟踪状态的策略
- **预配置资源**：需要预加载 API 客户端、数据库连接或模型实例的策略
- **对话隔离**：保证每个对话获得具有独立状态的独立策略实例

`StrategyLikedObject` 通过允许你直接向 `ChatObject` 传递**已经初始化的实例**来解决这些问题。

### 对比：AgentStrategy vs StrategyLikedObject

| 方面     | `AgentStrategy`      | `StrategyLikedObject`  |
| -------- | -------------------- | ---------------------- |
| 传递形式 | 类（`type`）         | 实例                   |
| 实例化   | 每次请求由框架实例化 | 用户一次性创建         |
| 有状态   | 否（每次都是新实例） | 是（同一实例全程使用） |
| 资源加载 | 每次请求             | 创建时一次             |
| 使用场景 | 无状态的简单策略     | 复杂的有状态工作流     |

### 用法

```python
from amrita_core.agent.strategy import StrategyLikedObject
from amrita_core.agent.context import StrategyContext

class RateLimitedStrategy(StrategyLikedObject):
    def __init__(self, max_calls: int, api_key: str):
        self.max_calls = max_calls
        self.call_count = 0
        self.api_key = api_key
        self.client = MyAPIClient(api_key)  # 预加载资源

    @classmethod
    def get_category(cls) -> str:
        return "agent"

    async def single_execute(self) -> bool:
        self.call_count += 1
        if self.call_count > self.max_calls:
            return False  # 停止
        # 使用 self.client 进行 API 调用...
        return True

    async def on_limited(self) -> None:
        await self.chat_object.yield_response(
            "本次对话已达到调用限制。"
        )

# 传递实例 — 而非类
strategy = RateLimitedStrategy(max_calls=5, api_key="sk-...")
chat_obj = ChatObject(
    train={"system": "你是一个有帮助的助手"},
    user_input="你好",
    context=None,
    session_id="session_123",
    agent_strategy=strategy,  # 实例！
)
```

### 生命周期

1. **创建**：用户使用自定义参数实例化 `StrategyLikedObject`
2. **注册**：实例传递给 `ChatObject(agent_strategy=instance)`
3. **初始化**：一旦上下文就绪，框架调用 `strategy(ctx)`
4. **执行**：同一实例处理所有 `single_execute()` / `run()` 调用
5. **清理**：对话结束时丢弃实例

### 何时使用

- **速率限制**：跟踪每个对话的工具调用次数
- **认证客户端**：使用会话令牌预初始化 API 客户端
- **多步骤工作流**：跨工作流阶段维护状态
- **资源池**：跨策略实例共享连接池

## Post-Process 钩子

`on_post_process()` 方法是一个生命周期钩子，在所有 agent 步骤成功完成后调用。此钩子适用于**所有策略类别**（`"agent"`、`"rag"`、`"workflow"`、`"agent-mixed"`），可用于：

- 向上下文添加最终指令
- 上下文摘要或清理
- 完成前的最终验证

```python
async def on_post_process(self) -> None:
    """在 agent 成功执行后调用"""
    if self.call_count >= 2:  # 仅在确实调用了工具时
        self.ctx.message.append(
            Message(
                role="user",
                content="<END_OF_PROCESS>\n请根据之前获得的信息直接回答我。\n<END_OF_PROCESS>"
            )
        )
```
