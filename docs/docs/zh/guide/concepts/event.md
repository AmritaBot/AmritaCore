# 事件系统

AmritaCore 的管线是**事件驱动**的。工作流节点与策略分发事件；注册的
**matcher** 拦截它们、可以修改它们，并通过异常控制流程。

## Matcher——钩子原语

用 AmritaSense 的术语：事件是 `ConstructableEvent`，通过
`MatcherFactory.trigger_event(event, exception_ignored=...)` 分发。Matcher
按**事件类型字符串**匹配：

```python
from amrita_sense.hook.matcher import Matcher

matcher = Matcher("agent.step_intro", priority=1)


@matcher.handle()
async def on_step_intro(event): ...
```

> 使用**字面量字符串**，不要用 `SomeEvent.event_type`——那是 property 对象
> 而非字符串。

## 事件类别

### 管线事件

| 事件                 | 类型字符串 | 触发时机                        |
| -------------------- | ---------- | ------------------------------- |
| `PreCompletionEvent` | —          | LLM 调用前（在此修改上下文）    |
| `CompletionEvent`    | —          | 响应后（改写 `model_response`） |

便捷装饰器：`@on_precompletion`、`@on_completion`、`@on_event("<type>")`。

### Step 生命周期事件（内置 ReAct）

| 类型字符串             | 可变字段                           | 触发时机       |
| ---------------------- | ---------------------------------- | -------------- |
| `agent.step_intro`     | `override_phase`                   | Step 开始      |
| `agent.step_leave`     | `override_verb`、`override_object` | Step 结束      |
| `agent.step_iteration` | `end_step`                         | 每轮工具调用后 |
| `agent.tool_call`      | `arguments`、`cancel`              | 常规工具执行前 |
| `agent.tool_return`    | `result`、`skip_append`            | 常规工具返回后 |

所有 step 事件通过各自的 `constructor()` 类方法从 `AgentRunState` 构建。

## 修改与控制流

两个强大特性：

1. **事件可变**——钩子在分发后读回字段：

   ```python
   @on_event("agent.step_leave")
   async def fix_summary(event):
       event.override_verb = "Reviewed"  # 替换自动摘要
   ```

2. **`exception_ignored`**——列出的异常从 `trigger_event` 传播回钩子。
   `StepAbortError`（一个 `BaseException`）是框架的控制流信号：

   ```python
   from amrita_core.builtins.agent.events import StepAbortError


   @on_event("agent.tool_call")
   async def block_tool(event):
       raise StepAbortError("blocked")  # 工具永不执行
   ```

## 事件如何到达节点

工作流节点与生命周期钩子调用 `_trigger_step_event(...)`；同进程注册的
matcher 看到每次分发。这是护栏、遥测与人机协同的扩展点。

## 下一步

[工具系统](tool.md)——工具如何定义与执行。
