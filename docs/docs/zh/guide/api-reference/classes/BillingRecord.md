# BillingRecord

单次 provider 请求的用量与价格快照。

## 描述

粒度是**单次请求**：每一次抵达 provider 的补全或工具调用轮次，最多向本次运行的账本追加一条 `BillingRecord`。`model`、`preset_name` 与 `rate` 与计数一同保存，因此预设或价格变更后，记录仍能自我描述。

运行期间记录收集在本次运行作用域的 `SessionUsageProxy` 中，运行结束时复制进 [`MemoryModel.billing`](MemoryModel.md)。该列表即默认持久化路径；只有当同一批数据还需镜像到别处时，才需要 [`BillingBackend`](BillingBackend.md)。

AmritaCore 不计算货币金额。消费方依据 `rate` 与 token 计数自行推导。

## 字段

| 字段                | 类型                                    | 默认值        | 说明                        |
| ------------------- | --------------------------------------- | ------------- | --------------------------- |
| `model`             | `str \| None`                           | `None`        | 请求使用的模型名            |
| `preset_name`       | `str \| None`                           | `None`        | 发起请求所用的预设名        |
| `rate`              | [`RateConfig`](RateConfig.md)` \| None` | `None`        | 请求时刻捕获的价格快照      |
| `prompt_tokens`     | `int`                                   | `0`           | 上报的 prompt token 数      |
| `completion_tokens` | `int`                                   | `0`           | 上报的 completion token 数  |
| `total_tokens`      | `int`                                   | `0`           | 上报的总 token 数           |
| `cache_hit`         | `int \| None`                           | `None`        | 从缓存读取的 token 数       |
| `cache_creation`    | `int \| None`                           | `None`        | 创建缓存条目消耗的 token 数 |
| `session_id`        | `str`                                   | `""`          | 所属会话 id                 |
| `stream_id`         | `str`                                   | `""`          | 所属运行 id                 |
| `request_id`        | `str \| None`                           | `None`        | provider 请求 id            |
| `ts`                | `float`                                 | `time.time()` | 记录时间戳                  |

## 读取记录

```python
records = chat.data.billing
total = sum(r.total_tokens for r in records)
by_preset = {r.preset_name for r in records}
```

## 下一步

[RateConfig](RateConfig.md)——价格快照，或 [BillingBackend](BillingBackend.md)——把记录转发到外部存储。
