# DatabackendOptions

控制 `ChatObject` 执行期间执行哪些后端获取和提交操作的选项。

## 描述

`DatabackendOptions` 提供了对框架管理的数据获取策略的细粒度控制。通过将标志设置为 `True`，可以跳过特定的后端操作，这对于性能优化或某些数据已经可用的情况非常有用。

## 字段

- `skip_memory_fetch` (bool): 跳过从后端加载记忆（默认：`False`）
- `skip_tools_fetch` (bool): 跳过从后端加载工具（默认：`False`）
- `skip_mcp_fetch` (bool): 跳过从后端加载 MCP 客户端（默认：`False`）
- `skip_presets_fetch` (bool): 跳过从后端加载预设（默认：`False`）
- `skip_ability_extra_setting` (bool): 跳过从后端加载额外能力设置（默认：`False`）
- `skip_memory_commit` (bool): 跳过在执行后将记忆提交回后端（默认：`False`）

## 用法

> **v0.12.0 迁移**: `DatabackendOptions` 已从 `amrita_core.chatmanager.chat_object` 移至 `amrita_core.contexts`。旧导入路径仍可通过兼容重导出工作，但建议更新为新路径。

```python
from amrita_core.contexts import DatabackendOptions

# 只加载记忆，跳过其他所有内容
opts = DatabackendOptions(
    skip_tools_fetch=True,
    skip_mcp_fetch=True,
    skip_presets_fetch=True,
    skip_ability_extra_setting=True,
)

chat = ChatObject(
    train=train,
    user_input="Hello",
    session_id="session_123",
    backend_options=opts,
)
```
