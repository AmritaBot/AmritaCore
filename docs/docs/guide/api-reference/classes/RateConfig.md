# RateConfig

Unit-price snapshot for one model, used for cost accounting.

## Description

`RateConfig` describes how much a model charges, expressed as a price per token bundle. It is attached to a [`ModelPreset`](ModelPreset.md) and copied verbatim into every [`BillingRecord`](BillingRecord.md) produced while that preset is active.

AmritaCore deliberately does **not** compute currency amounts. Prices are stored as `Decimal` so a consumer can multiply by token counts without accumulating binary floating-point error, and a later price change never rewrites historical records.

Because prices are `Decimal`, `model_dump()` returns `Decimal` objects. Use `model_dump(mode="json")` when serializing a preset to JSON.

## Fields

| Field      | Type      | Default        | Description                      |
| ---------- | --------- | -------------- | -------------------------------- |
| `per`      | `int`     | `1000`         | Token bundle the prices refer to |
| `input`    | `Decimal` | `Decimal("0")` | Price per `per` input tokens     |
| `output`   | `Decimal` | `Decimal("0")` | Price per `per` output tokens    |
| `currency` | `str`     | `"USD"`        | Currency code of the prices      |

## Attaching a Rate to a Preset

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

## Deriving a Cost

```python
rate = record.rate
if rate is not None:
    cost = (
        Decimal(record.prompt_tokens) * rate.input
        + Decimal(record.completion_tokens) * rate.output
    ) / rate.per
```

## Next

[BillingRecord](BillingRecord.md) - where the snapshot is stored.
