# AbilityContext

一个数据类，保存 `ChatObject` 运行时会话的能力相关状态。

## 字段

- `tools` ([MultiToolsManager](MultiToolsManager.md))：会话中可用工具的管理器，默认为全局 `ToolsManager()` 单例
- `presets` ([MultiPresetManager](MultiPresetManager.md))：会话中模型预设的管理器，默认为全局 `PresetManager()` 单例
- `mcp` ([MultiClientManager](MultiClientManager.md))：MCP 客户端连接的管理器，默认为全局 `ClientManager()` 单例
- `extra` (dict[str, Any])：与能力上下文关联的额外自定义数据

## 使用

```python
from amrita_core.contexts import AbilityContext

ctx = AbilityContext()
print(ctx.tools)    # ToolsManager 单例
print(ctx.presets)  # PresetManager 单例
```
