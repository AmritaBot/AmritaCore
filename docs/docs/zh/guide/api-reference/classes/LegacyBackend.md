# LegacyBackend

默认的内置后端，使用进程内全局容器实现 [AbilityBackend](AbilityBackend.md) 和 [MemoryBackend](MemoryBackend.md)。

## 描述

`LegacyBackend` 是未提供自定义后端时使用的默认后端。它保留了原始的 AmritaCore 行为，其中工具、预设、MCP 客户端和记忆存储在全局进程内容器中。适用于单进程应用和测试。

## 继承

`LegacyBackend` 同时实现了 [AbilityBackend](AbilityBackend.md) 和 [MemoryBackend](MemoryBackend.md)。

## 构造函数

```python
LegacyBackend(ctx: StateContext | None = None)
```

## 使用

```python
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.base.backend import BackendSlots

backend = LegacyBackend()
slot = BackendSlots(ability=backend, memory=backend)
```
