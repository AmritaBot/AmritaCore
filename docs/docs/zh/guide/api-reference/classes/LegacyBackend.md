# LegacyBackend

默认的内置后端，使用进程内全局容器实现 [AbilityBackend](AbilityBackend.md)、[MemoryBackend](MemoryBackend.md) 和 [BillingBackend](BillingBackend.md)。

## 描述

`LegacyBackend` 是未提供自定义后端时使用的默认后端。它保留了原始的 AmritaCore 行为，其中工具、预设、MCP 客户端和记忆存储在全局进程内容器中。适用于单进程应用和测试。

## 继承

`LegacyBackend` 同时实现了 [AbilityBackend](AbilityBackend.md)、[MemoryBackend](MemoryBackend.md) 和 [BillingBackend](BillingBackend.md)。

## 构造函数

```python
LegacyBackend()
```

## 行为

- **能力方法**（`load_ability_all`、`load_mcp_clients`、`load_tools`、`load_presets`）：全部返回共享的全局 `AbilityContext` 单例引用（`LegacyBackend.glb`）
- **记忆方法**（`load_memory`、`commit_memory`）：读写一个 `MemoryModel` 字段，作用域为每个 `LegacyBackend` 实例
- **计费方法**（`commit_billing`、`load_billing`）：向按会话划分的进程内记录存储追加并从中读取，该存储由锁保护

## 使用

```python
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.base.backend import BackendSlots

backend = LegacyBackend()
slot = BackendSlots(ability=backend, memory=backend, billing=backend)
```
