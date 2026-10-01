# DatabackendOptions

控制 `ChatObject` 执行期间执行哪些后端获取和提交操作的选项。

## 描述

`DatabackendOptions` 对框架管理的获取策略提供细粒度控制。将标志设为 `True` 可以跳过特定的后端操作，这在做性能优化、或某些数据已经可用时很有用。

## 字段

- `skip_memory_fetch` (bool)：跳过从后端加载记忆（默认：`False`）
- `skip_tools_fetch` (bool)：跳过从后端加载工具（默认：`False`）
- `skip_mcp_fetch` (bool)：跳过从后端加载 MCP 客户端（默认：`False`）
- `skip_presets_fetch` (bool)：跳过从后端加载预设（默认：`False`）
- `skip_ability_extra_setting` (bool)：跳过从后端加载额外能力设置（默认：`False`）
- `skip_memory_commit` (bool)：跳过执行后将记忆提交回后端（默认：`False`）
- `skip_billing_commit` (bool)：跳过把计费记录交给 `BackendSlots.billing`（默认：`False`）。记录仍会写入 `MemoryModel.billing`，因此不会丢数据，只是跳过了外部镜像

## 使用

> **v0.12.0 迁移**：`DatabackendOptions` 已从 `amrita_core.chatmanager.chat_object` 迁移到 `amrita_core.contexts`。旧导入路径通过向后兼容的重导出仍然可用，但建议改用新路径。

```python
from amrita_core.contexts import DatabackendOptions

opts = DatabackendOptions(
    skip_tools_fetch=True,
    skip_mcp_fetch=True,
    skip_presets_fetch=True,
    skip_ability_extra_setting=True,
)

chat = ChatObject(
    train=train,
    user_input="你好",
    session_id="session_123",
    backend_options=opts,
)
```
