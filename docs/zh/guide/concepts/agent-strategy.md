# Agent 策略

## 理解 Agent 策略架构

AmritaCore 实现了灵活的 Agent 策略架构，允许 AI agent 采用不同的执行模式。核心概念是将 agent 行为逻辑与底层执行框架分离，使开发者能够创建自定义 agent 行为，同时利用 AmritaCore 提供的强大基础设施。

### 策略类别

AmritaCore 支持四种不同的策略类别，每种类别都针对特定用例设计：

#### 1. Agent 类别 (`"agent"`)

- **执行方法**: `single_execute()`
- **框架控制**: 完全由框架管理执行循环、调用计数和终止条件
- **使用场景**: 需要框架级控制的标准工具调用 agent
- **上下文**: 包含系统消息、记忆和用户查询的完整对话历史

#### 2. RAG 类别 (`"rag"`)

- **执行方法**: `run()`
- **框架控制**: 仅最小上下文（系统消息 + 用户查询）
- **使用场景**: 检索增强生成场景，其中外部知识检索是主要功能
- **上下文**: 仅系统消息和用户查询，无历史对话上下文

#### 3. Workflow 类别 (`"workflow"`)

- **执行方法**: `run()`
- **框架控制**: 对所有内容的完全手动控制
- **使用场景**: 具有自定义编排逻辑的复杂多步骤工作流
- **上下文**: 具有完全手动管理的完整对话历史

#### 4. Agent-Mixed 类别 (`"agent-mixed"`)

- **执行方法**: `single_execute()`
- **框架控制**: 框架管理的执行，具有动态模式切换
- **使用场景**: 需要根据上下文在 RAG 和迭代工具调用之间适应的 agent
- **上下文**: 具有动态行为适应的完整对话历史

## 实现指南

### 创建自定义 Agent 策略

要创建自定义 agent 策略，请扩展 `AgentStrategy` 抽象基类并实现所需的方法：

```python
from amrita_core.agent.strategy import AgentStrategy
from typing import Literal

class MyCustomAgentStrategy(AgentStrategy):
    def __init__(self, ctx):
        super().__init__(ctx)
        # 初始化自定义状态
        
    async def single_execute(self) -> bool:
        # 实现单步执行逻辑
        # 返回 True 继续，返回 False 停止
        return True
        
    @classmethod
    def get_category(cls) -> Literal["agent"]:
        return "agent"
```

### 使用内置策略

AmritaCore 提供了 `AmritaAgentStrategy` 作为内置实现，支持 `"agent-mixed"` 类别：

```python
from amrita_core import create_agent
from amrita_core.builtins.agent import AmritaAgentStrategy

# 使用自定义策略创建 agent
agent = create_agent(
    url="https://api.example.com",
    key="your-api-key",
    strategy=AmritaAgentStrategy
)

# 使用 agent
chat = agent.get_chatobject("你能做什么？")
async with chat.begin():
    response = await chat.full_response()
```

## 策略上下文

`StrategyContext` 为策略执行提供所有必要信息：

- `user_input`: 原始用户输入
- `original_context`: 包含系统消息、记忆和用户查询的完整消息上下文
- `chat_object`: 用于生成响应的聊天对象引用

## 最佳实践

1. **选择正确的类别**: 选择最适合您用例的策略类别
2. **利用框架功能**: 使用内置功能如工具调用限制、错误处理和响应流
3. **优雅地处理错误**: 在策略方法中实现适当的错误处理
4. **尽可能使用内置策略**: 在创建自定义实现之前，先从 `AmritaAgentStrategy` 开始
5. **彻底测试**: 确保您的策略能正确处理边缘情况和错误条件

## 示例：自定义 RAG 策略

```python
from amrita_core.agent.strategy import AgentStrategy
from typing import Literal

class RAGStrategy(AgentStrategy):
    async def run(self) -> None:
        # 根据用户查询检索相关文档
        documents = self.retrieve_documents(self.ctx.user_input)
        
        # 使用检索到的文档构建上下文
        rag_context = f"基于以下文档:\n{documents}\n\n用户查询: {self.ctx.user_input}"
        
        # 更新消息上下文
        self.ctx.original_context.train.content += f"\n\n检索到的上下文: {rag_context}"
        
        # 让框架处理其余部分
        pass
        
    @classmethod
    def get_category(cls) -> Literal["rag"]:
        return "rag"
```
