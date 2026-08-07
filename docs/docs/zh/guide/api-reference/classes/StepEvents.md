# Step 生命周期事件

step 循环在每个边界发出**可变**事件。按事件类型字符串注册的 matcher 可以
修改事件字段(钩子读回修改后的值),或抛 `StepAbortError` 控制流程。

```python
from amrita_sense.hook.matcher import Matcher

matcher = Matcher("agent.tool_call", priority=1)


@matcher.handle()
async def guard(event):
    event.cancel = True


# 测试/运行后清理:
# matcher._dead_at = <过去的时间>
```

> 使用**字面量字符串**(`"agent.step_intro"`),不要用
> `StepIntroEvent.event_type`——那是 property 对象。

## StepAbortError

matcher 抛出的 `BaseException`,用于中止当前操作——经 `exception_ignored`
从 `trigger_event` 传播回钩子,由钩子决定如何处理(跳过工作、提前结束 Step……)。

## 事件

### StepIntroEvent —— `agent.step_intro`

Step 开始时(`intro_step`)广播。

| 字段             | 含义                     |
| ---------------- | ------------------------ |
| `step_index`     | 全局 step 计数器         |
| `phase`          | 进入的阶段               |
| `simple_mode`    | 裸运行(无 DAG)?          |
| `plan_summary`   | 前 5 个计划描述          |
| `override_phase` | **可变** —— 重定向阶段名 |

### StepLeaveEvent —— `agent.step_leave`

Step 结束时(`leave_step`)广播。

| 字段                                | 含义                      |
| ----------------------------------- | ------------------------- |
| `step_index` / `phase`              | 哪个 Step                 |
| `verb` / `object`                   | 自动摘要(主谓)            |
| `stall_injected`                    | 是否注入了 give-up prompt |
| `override_verb` / `override_object` | **可变** —— 替换摘要      |

### StepIterationEvent —— `agent.step_iteration`

execute Step 内每轮工具调用后广播。

| 字段                   | 含义                      |
| ---------------------- | ------------------------- |
| `step_index` / `phase` | 哪个 Step                 |
| `tool_signatures`      | 当前窗口内的签名          |
| `end_step`             | **可变** —— 强制结束 Step |

### StepToolCallEvent —— `agent.tool_call`

常规工具执行*前*广播(内置工具除外)。

| 字段                    | 含义                                                |
| ----------------------- | --------------------------------------------------- |
| `tool_name` / `tool_id` | 工具调用                                            |
| `arguments`             | **可变** —— 改写调用参数                            |
| `cancel`                | **可变** —— 不执行直接取消(返回 `"Cancelled: ..."`) |

### StepToolReturnEvent —— `agent.tool_return`

常规工具返回*后*广播。

| 字段                    | 含义                             |
| ----------------------- | -------------------------------- |
| `tool_name` / `tool_id` | 工具调用                         |
| `result`                | **可变** —— 改写模型看到的结果   |
| `skip_append`           | **可变** —— 跳过把结果写回上下文 |

所有事件通过各自的 `constructor()` 类方法从 `AgentRunState` 构建。

## 相关

- [AgentRunState](AgentRunState.md) —— 事件构建自的状态
- [核心概念 → 事件系统](../concepts/event.md) —— matcher 机制
- [进阶 → Step 循环](../advanced/step-loop.md) —— 每个事件的触发时机
