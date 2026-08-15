# 1. 创建你的第一个 Agent

## 本章目标

与 LLM 跑通一次真实对话。学完你能：

- 初始化 AmritaCore 并创建 agent
- 理解 `ChatObject` 是什么、为什么它包装了整次对话
- 看到两种工作流：默认的简单对话与显式开启的 Step 循环

## 概念速览（用到才讲）

- **Agent**：绑定你 LLM 端点的工厂。你向它要对话（`get_chatobject`）。
- **`ChatObject`**：一次对话。它拥有流、会话状态和运行对话的工作流。
- **策略**：决定 agent 如何行动的"驱动器"（调用工具、停止、作答）。
  AmritaCore 内置 step 驱动的 ReAct 策略——通过显式传入 step 循环
  工作流来启用它。

## 1. 初始化 AmritaCore

每个进程只需初始化一次配置：

```python
import asyncio
import os

from amrita_core import create_agent, minimal_init


async def main() -> None:
    await minimal_init()
    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key=os.environ["OPENAI_API_KEY"],
        model="gpt-4o-mini",
    )
```

`create_agent()` 返回 `Agent` 对象——对话的工厂。

## 2. ChatObject——对话的基本单位

一次对话就是一个 `ChatObject`。它拥有工作流、流和会话状态：

```python
    chat = agent.get_chatobject("What is the capital of France?")
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            print(msg, end="", flush=True)
```

- `get_chatobject(text)` 创建一次对话
- `chat.begin()` 运行工作流（流式内置）
- `chat.io_stream.get_response_generator()` 产出响应 chunk

## 3. 两种工作流：简单对话 vs Step 循环

不带任何额外参数调用 `get_chatobject()` 运行的是**简单对话工作流**：
一次 LLM 调用、一个回答。它是对话最快的路径——但不会分解任务，
也不运行 Step 循环。

```python
    chat = agent.get_chatobject("What is the capital of France?")
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            print(msg, end="", flush=True)
```

要运行内置的 **Step 驱动的 ReAct 策略**——LLM 把任务分解为计划、框架
逐 Step 走完、agent 可以调用工具甚至中途修订自己的计划——你必须
**显式传入 step 循环工作流**：

```python
from amrita_core.chatmanager import _step_workflow_rendered

    chat = agent.get_chatobject(
        "What is the capital of France?",
        workflow=_step_workflow_rendered,
    )
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            print(msg, end="", flush=True)
```

你可以把步骤作为结构化元数据观察：

```python
    async with chat.begin():
        async for msg in chat.io_stream.get_response_generator():
            if isinstance(msg, str):
                print(msg, end="", flush=True)
            else:
                print(f"\n[meta:{msg.metadata}] {msg.content}", flush=True)
```

你会看到 `step` 事件（`decompose` / `intro` / `leave`）与文本交错出现——
完整列表见[流式与回调](streaming.md)。

> **为什么要显式传入？** 默认使用简单工作流，是为了让裸调用
> `get_chatobject()` 在普通对话场景下"开箱即用"。Step 循环用简单换取
> 计划驱动的自主性——需要时传 `workflow=_step_workflow_rendered` 即可。

## 刚才发生了什么

- `minimal_init()` + `create_agent()` → 可以对话
- `ChatObject` = 一次对话：工作流 + 流 + 会话
- 默认工作流 = 简单对话（一次调用、一个回答）
- Step 循环需要显式传 `workflow=_step_workflow_rendered`

## 下一步

[2. 给 Agent 添加工具](tools.md)——让你的 agent 有事可做。
