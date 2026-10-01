# NoActionAgentStrategy

`NoActionAgentStrategy` 是一个简单的工作流策略，不执行任何操作。可在需要放弃工具调用过程时使用。

## 继承

- 继承自：[AgentStrategy](AgentStrategy.md)
- 类别：`"workflow"`

## 构造函数参数

- `ctx` ([StrategyContext](StrategyContext.md))：策略上下文，包含 chat_object、配置与消息上下文

## 方法

### run()

无操作实现，立即返回而不执行任何操作。

**返回**：None

### on_exception()

无操作异常处理器，立即返回而不执行任何操作。

**参数**：

- `exc` (BaseException)：发生的异常

**返回**：None

## 使用示例

```python
import asyncio
from amrita_core import create_agent, minimal_init
from amrita_core.builtins.agent import NoActionAgentStrategy


async def use_no_action_strategy():
    # 初始化 AmritaCore
    await minimal_init()

    # 创建使用无操作策略的 agent，以跳过工具执行
    agent = create_agent(
        url="https://api.example.com",
        key="your-api-key",
        strategy=NoActionAgentStrategy,
    )

    # 使用该 agent——它会直接回复，不调用工具
    chat = agent.get_chatobject("Just respond to this query directly")
    async with chat.begin():
        response = await chat.full_response()
        await chat  # 退出前等待任务完成
```

## 何时使用

在以下情况使用 `NoActionAgentStrategy`：

- 你希望完全跳过工具执行
- 你需要一个不带任何工具调用逻辑的简单直接回复
- 你正在实现条件逻辑，某些场景下应绕过工具调用
- 你需要一个用于测试或调试的占位策略
