# Agent 策略

## 策略契约

策略实现 `AgentStrategy` ABC（或有状态实例用 `StrategyLikedObject`），并通过
`get_category()` 声明**类别**：

| 类别                    | 执行方式                | 框架的角色   |
| ----------------------- | ----------------------- | ------------ |
| `agent` / `agent-mixed` | 每轮 `single_execute()` | 框架运行循环 |
| `rag` / `workflow`      | 一次 `run()`            | 策略完全掌控 |

`_run_strategy` 按类别分派并跳入对应的工作流块。

## 通过 DI 获取资源

策略从不穿过 `ChatObject` 拿资源——`_StrategyBase` 暴露**便捷属性**，
从 `StrategyContext` DI 字段解析，回退到 `chat_object`：

| 属性                    | 解析自                 | 回退                               |
| ----------------------- | ---------------------- | ---------------------------------- |
| `self.preset`           | `ctx.preset`           | `chat_object.preset`               |
| `self.config`           | `ctx.config`           | `chat_object.config`               |
| `self.io_stream`        | `ctx.io_stream`        | `chat_object.io_stream`            |
| `self.train_content`    | `ctx.train_content`    | `chat_object.train.content`        |
| `self.stream_id`        | `ctx.stream_id`        | `chat_object.stream_id`            |
| `self.resp_extra_usage` | `ctx.resp_extra_usage` | `chat_object._di_resp.extra_usage` |

> `chat_object` 是**生命周期管理器句柄**——核心引用，不是弃用路径。
> 优先 DI 字段；回退 `chat_object`。

## 内置 Step 驱动 ReAct 策略

`ReActAgentStrategy`（类别 `agent-mixed`）是默认策略类。其执行是**节点驱动**
的：LLM 决定是否把任务分解为语义 DAG；框架按拓扑序走 DAG，每个 **Step**
对应一个节点。

```
intro_step → [NATIVE_WHILE: single_execute → after_iteration] → leave_step
```

- **decompose** —— LLM 返回 `{needs_decomposition, dag, reason}`（或 simple 模式）
- **Step** —— 一个 DAG 节点；可跨多轮工具调用
- **停滞检测** —— 重复相同签名 → give-up prompt + 取消
- **摘要** —— 每个 Step 以主谓短语摘要结束（可被事件覆盖）
- **生命周期事件** —— `step_intro/leave/iteration`、`tool_call/return`
- **update_step 工具** —— agent 可中途修订计划

> **工作流需显式启用。** 策略类默认是 `ReActAgentStrategy`，但 Step 循环
> 只在 **step 循环工作流** 激活时才运行。`ChatObject` 默认是简单对话工作流
> （一次 LLM 调用、不分解）；传入 `workflow=_step_workflow_rendered`
> （或 `SIMPLE_STEP_REACT`）即可启用上面的循环。见
> [ChatObject](chat-object.md) 与 [进阶 → Step 循环](../advanced/step-loop.md)。

完整细节：[进阶 → Step 循环](../advanced/step-loop.md)。

## 其他内置策略

| 策略                       | 类别          | 用途                                               |
| -------------------------- | ------------- | -------------------------------------------------- |
| `HybridReActAgentStrategy` | `agent-mixed` | MoE 模型；XML 风格结果（**已弃用，v0.14.0 移除**） |
| `NoActionAgentStrategy`    | `workflow`    | 完全跳过工具调用                                   |

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

ReAct 风格策略请扩展 `BaseReActAgentStrategy`，覆写模板方法
（`_append_tool_result_to_context`、`_handle_error_append`、
`_append_reasoning`……）。

## 下一步

[数据层](data.md)——消息、记忆与后端。
