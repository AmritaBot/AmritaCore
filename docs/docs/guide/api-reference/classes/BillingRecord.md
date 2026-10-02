# BillingRecord

Usage and pricing snapshot for one provider request.

## Description

Granularity is a **single request**: every completion or tool-calling round that reaches the provider appends at most one `BillingRecord` to the run's ledger. `model`, `preset_name` and `rate` are stored alongside the counts, so a record stays self-describing after presets or prices change.

Records are collected in a run-scoped `SessionUsageProxy` while the run is in flight, then copied into [`MemoryModel.billing`](MemoryModel.md) at the end of the run. That list is the default persistence path; a [`BillingBackend`](BillingBackend.md) is only needed to mirror the same data elsewhere.

AmritaCore does not compute currency amounts. Consumers derive money from `rate` and the token counts.

## Fields

| Field               | Type                                    | Default       | Description                               |
| ------------------- | --------------------------------------- | ------------- | ----------------------------------------- |
| `model`             | `str \| None`                           | `None`        | Model name used for the request           |
| `preset_name`       | `str \| None`                           | `None`        | Preset name the request was issued with   |
| `rate`              | [`RateConfig`](RateConfig.md)` \| None` | `None`        | Pricing snapshot captured at request time |
| `prompt_tokens`     | `int`                                   | `0`           | Prompt tokens reported                    |
| `completion_tokens` | `int`                                   | `0`           | Completion tokens reported                |
| `total_tokens`      | `int`                                   | `0`           | Total tokens reported                     |
| `cache_hit`         | `int \| None`                           | `None`        | Tokens read from cache                    |
| `cache_creation`    | `int \| None`                           | `None`        | Tokens spent creating cache entries       |
| `session_id`        | `str`                                   | `""`          | Owning session id                         |
| `stream_id`         | `str`                                   | `""`          | Owning run id                             |
| `request_id`        | `str \| None`                           | `None`        | Provider request id                       |
| `ts`                | `float`                                 | `time.time()` | Record timestamp                          |

## Reading Records

```python
records = chat.data.billing
total = sum(r.total_tokens for r in records)
by_preset = {r.preset_name for r in records}
```

## Next

[RateConfig](RateConfig.md) - the pricing snapshot, or [BillingBackend](BillingBackend.md) - forwarding records to an external store.
