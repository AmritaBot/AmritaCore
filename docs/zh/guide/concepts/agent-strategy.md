# Agent 策略

## 理解Agent策略架构

AmritaCore实现了灵活的Agent策略架构，允许为AI Agent使用不同的执行模式。核心概念是将Agent行为逻辑与底层执行框架分离，使开发人员能够创建自定义Agent行为，同时利用AmritaCore提供的强大基础设施。

### 策略类别

AmritaCore支持四种不同的策略类别，每种类别都针对特定用例设计：

#### 1. Agent类别 (`"agent"`)

- **执行方法**: `single_execute()`
- **框架控制**: 完整的框架管理执行循环、调用计数和终止
- **用例**: 需要框架级控制的标准工具调用Agent
- **上下文**: 包含系统消息、内存和用户查询的完整对话历史

#### 2. RAG类别 (`"rag"`)

- **执行方法**: `run()`
- **框架控制**: 仅最小上下文（系统消息 + 用户查询）
- **用例**: 外部知识检索为主要目的的检索增强生成场景
- **上下文**: 仅系统消息和用户查询，无历史对话上下文

#### 3. 工作流类别 (`"workflow"`)

- **执行方法**: `run()`
- **框架控制**: 对所有内容的完全手动控制
- **用例**: 具有自定义编排逻辑的复杂多步骤工作流
- **上下文**: 具有完整手动管理的完整对话历史

#### 4. Agent混合类别 (`"agent-mixed"`)

- **执行方法**: `single_execute()`
- **框架控制**: 具有动态模式切换的框架管理执行
- **用例**: 需要根据上下文在RAG和迭代工具调用之间适应的Agent
- **上下文**: 具有动态行为适应的完整对话历史

### 两种策略类型

AmritaCore 支持**两种互补的 Agent 策略定义方式**，根据是否需要内部状态来选择。

#### 类型一：`type[AgentStrategy]` — 类策略（通用/无状态）

传入一个**类**给 `ChatObject`，框架每次请求自动实例化新副本。

- ✅ 简单、无状态 — 一次编写，处处运行
- ✅ 适用于大多数常见 Agent 模式（ReAct、RAG 等）
- ✅ 无需管理生命周期 — 框架自动处理

```python
chat = ChatObject(
    ...,
    agent_strategy=ReActAgentStrategy,  # 传入类
)
```

#### 类型二：`StrategyLikedObject` — 实例策略（状态机/灵活）

传入一个**已初始化的实例**，同一对象存活于整个对话周期，可携带内部状态机、资源和预配置参数。

- ✅ 跨 `single_execute()` / `run()` 调用保持内部状态
- ✅ 在创建时预加载重量资源（API 客户端、数据库连接等）
- ✅ 保障对话隔离 — 每个对话各自独立实例
- ✅ 适用于限流、认证、多步骤有状态工作流

```python
strategy = MyStatefulStrategy(api_key="sk-...", max_calls=5)
chat = ChatObject(
    ...,
    agent_strategy=strategy,  # 传入实例
)
```

> `ChatObject.agent_strategy` 同时接受 **`type[AgentStrategy]` 或 `StrategyLikedObject` 实例**。

### 模板方法模式架构

AmritaCore的Agent策略系统通过**模板方法模式**得到了增强，该模式提供了统一的执行框架，同时允许策略特定的自定义。

`BaseReActAgentStrategy` 抽象基类定义了通用执行流程：

1. **工具调用生成**: 模型基于当前上下文生成工具调用
2. **工具执行循环**: 每个工具调用都通过标准化流程处理
3. **结果处理**: 策略特定逻辑处理如何将结果添加到上下文
4. **循环检测**: 自动检测和处理推理循环
5. **错误处理**: 具有策略特定恢复的通用错误模式
6. **后处理**: 可选的 `on_post_process()` 钩子用于最终修改

这种模式确保所有ReAct风格策略的行为一致性，同时通过抽象方法（如 `_append_tool_result_to_context()` 和 `_handle_error_append()`）允许自定义。

