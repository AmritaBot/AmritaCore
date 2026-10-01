# BillingBackend

接收逐请求计费记录的可选外部接收端的抽象基类。

## 描述

`BillingBackend` 是**可选的镜像出口，而非默认持久化路径**。每条记录本身已经随 [`MemoryModel.billing`](MemoryModel.md) 一起流动，因此一次会话的成本历史无需任何计费后端也能通过常规的记忆提交得以保留。仅当同一批记录还需要进入外部成本存储（数据库、指标管道、配额执行器）时，才需要实现本接口。

粒度是单次运行：`commit_billing` 在运行结束时被调用一次，携带该次运行产生的全部记录。

## 方法

### `commit_billing(session_id: str, records: list[BillingRecord]) -> None`

追加一次运行产生的记录。

**参数**：

- `session_id` (str)：会话标识符
- `records` (list[[BillingRecord](BillingRecord.md)])：该次运行的记录，按记录顺序排列

### `load_billing(session_id: str) -> list[BillingRecord]`

返回此前为某会话提交的记录。

**参数**：

- `session_id` (str)：会话标识符

**返回**：list[[BillingRecord](BillingRecord.md)] - 该会话已存储的记录

## 内置实现

- `NullBillingBackend`：空操作接收端，记录仅留在内存
- [`LegacyBackend`](LegacyBackend.md)：由锁保护的进程内存储，同时也是 [`BackendSlots.billing`](BackendSlots.md) 的默认值

## 接入自定义接收端

```python
from amrita_core import BackendSlots, BillingBackend, BillingRecord, LegacyBackend


class MyBillingSink(BillingBackend):
    async def commit_billing(
        self, session_id: str, records: list[BillingRecord]
    ) -> None:
        await my_db.insert_many(session_id, records)

    async def load_billing(self, session_id: str) -> list[BillingRecord]:
        return await my_db.fetch(session_id)


backend = LegacyBackend()
slot = BackendSlots(ability=backend, memory=backend, billing=MyBillingSink())
```

## 调用时机

`COMMIT_MEMORY` 是工作流的终结节点，按顺序执行三步：

1. 把本次运行的账本移入 `memory.billing`（`SessionUsageProxy.flush_into`）
2. 通过 `slot.memory` 提交记忆
3. 把同一批记录交给 `slot.billing`

将 `DatabackendOptions.skip_billing_commit` 设为 `True` 只会跳过第 3 步，记忆仍会携带这些记录。

## 下一步

[BillingRecord](BillingRecord.md)——记录结构，或 [RateConfig](RateConfig.md)——价格快照。
