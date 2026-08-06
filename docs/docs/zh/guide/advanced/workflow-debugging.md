# 工作流调试

## 单步执行解释器

AmritaSense 的 `WorkflowInterpreter` 支持 `run_step_by()`——逐步产出每个节点
执行，而非跑完：

```python
async def debug(chat: ChatObject) -> None:
    interp = chat._interpreter
    async for result in interp.run_step_by():
        print(f"→ {result}")
```

结合[挂起点](suspend.md)在节点之间检查状态。

## 节点断点

`@Node(tag=...)` 标签兼作挂起点。外部代码可在流上 `wait_to_suspend(tag)`，
精确停在感兴趣的节点——例如 `"ChatObject::step_intro"` 在每次 Step 边界
暂停。

## 中间件

用 `middleware` 包装整个工作流做粗粒度控制：

```python
async def trace_middleware(chat: ChatObject) -> None:
    print(f"[trace] start {chat.stream_id}")
    try:
        await chat._interpreter.run()
    finally:
        print(f"[trace] done {chat.stream_id}")

chat = ChatObject(..., middleware=trace_middleware)
```

## 常见检查点

| 检查什么       | 在哪                                         |
| -------------- | -------------------------------------------- |
| 当前 Step 状态 | `chat._di_loop.run_state`（`AgentRunState`） |
| 策略上下文     | `chat._di_loop.stg_ctx`                      |
| 消息列表       | `chat._di_working.context_wrap`              |
| 流事件         | `get_response_generator()` 的元数据条目      |
| 会话记忆       | `chat._di_memory.memory`                     |

> 用 AmritaSense 的术语，`run_step_by()` 与中间件是引擎特性——通用调试参考
> 见 [sense.amritabot.com](https://sense.amritabot.com)。
