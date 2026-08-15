# 挂起与恢复

## 机制

每个 `ChatObject` 拥有一个 `SuspendObjectStream`（用 AmritaSense 的术语：
工作流是 producer，你的代码是 consumer）。流支持**挂起**：producer 在标记点
阻塞，直到外部 `resume()`。

- `wait_to_suspend(tags)` —— 请求 producer 在带标签的断点阻塞
- `resume()` —— 释放它
- `@Node(SuspendEnum.X)` 标签兼作断点（如 `STEP_INTRO`、`MEMORY`、`COMPLE`）

```python
import asyncio


async def interactive(chat):
    stream = chat.io_stream
    suspend_task = asyncio.create_task(stream.wait_to_suspend("ChatObject::step_intro"))
    run_task = asyncio.create_task(chat.begin())
    await suspend_task  # producer 现在停在 Step 边界
    # ... 检查或注入 ...
    stream.resume()  # 让 agent 继续
    await run_task
```

> Core 在此回顾 Sense 机制；完整 API 见
> [sense.amritabot.com — SuspendObjectStream](https://sense.amritabot.com/reference/api/suspend-object-stream)。

## 双向流

流有**两条独立通道**：

| 方向       | Producer API                        | Consumer API                                    |
| ---------- | ----------------------------------- | ----------------------------------------------- |
| Agent → 你 | `yield_response()`、`push_object()` | `get_response_generator()`                      |
| 你 → Agent | `get_producer_input_generator()`    | `send_to_producer()`、`send_done_to_producer()` |

### Peer → Agent 在 Step 边界注入

`send_to_producer()` 推送的消息由策略在下一个 Step 边界（`intro_step`）消费，
以 `[peer message]` 用户消息追加到对话上下文：

- **Step 开始前**推送 → 在该边界消费
- **agent 工作期间**推送 → 排队至下一个边界
- **运行结束后**推送 → 丢弃（通道关闭）

这实现了人机协同反馈、外部上下文注入与流式输入。实践用法见
[流式](../tutorials/streaming.md)。

## 规则

- 每方向单一 consumer：生成器 _或_ 回调（不能同时）
- `set_queue_done()` 后，进一步 `yield_response` 抛 `StreamStateError`
- `send_done_to_producer()` 后，进一步 `send_to_producer` 快速失败——
  不阻塞队列超时

## 下一步

[Step 循环](step-loop.md)——内置 Step 驱动 ReAct 循环（显式启用：传 `workflow=_step_workflow_rendered`）。