### 统一工具接口

所有Agent策略都从基类 `AgentStrategy` 继承 `call_tool()` 方法。这提供了**统一的工具执行接口**，确保AmritaCore中所有策略实现的一致性。

统一工具接口的关键特性：

- **单步执行**: 每次调用恰好执行一个工具，不修改Agent的内部上下文
- **一致的错误处理**: 在管理器中找不到的工具会引发 `RuntimeError`
- **标准化响应格式**: 返回字符串响应或None返回的默认消息
- **ToolContext集成**: 支持简单的函数调用和具有上下文访问的高级工具实现

这种统一接口保证了无论您实现哪种策略类别，工具调用行为在整个AmritaCore生态系统中都保持一致和可预测。

### 内置策略实现

#### ReActAgentStrategy

遵循OpenAI兼容ToolCall-ToolResult配对的标准实现。它保持严格的消息格式合规性，适用于大多数LLM提供商。

#### HybridReActAgentStrategy

针对**混合专家（MoE）架构模型**优化的专门实现。它不使用标准的ToolCall-ToolResult对，而是使用嵌入在对话上下文中的XML标签（`<TOOL_CALL>`、`<TOOL_RESULT>`）作为纯文本消息。

这种方法解决了MoE模型中的状态机模糊问题，但由于潜在的提示注入风险，需要仔细的安全考虑。

#### NoActionAgentStrategy

执行无操作的最小工作流策略，当需要跳过工具执行时很有用。

## 实现指南

### 创建自定义Agent策略

要创建自定义Agent策略，您有两种选择：

#### 选项1: 扩展 BaseReActAgentStrategy（推荐用于ReAct风格Agent）

```python
from amrita_core.builtins.agent import BaseReActAgentStrategy
from typing import Literal

class MyCustomReActStrategy(BaseReActAgentStrategy):
    def __init__(self, ctx):
        super().__init__(ctx)
        # 初始化自定义状态

    async def _append_tool_result_to_context(self, tool_call, func_response, response_msg):
        # 实现工具结果如何添加到上下文
        pass

    async def _handle_error_append(self, function_name, error_content, tool_call_id, original_exception):
        # 实现特定于策略的错误处理
        pass

    async def _append_reasoning(self, response):
        # 实现推理步骤处理
        pass

    @classmethod
    def get_category(cls) -> Literal["agent-mixed"]:
        return "agent-mixed"
```

#### 选项2: 直接扩展 AgentStrategy（用于完全自定义行为）

```python
from amrita_core.agent.strategy import AgentStrategy
from typing import Literal

class MyCustomAgentStrategy(AgentStrategy):
    def __init__(self, ctx):
        super().__init__(ctx)
        # 初始化自定义状态

    async def single_execute(self) -> bool:
        # 实现单步执行逻辑
        # 返回True继续，False停止
        return True

    async def on_post_process(self) -> None:
        # 可选：实现后处理逻辑
        # 在agent/agent-mixed模式下成功执行后调用
        pass

    @classmethod
    def get_category(cls) -> Literal["agent"]:
        return "agent"
```

### 使用内置策略

AmritaCore为不同用例提供多种内置策略：

```python
import asyncio
from amrita_core import create_agent, minimal_init
from amrita_core.builtins.agent import (
    ReActAgentStrategy,
    HybridReActAgentStrategy,
    NoActionAgentStrategy
)

async def use_builtin_strategies():
    # 初始化AmritaCore
    await minimal_init()

    # 标准ReAct策略（推荐用于大多数情况）
    standard_agent = create_agent(
        url="https://api.openai.com",
        key="your-api-key",
        strategy=ReActAgentStrategy
    )

    # MoE模型的混合策略
    hybrid_agent = create_agent(
        url="https://api.moemodel.com",
        key="your-api-key",
        strategy=HybridReActAgentStrategy
    )

    # 跳过工具执行的无操作策略
    no_action_agent = create_agent(
        url="https://api.example.com",
        key="your-api-key",
        strategy=NoActionAgentStrategy
    )

    # 使用这些Agent
    chat1 = standard_agent.get_chatobject("你能做什么？")
    chat2 = hybrid_agent.get_chatobject("分析这些数据")
    chat3 = no_action_agent.get_chatobject("直接回应")

    async with chat1.begin(), chat2.begin(), chat3.begin():
        response1 = await chat1.full_response()
        response2 = await chat2.full_response()
        response3 = await chat3.full_response()
```

