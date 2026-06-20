# LegacyBackend

默认的内置后端，使用进程内全局容器同时实现 [AbilityBackend](AbilityBackend.md) 和 [MemoryBackend](MemoryBackend.md)。

## 描述

`LegacyBackend` 是未提供自定义后端时使用的默认后端。它保留了原始的 AmritaCore 行为，即工具、预设、MCP 客户端和记忆存储在进程内全局容器中。适用于单进程应用和测试。

## 继承

`LegacyBackend` 同时实现了 [AbilityBackend](AbilityBackend.md) 和 [MemoryBackend](MemoryBackend.md)。

## 构造函数

```python
LegacyBackend(ctx: StateContext | None = None)
```

**参数**：

- `ctx` ([StateContext](StateContext.md) | None, 可选): 可选的预构建状态上下文。如果未提供，则在执行记忆操作时延迟创建新的状态上下文

## 行为

- **能力方法**（`load_ability_all`、`load_mcp_clients`、`load_tools`、`load_presets`）：都返回对共享全局 `AbilityContext` 单例（`LegacyBackend.glb`）的引用
- **记忆方法**（`load_memory`、`commit_memory`）：从每个 `LegacyBackend` 实例的内部 `StateContext` 读取和写入

## 用法

```python
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.base.backend import BackendSlots

backend = LegacyBackend()
slot = BackendSlots(ability=backend, memory=backend)
```
