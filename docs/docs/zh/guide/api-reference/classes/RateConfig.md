# RateConfig

单个模型的价格快照，用于成本核算。

## 描述

`RateConfig` 描述模型的计费方式，表示为每若干 token 的价格。它挂载在 [`ModelPreset`](ModelPreset.md) 上，并在该预设生效期间逐字复制进每一条 [`BillingRecord`](BillingRecord.md)。

AmritaCore 刻意**不计算货币金额**。价格以 `Decimal` 存储，消费方乘以 token 计数时不会累积二进制浮点误差，且后续调价不会改写历史记录。

由于价格是 `Decimal`，`model_dump()` 返回的是 `Decimal` 对象。将预设序列化为 JSON 时请使用 `model_dump(mode="json")`。

## 字段

| 字段       | 类型      | 默认值         | 说明                         |
| ---------- | --------- | -------------- | ---------------------------- |
| `per`      | `int`     | `1000`         | 价格所指的 token 数量        |
| `input`    | `Decimal` | `Decimal("0")` | 每 `per` 个输入 token 的价格 |
| `output`   | `Decimal` | `Decimal("0")` | 每 `per` 个输出 token 的价格 |
| `currency` | `str`     | `"USD"`        | 价格所用货币代码             |

## 为预设挂载价格

```python
from decimal import Decimal

from amrita_core import ModelPreset, RateConfig

preset = ModelPreset(
    model="deepseek-chat",
    name="deepseek",
    api_key="sk-...",
    max_context=64_000,
    max_output=8_000,
    rate=RateConfig(
        per=1_000_000,
        input=Decimal("0.27"),
        output=Decimal("1.10"),
        currency="USD",
    ),
)
```

## 推导开销

```python
rate = record.rate
if rate is not None:
    cost = (
        Decimal(record.prompt_tokens) * rate.input
        + Decimal(record.completion_tokens) * rate.output
    ) / rate.per
```

## 下一步

[BillingRecord](BillingRecord.md)——快照存放的位置。
