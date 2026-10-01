# NullBillingBackend

空操作计费出口；记录仅留在内存。

## 描述

`NullBillingBackend` 把每个 [`BillingBackend`](BillingBackend.md) 方法都实现为空操作。当你希望显式声明「不把计费记录转发到任何地方」，而不是让 `BackendSlots.billing` 保持默认值时，就绑定它。

注意**省略计费后端本来就是无害的**：记录仍会累积在 `MemoryModel.billing`，那是默认持久化路径。`NullBillingBackend` 存在的意义是让这一意图在代码中可见，以及为需要「可证明什么都不做」的后端的测试提供支持。

## 方法

### `async commit_billing(session_id, records) -> None`

立即返回。丢弃记录。

### `async load_billing(session_id) -> list[BillingRecord]`

始终返回空列表。

## 使用

```python
from amrita_core import BackendSlots, LegacyBackend, NullBillingBackend

backend = LegacyBackend()
slot = BackendSlots(
    ability=backend,
    memory=backend,
    billing=NullBillingBackend(),  # 显式声明「不镜像到任何地方」
)
```

## 相关

- [BillingBackend](BillingBackend.md)——接口
- [LegacyBackend](LegacyBackend.md)——默认计费出口
- [BackendSlots](BackendSlots.md)——承载它的槽位
