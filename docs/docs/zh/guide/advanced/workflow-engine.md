# Workflow Engine — 工作流引擎

AmritaCore 的工作流引擎允许你定义涉及多个步骤、决策和外部交互的复杂顺序处理。

> **重要**：工作流引擎仅通过 `amrita-sense` 包提供。本节介绍概念以及如何在 AmritaCore 中集成工作流。

## 什么是工作流引擎？

工作流引擎是一个状态机，它编排多个步骤——agent 调用、工具执行和自定义逻辑——在一个单一的连贯流中。与简单的顺序执行不同，工作流支持：

- **条件分支**——根据前一步的输出改变步骤
- **并行执行**——同时运行独立步骤
- **错误恢复**——定义重试和回退行为
- **状态持久化**——跨步骤持久化数据

## 核心概念

### 步骤

工作流中的最小执行单元，一个步骤可以：

- 调用 LLM（获取完成结果）
- 执行工具（`ToolResult` 消耗）
- 运行业务逻辑（自定义处理函数）

### 转换

转换定义了步骤之间的移动方式：

- **条件**：仅当条件为真时应用
- **默认**：无条件应用

### 状态

工作流引擎维护跨步骤的持久状态：

- 来自前一步骤的结果数据
- 中间值和累积输出
- 错误和历史信息

## 基本工作流结构

```python
from amrita_sense.workflow import WorkflowEngine, Step, Transition

# 定义步骤
step1 = Step(name="获取上下文", handler=fetch_context_fn)
step2 = Step(name="生成响应", handler=generate_response_fn)

# 定义转换
transitions = [
    Transition(source="获取上下文", target="生成响应"),
]

# 创建并运行工作流
engine = WorkflowEngine(steps=[step1, step2], transitions=transitions)
result = await engine.run()
```

## 与智能体策略集成

工作流引擎与智能体策略（如 AmritaCore 内置智能体使用的 ReAct 循环）共享其架构，但是为显式步骤定义进行了推广。你可以：

- 在策略内使用工作流进行复杂的多步骤智能体行为
- 直接从工作流调用工具
- 步骤之间的挂起/恢复以进行交互式工作流

## 高级示例

参见[工作流调试](./workflow-debugging.md)中关于调试复杂工作流的完整示例，以及[依赖注入](./dependency-intro.md)中关于在工作流步骤中注入依赖的示例。
