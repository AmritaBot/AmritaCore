# MultiToolsManager

The MultiToolsManager class manages multiple tool registrations and lookups.

## Description

MultiToolsManager provides a registry of tools keyed by function name, with support for enabling/disabling tools and conditional activation via `enable_if`. [ToolsManager](ToolsManager.md) is the singleton subclass used by default.

## Methods

- `has_tool(name: str) -> bool`: Whether a tool is registered and not disabled
- `get_tool(name: str, default=None) -> ToolData | None`: Get a tool by name; returns `default` if missing or disabled
- `get_tool_meta(name: str, default=None) -> ToolFunctionSchema | None`: Get a tool's metadata schema
- `get_tool_func(name: str, default=None)`: Get a tool's implementation function
- `get_tools() -> dict[str, ToolData]`: All enabled tools
- `tools_meta() -> dict[str, ToolFunctionSchema]`: Metadata of all enabled tools
- `tools_meta_dict(**kwargs) -> dict[str, dict]`: Metadata dumped to dicts (kwargs forwarded to `model_dump`)
- `register_tool(tool: ToolData) -> None`: Register a tool; raises `ValueError` if the name already exists
- `remove_tool(name: str) -> None`: Unregister a tool
- `enable_tool(name: str) -> None`: Re-enable a disabled tool
- `disable_tool(name: str) -> None`: Disable a tool; raises `ValueError` if it does not exist
- `get_disabled_tools() -> list[str]`: Names of disabled tools

## Example

```python
from amrita_core.tools.manager import MultiToolsManager

manager = MultiToolsManager()
manager.register_tool(my_tool_data)
assert manager.has_tool("my_tool")
func = manager.get_tool_func("my_tool")
```
