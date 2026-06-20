# AbilityContext

保存 `ChatObject` 运行时会话中能力相关状态的数据类。

## 描述

`AbilityContext` 将工具、预设、MCP 客户端和额外设置捆绑在一起，定义了 `ChatObject` 在会话期间可以执行的操作。

## 字段

- `tools` ([MultiToolsManager](MultiToolsManager.md)): 会话中可用的工具管理器。默认为全局 `ToolsManager()` 单例
- `presets` ([MultiPresetManager](MultiPresetManager.md)): 会话中的模型预设管理器。默认为全局 `PresetManager()` 单例
- `mcp` ([MultiClientManager](MultiClientManager.md)): MCP 客户端连接管理器。默认为全局 `ClientManager()` 单例
- `extra` (dict[str, Any]): 与能力上下文关联的额外自定义数据

## 默认行为

每个字段默认为对应的全局管理器单例，该单例在所有会话之间共享。要使用会话隔离的管理器，请将字段替换为新的 `MultiToolsManager()`、`MultiPresetManager()` 或 `MultiClientManager()` 实例。

## 用法

```python
from amrita_core.contexts import AbilityContext

ctx = AbilityContext()
# 所有字段默认为全局单例
print(ctx.tools)  # ToolsManager 单例
print(ctx.presets)  # PresetManager 单例
```
