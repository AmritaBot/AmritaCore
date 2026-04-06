# NoActionAgentStrategy

`NoActionAgentStrategy` 是一个执行无操作的简单工作流策略。当需要放弃工具调用过程时可以使用。

## 继承关系

- 继承自: [AgentStrategy](AgentStrategy.md)
- 类别: `"workflow"`

## 构造函数参数

- `ctx` ([StrategyContext](StrategyContext.md)): 包含chat_object、配置和消息上下文的策略上下文

## 方法

### run()

无操作实现，立即返回而不执行任何操作。

**返回**: None

### on_exception()

无操作异常处理程序，立即返回而不执行任何操作。

**参数**:

- `exc` (BaseException): 发生的异常

**返回**: None

## 使用示例

```python
import asyncio
from amrita_core import create_agent, minimal_init
from amrita_core.builtins.agent import NoActionAgentStrategy

async def use_no_action_strategy():
    # 初始化AmritaCore
    await minimal_init()

    # 创建带有无操作策略的Agent以跳过工具执行
    agent = create_agent(
        url="https://api.example.com",
        key="your-api-key",
        strategy=NoActionAgentStrategy
    )

    # 使用Agent - 它将直接响应而不调用工具
    chat = agent.get_chatobject("直接回应此查询")
    async with chat.begin():
        response = await chat.full_response()
```

## 何时使用

当以下情况时使用 `NoActionAgentStrategy`：

- 想要完全跳过工具执行
- 需要一个没有工具调用逻辑的简单直接响应
- 实现条件逻辑，其中在某些场景下应绕过工具调用
- 需要用于测试或调试目的的占位符策略
