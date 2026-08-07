# AgentRunState

`AgentRunState` 是内置 Step 驱动 ReAct 策略的**语义级 step 运行状态**。
它存在于工作流之外,在 `AgentLoopState.run_state` 与策略之间共享(同一实例,
由 `AGENT_ENTRY` 桥接)。

```python
from amrita_core.builtins.agent.state import AgentRunState

state = AgentRunState()
state.begin_step("execute")
```

## 字段

| 字段                   | 类型                    | 含义                                             |
| ---------------------- | ----------------------- | ------------------------------------------------ |
| `step_index`           | `int`                   | 全局 step 计数器(从 1 开始)                      |
| `current_phase`        | `str \| None`           | 当前阶段——DAG 节点 id(simple 模式为 `"execute"`) |
| `plan`                 | `list[DAGNode] \| None` | 任务 DAG(`None` = 未分解)                        |
| `simple_mode`          | `bool`                  | LLM 决定直接运行时为 True                        |
| `current_step_id`      | `str \| None`           | 正在执行的 DAG 节点 id                           |
| `completed_step_ids`   | `list[str]`             | 已完成的 DAG 节点 id(依赖检查)                   |
| `plan_revision`        | `int`                   | `update_step` 修订计数器                         |
| `step_tool_signatures` | `list[str]`             | 当前 Step 内的工具签名(停滞窗口)                 |
| `stall_injected`       | `bool`                  | give-up prompt 已注入(每 Step 一次)              |
| `last_summary`         | `StepSummary \| None`   | 前一个 Step 的主谓摘要                           |
| `tokens`               | `TokenBudget`           | 真实 API token 统计                              |
| `exec_finished`        | `bool`                  | 策略完成工具调用 → 迭代循环结束                  |

## 方法

| 方法                                | 用途                                                         |
| ----------------------------------- | ------------------------------------------------------------ |
| `begin_step(phase)`                 | 进入新 Step:推进计数器、重置 per-Step 状态                   |
| `begin_node(node)`                  | `begin_step(node.id)` + 跟踪 `current_step_id`               |
| `record_tool_call(signature)`       | 在当前 Step 记录工具签名                                     |
| `is_stalled(threshold)`             | 最后 N 个签名相同时为 True                                   |
| `would_stall(signature, threshold)` | 记录该签名是否会触发检测(执行前取消)                         |
| `next_ready_node()`                 | 拓扑序的下一个 DAG 节点(`graphlib.TopologicalSorter`;环降级) |
| `complete_current_node()`           | 标记当前节点完成                                             |
| `all_plan_done()`                   | 所有 DAG 节点完成时为 True                                   |

## 相关

- [DAGNode](DAGNode.md) —— 计划子步骤
- [StepSummary](StepSummary.md) —— 主谓摘要
- [TokenBudget](TokenBudget.md) —— token 统计
- 完整机制见[进阶 → Step 循环](../advanced/step-loop.md)
