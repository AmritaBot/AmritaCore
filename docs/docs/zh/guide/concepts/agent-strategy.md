# Agent 策略

## 策略契约

策略实现 `AgentStrategy` ABC（或有状态实例用 `StrategyLikedObject`），并通过
`get_category()` 声明**类别**：

| 类别                    | 执行方式                | 框架的角色   |
| ----------------------- | ----------------------- | ------------ |
| `agent` / `agent-mixed` | 每轮 `single_execute()` | 框架运行循环 |
| `rag` / `workflow`      | 一次 `run()`            | 策略完全掌控 |

分派属于工作流控制流，而不是 Python：`_prepare_strategy` 只构建
`StrategyContext`，随后两个带守卫的分支选定执行形态——
`NATIVE_IF(is_agent_category, ...)` 运行框架循环，
`NATIVE_IF(not_agent_category, RUN_INLINE_STRATEGY)` 调用一次 `run()`。
各自在断言为假时被跳过，因此任何类别都不会被执行两次
（见[工作流引擎](../advanced/workflow-engine.md)）。

## 通过 DI 获取资源

策略从不穿过 `ChatObject` 拿资源——`_StrategyBase` 暴露**便捷属性**，
从 `StrategyContext` DI 字段解析，回退到 `chat_object`：

| 属性                 | 解析自              | 回退                                      |
| -------------------- | ------------------- | ----------------------------------------- |
| `self.preset`        | `ctx.preset`        | `chat_object.preset`                      |
| `self.config`        | `ctx.config`        | `chat_object.config`                      |
| `self.io_stream`     | `ctx.io_stream`     | `chat_object.io_stream`                   |
| `self.train_content` | `ctx.train_content` | `chat_object.train.content`               |
| `self.stream_id`     | `ctx.stream_id`     | `chat_object.stream_id`                   |
| `self.usage`         | `ctx.usage`         | `chat_object._di_resp.usage`，否则 `None` |

> `self.usage` 是运行级作用域的 `SessionUsageProxy` 账本。它覆盖工作流内部用量
> （策略工具轮次加上辅助调用）；最终补全的用量位于 `resp.response.usage`。

> `chat_object` 是**生命周期管理器句柄**——核心引用，不是弃用路径。
> 优先 DI 字段；回退 `chat_object`。

## 内置 Step 驱动 ReAct 策略

`ReActAgentStrategy`（类别 `agent-mixed`）是默认策略类。其执行是**节点驱动**
的：LLM 决定是否把任务分解为语义 DAG；框架按拓扑序走 DAG，每个 **Step**
对应一个节点。

```
intro_step → [NATIVE_WHILE: single_execute → after_iteration] → leave_step
```

- **decompose** —— LLM 返回 `{needs_decomposition, dag, reason}`。
  **SIMPLE 模式（`needs_decomposition=false`）也是 ReAct**——普通工具循环照常
  运行，只是非步骤驱动（不分解 DAG）；常规提问与简单任务默认分配到此模式。
- **Step** —— 一个 DAG 节点；可跨多轮工具调用
- **停滞检测** —— 重复相同签名 → give-up prompt + 取消
- **摘要** —— 每个 Step 以主谓短语摘要结束（可被事件覆盖）
- **生命周期事件** —— `step_intro/leave/iteration`、`tool_call/return`
- **update_step 工具** —— agent 可中途修订计划

> **工作流需显式启用。** 策略类默认是 `ReActAgentStrategy`，但 Step 循环
> 只在 **step 循环工作流** 激活时才运行。`ChatObject` 默认使用
> `_workflow_rendered`，其 agent 分支是**传统单调用循环**（`AGENT_BLOCK`）——
> 每轮一次 `single_execute`、不做 DAG 分解；传入
> `workflow=_step_workflow_rendered`
> （或 `SIMPLE_STEP_REACT`）即可启用上面的循环。见
> [ChatObject](chat-object.md) 与 [进阶 → Step 循环](../advanced/step-loop.md)。

完整细节：[进阶 → Step 循环](../advanced/step-loop.md)。

## Agentic 调用路径

策略不必把"要工具调用"和"要文本"拆成两次请求。当 preset 开启了原生思考**且**它的协议适配器实现了 [`agentic_call_api()`](../api-reference/classes/ModelAdapter.md#agentic_call_api) 时，内置 ReAct 策略会走 **agentic 路径**：每一轮都是一次请求，边生成边流出文本，并在末尾交出该轮的工具调用。

有三点关键：

- **每次请求都声明工具。** 工具定义随每一轮一起发送，包括产生终答的那一轮。历史里带着 `tool_calls`、而请求本身却不声明 `tools`，正是让 provider 要么拒绝该 payload、要么让模型把调用写成纯文本而不是结构化调用的原因。
- **不返回工具调用的那一轮就是终答。** 它的内容已经流出去了，工作流会跳过那次独立的、不带工具的 completion。不会再发第二次请求来生成回复。
- **`tool_choice` 保持 `auto`。** 原生思考的 provider 会拒绝强制值，因此 `required` 会在发送前被降级。

当适配器不具备该能力，或思考关闭时，策略走传统路径：先用 `tools_caller()` 跑工具轮，再单独发一次 completion。这条组合会记录一条 warning，因为该路径上最后一次请求不携带工具定义。

## 其他内置策略

| 策略                    | 类别       | 用途             |
| ----------------------- | ---------- | ---------------- |
| `NoActionAgentStrategy` | `workflow` | 完全跳过工具调用 |

## 编写自定义策略

```python
from amrita_core.agent.strategy import AgentStrategy
from typing import Literal


class MyStrategy(AgentStrategy):
    async def single_execute(self) -> bool:
        # 一轮工具调用。返回 True 继续，False 停止。
        return True

    async def on_post_process(self) -> None:
        pass  # 循环结束后

    @classmethod
    def get_category(cls) -> Literal["agent"]:
        return "agent"
```

ReAct 风格策略请扩展 `BaseReActAgentStrategy`，覆写 `_append_reasoning`
（唯一的抽象方法）；`_append_tool_results_batch` 与 `_handle_error_append`
可以覆写，但已有可用的默认实现。

## 下一步

[数据层](data.md)——消息、记忆与后端。
