# SuspendObjectStream — 挂起与恢复

AmritaCore 提供了一个内置的**挂起/恢复**机制，允许你在处理过程中随时暂停和恢复 `ChatObject` 的执行流。此功能支持交互式应用程序，其中用户干预或外部事件可能需要临时暂停智能体的工作流。

## 什么是挂起/恢复？

挂起/恢复机制允许 `ChatObject` 的控制流在处理过程中暂停并在稍后恢复，而不会丢失状态或导致故障。这是通过 `amrita-sense` 包中的 `SuspendObjectStream` 实现的，该包在 `ChatObject` 内部使用。

## 核心特性

- **非阻塞**：挂起不会阻塞主事件循环，允许其他 `asyncio` 任务并发运行
- **细粒度控制**：你可以在处理过程中的确切点挂起
- **可选超时**：支持超时以防止无限等待
- **无状态丢失**：恢复后状态得以保持

## 基本用法

### 使用 `suspend_object` 挂起

```python
from amrita_core import create_agent, minimal_init, suspend_object

@some_hook.handle()
async def check_something(chat_obj):
    result = await some_condition()
    if not result:
        await suspend_object(chat_obj)  # 挂起执行
    return result
```

`timeout` 参数指定在取消前等待的最长时间（秒）：

```python
await suspend_object(chat_obj, timeout=30)  # 30 秒后取消
```

### 使用 `.resume()` 恢复

挂起的 `ChatObject` 可以通过环境重置来重启：

```python
if chat_obj.io_stream.is_suspended():
    chat_obj.io_stream.resume()
```

## 使用场景

- **用户确认**：在继续之前提示用户批准
- **外部验证**：等待外部服务或 API
- **资源限制**：在重负载下暂停处理
- **调试**：暂停执行以检查智能体状态

## 内部原理

`ChatObject.io_stream` 内部使用的是来自 `amrita-sense` 包的 `SuspendObjectStream`，该包为 AmritaCore 流提供异步控制。该流在挂起状态和恢复能力之间转换，同时保持所有已消费的块完好无损。

当调用 `suspend_object()` 时，`SuspendObjectStream` 进入等待 `resume()` 被调用的暂停状态。在此期间，`begin()` 之后的异步任务保持活动但被阻塞，直到恢复。

## 高级用法的完整工作流

参见[工作流调试](../advanced/workflow-debugging.md)和[依赖注入](../advanced/dependency-intro.md)中的示例，了解在工作流中进行挂起/恢复模式的完整示例。
