# MultiToolsManager

MultiToolsManager 类管理多个工具的注册和查找。

## 描述

MultiToolsManager 提供按函数名索引的工具注册表，支持启用/禁用工具以及通过 `enable_if` 进行条件激活。[ToolsManager](ToolsManager.md) 是默认使用的单例子类。

## 方法

- `has_tool(name: str) -> bool`：工具是否已注册且未被禁用
- `get_tool(name: str, default=None) -> ToolData | None`：按名称获取工具
- `get_tool_meta(name: str, default=None) -> ToolFunctionSchema | None`：获取工具的元数据模式
- `get_tool_func(name: str, default=None)`：获取工具的实现函数
- `get_tools() -> dict[str, ToolData]`：所有已启用的工具
- `tools_meta() -> dict[str, ToolFunctionSchema]`：所有已启用工具的元数据
- `tools_meta_dict(**kwargs) -> dict[str, dict]`：元数据转储为字典
- `register_tool(tool: ToolData) -> None`：注册工具
- `remove_tool(name: str) -> None`：取消注册工具
- `enable_tool(name: str) -> None`：重新启用已禁用的工具
- `disable_tool(name: str) -> None`：禁用工具
- `get_disabled_tools() -> list[str]`：已禁用工具的名称列表

## 示例

```python
from amrita_core.tools.manager import MultiToolsManager

manager = MultiToolsManager()
manager.register_tool(my_tool_data)
assert manager.has_tool("my_tool")
func = manager.get_tool_func("my_tool")
```
