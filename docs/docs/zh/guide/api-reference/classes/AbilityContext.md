# AbilityContext

一个数据类，保存 `ChatObject` 运行时会话的能力相关状态。

## 描述

`AbilityContext` 把定义 `ChatObject` 在会话期间能做什么的工具、预设、MCP 客户端
与额外设置打包在一起。

## 字段

- `tools` ([MultiToolsManager](MultiToolsManager.md))：会话中可用工具的管理器，默认为全局 `ToolsManager()` 单例
- `presets` ([MultiPresetManager](MultiPresetManager.md))：会话中模型预设的管理器，默认为全局 `PresetManager()` 单例
- `mcp` ([MultiClientManager](MultiClientManager.md))：MCP 客户端连接的管理器，默认为全局 `ClientManager()` 单例
- `extra` (dict[str, Any])：与能力上下文关联的额外自定义数据

## 默认行为

每个字段都默认为对应的全局管理器单例，所有会话共享。若要使用会话隔离的管理器，把
字段替换为新建的 `MultiToolsManager()`、`MultiPresetManager()` 或
`MultiClientManager()` 实例。

## 使用

```python
from amrita_core.contexts import AbilityContext

ctx = AbilityContext()
# 所有字段都默认为全局单例
print(ctx.tools)  # ToolsManager 单例
print(ctx.presets)  # PresetManager 单例
```
