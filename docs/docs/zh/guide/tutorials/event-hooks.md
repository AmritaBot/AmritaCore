# 4. 事件与钩子

## 本章目标

不碰框架代码就能拦截管线。学完你能：

- 用装饰器钩住完成与预完成
- 按类型字符串匹配任意事件——包括 step 生命周期事件
- 修改事件并用 `StepAbortError` 控制流程

## 概念速览（用到才讲）

- **事件**：描述某事发生的对象（一次完成、一个 Step 边界、一次工具调用）。
- **Matcher**：按事件*类型字符串*注册的处理器。Matcher 可以修改事件；
  框架读回修改后的值。

管线是事件驱动的：基于 `Matcher` 的钩子让你拦截各阶段、修改消息、注入上下文。

## 1. 用 `@on_completion` 响应完成

```python
from amrita_core import on_completion
from amrita_core.hook.event import CompletionEvent


@on_completion
async def log_response(event: CompletionEvent):
    print(f"[completion] {event.model_response[:80]}...")
```

`CompletionEvent` 携带最终响应；你可以在提交前改写
`event.model_response`。

## 2. 用 `@on_precompletion` 预完成钩子

```python
from amrita_core import on_precompletion
from amrita_core.hook.event import PreCompletionEvent


@on_precompletion
async def inject_context(event: PreCompletionEvent):
    # `event.original_context` 是 SendMessageWrap——可追加任何内容。
    event.original_context.append(
        Message(role="user", content="[system note] Today is 2026-08-06.")
    )
```

## 3. 用 `@on_event` 自定义事件

按字符串匹配任意事件类型：

```python
from amrita_core import on_event


@on_event("agent.step_intro")
async def on_step_intro(event):
    print(f"[step intro] {event.phase}")
```

### Step 生命周期事件（内置 ReAct）

| 事件类型               | 可变字段                           | 触发时机              |
| ---------------------- | ---------------------------------- | --------------------- |
| `agent.step_intro`     | `override_phase`                   | Step 开始             |
| `agent.step_leave`     | `override_verb`、`override_object` | Step 结束（覆盖摘要） |
| `agent.step_iteration` | `end_step`                         | 每轮工具调用后        |
| `agent.tool_call`      | `arguments`、`cancel`              | 常规工具执行前        |
| `agent.tool_return`    | `result`、`skip_append`            | 常规工具返回后        |

> `agent.step_*` 事件要求 **step 循环工作流**
> （`get_chatobject(..., workflow=_step_workflow_rendered)`）；默认的
> 简单对话工作流不会触发它们。

handler 可以**修改事件**，生命周期钩子读回修改后的值；也可以抛
`StepAbortError` 中止当前操作（取消工具调用、提前结束 Step、跳过追加结果）。

```python
from amrita_core import on_event
from amrita_core.builtins.agent.events import StepAbortError


@on_event("agent.tool_call")
async def guard_tool(event):
    if event.tool_name == "dangerous_delete":
        event.cancel = True  # 或: raise StepAbortError("blocked")
```

## 4. 刚才发生了什么

- `@on_completion` / `@on_precompletion`——管线边界
- `@on_event("<type>")`——任意事件，包括 step 生命周期
- 事件可变；`StepAbortError` 是控制流逃生舱

## 下一步

[5. 记忆与会话](memory.md)——跨轮次持久化历史。
