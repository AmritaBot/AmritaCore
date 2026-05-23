# SuspendObjectStream

> **已迁移至 AmritaSense**。`amrita_core.streaming` 现为弃用包装器。

`SuspendObjectStream` 是 AnyIO 内存对象流之上的生产者-单消费者架构，内建挂起/恢复和流式响应能力。

**完整 API 文档**：[SuspendObjectStream — AmritaSense](https://sense.amritabot.com/reference/api/suspend-object-stream)

## 迁移

```python
# 旧（弃用）
from amrita_core.streaming import SuspendObjectStream

# 新
from amrita_sense.streaming import SuspendObjectStream
```

## 在 AmritaCore 中的使用

ChatObject 继承自 `SuspendObjectStream[RESPONSE_TYPE]`。所有流式交互方法均来自此基类：

| 方法                       | 用途                     |
| -------------------------- | ------------------------ |
| `yield_response()`         | 向队列或回调发送响应     |
| `get_response_generator()` | 异步迭代响应流           |
| `set_callback_func()`      | 设置响应回调             |
| `wait_to_suspend()`        | 外部等待挂起             |
| `resume()`                 | 恢复执行                 |
| `@suspend`                 | 可挂起方法装饰器         |
| `@suspend_with_tag(tag)`   | 带标签的可挂起方法装饰器 |

> **注意**：`callback` 与 `async for` 迭代**互斥**，同一实例只能使用一种方式消费响应流。
