# 3. 流式与回调

## 本章目标

看到 agent 输出实时产生——并读懂藏在流里的结构化事件。学完你能：

- 用异步生成器（拉）或回调（推）消费流
- 区分纯文本 chunk 与 `MessageWithMetadata` 事件
- 通过反向通道把消息*推回*给 agent

## 概念速览（用到才讲）

- **`SuspendObjectStream`**：每个 `ChatObject` 拥有的双向通道。工作流写入它；
  你的代码从它读取。
- **`MessageWithMetadata`**：与纯文本同行的结构化事件（Step 边界、工具调用、
  推理 chunk）。

## 1. 流式读取响应

每个 `ChatObject` 暴露 `chat.io_stream`——一个 `SuspendObjectStream`。
用 AmritaSense 的术语：工作流是 _producer_，你的代码是 _consumer_；
用异步生成器读取响应：

```python
async with chat.begin():
    async for msg in chat.io_stream.get_response_generator():
        print(msg, end="", flush=True)
```

## 2. 两种条目

流携带**两种**条目：

| 条目                  | 含义                                        |
| --------------------- | ------------------------------------------- |
| `str`                 | 纯文本 chunk（逐 token）                    |
| `MessageWithMetadata` | 结构化事件：Step 边界、工具调用、推理 chunk |

```python
async with chat.begin():
    async for msg in chat.io_stream.get_response_generator():
        if isinstance(msg, str):
            print(msg, end="", flush=True)
        else:
            content = getattr(msg, "content", None)
            meta = getattr(msg, "metadata", None)
            if content:
                print(f"\n[{meta}] {content}", flush=True)
```

### 常见元数据类型

| `type`            | `extra_type`         | 触发时机                                            |
| ----------------- | -------------------- | --------------------------------------------------- |
| `step`            | `decompose`          | 策略决定 simple 还是 DAG 规划                       |
| `step`            | `intro` / `leave`    | Step 开始 / 结束（带摘要）                          |
| `step`            | `stall` / `compress` | 检测到停滞 / 历史压缩                               |
| `function_call`   | —                    | 工具开始（`is_done=False`）或结束（`is_done=True`） |
| `reasoning_chunk` | `cot_chunk`          | thinking 模式推理流式输出                           |

> `step` 元数据只在 **step 循环工作流** 激活时存在
> （`get_chatobject(..., workflow=_step_workflow_rendered)`）；默认的
> 简单对话工作流从不发出它。

## 3. 基于回调的消费

喜欢推而不是拉？注册回调代替读取生成器：

```python
from amrita_core import SuspendObjectStream

stream = SuspendObjectStream(callback=on_chunk)
```

> 每个流只允许一种消费方式——生成器 _或_ 回调。

## 4. 反向通道（Peer → Agent）

`SuspendObjectStream` 是**双向**的。consumer 可以用 `send_to_producer()`
把消息推回 producer；agent 在下一个 Step 边界消费并追加到对话上下文：

```python
await chat.io_stream.send_to_producer(
    "IMPORTANT: end your final answer with the exact line: [peer-acked]"
)
```

- **Step 开始前**推送的消息 → 在该边界被消费。
- **agent 工作期间**推送 → 在下一个边界被拾取。
- **运行结束后**推送 → 被丢弃（通道已关闭）。

这是人机协同、工具反馈与流式输入的基础。完整机制见
[挂起/恢复](../advanced/suspend.md)。

## 刚才发生了什么

- 流既可拉取（`get_response_generator`）也可推送（回调）
- 结构化元数据与纯文本同行
- 反向通道让你在 Step 边界注入上下文

## 下一步

[4. 事件与钩子](event-hooks.md)——以编程方式拦截管线。