## 有状态策略：StrategyLikedObject

> **v0.9.0rc1 新增**：`StrategyLikedObject` 通过传入预初始化的实例（而非类）实现有状态策略。

标准 `AgentStrategy` 子类由框架为每个请求实例化，适合无状态场景，但有以下局限：

- **状态机**：需要跨调用跟踪状态的策略无法实现
- **预配置资源**：无法在创建时预加载 API 客户端、数据库连接等
- **对话隔离**：每个对话获得独立的策略实例及其独立状态

`StrategyLikedObject` 通过允许你**直接传入已初始化的实例**解决了这些问题。

### 对比

| 维度 | `AgentStrategy`（类） | `StrategyLikedObject`（实例） |
|------|----------------------|-----------------------------|
| 传入方式 | 类（`type`） | 已初始化实例 |
| 实例化 | 框架每次请求自动创建 | 用户手动创建一次 |
| 有状态 | 否（每次新实例） | 是（同一实例贯穿全程） |
| 资源加载 | 每次请求 | 创建时一次性 |
| 适用场景 | 无状态、简单策略 | 复杂有状态工作流 |

### 用法示例

```python
from amrita_core.agent.strategy import StrategyLikedObject

class 限流策略(StrategyLikedObject):
    def __init__(self, 最大调用次数: int, api_key: str):
        self.最大调用次数 = 最大调用次数
        self.调用计数 = 0
        self.api_key = api_key
        self.客户端 = MyAPIClient(api_key)  # 预加载资源

    @classmethod
    def get_category(cls) -> str:
        return "agent"

    async def single_execute(self) -> bool:
        self.调用计数 += 1
        if self.调用计数 > self.最大调用次数:
            return False  # 停止
        # 使用 self.客户端 进行 API 调用...
        return True

    async def on_limited(self) -> None:
        await self.chat_object.yield_response(
            "本次对话已达到调用上限。"
        )

# 传入实例 — 而非类
策略 = 限流策略(最大调用次数=5, api_key="sk-...")
chat_obj = ChatObject(
    train={"system": "你是一个有用的助手"},
    user_input="你好",
    context=None,
    session_id="session_123",
    agent_strategy=策略,  # 实例！
)
```

### 生命周期

1. **创建**：用户手动实例化 `StrategyLikedObject`
2. **注册**：实例传入 `ChatObject(agent_strategy=实例)`
3. **初始化**：框架调用 `strategy(ctx)` 注入运行时上下文
4. **执行**：同一实例处理所有 `single_execute()` / `run()` 调用
5. **清理**：对话结束时实例被丢弃

### 何时使用

- **限流**：跟踪每个对话的工具调用次数
- **认证客户端**：用会话令牌预初始化 API 客户端
- **多步骤工作流**：在工作流各阶段之间保持状态
- **资源池化**：在策略实例间共享连接池

### 后处理钩子

`on_post_process()` 方法是一个新的生命周期钩子，在所有Agent步骤成功完成后调用。此钩子对**所有策略类别**（`"agent"`、`"rag"`、`"workflow"`、`"agent-mixed"`）都可用，可用于：

- 向上下文添加最终指令
- 上下文摘要或清理
- 完成前的最终验证

```python
async def on_post_process(self) -> None:
    """在成功Agent执行后调用"""
    if self.call_count >= 2:  # 仅在实际调用了工具时
        self.ctx.message.append(
            Message(
                role="user",
                content="<END_OF_PROCESS>\n请根据我们之前获得的信息直接回答我。\n<END_OF_PROCESS>"
            )
        )
```
