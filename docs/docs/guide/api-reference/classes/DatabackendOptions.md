# DatabackendOptions

Options that control which backend fetch and commit operations are performed during `ChatObject` execution.

## Description

`DatabackendOptions` provides fine-grained control over the framework-managed fetch strategy. By setting flags to `True`, you can skip specific backend operations, which is useful for performance optimization or when certain data is already available.

## Fields

- `skip_memory_fetch` (bool): Skip loading memory from the backend (default: `False`)
- `skip_tools_fetch` (bool): Skip loading tools from the backend (default: `False`)
- `skip_mcp_fetch` (bool): Skip loading MCP clients from the backend (default: `False`)
- `skip_presets_fetch` (bool): Skip loading presets from the backend (default: `False`)
- `skip_ability_extra_setting` (bool): Skip loading extra ability settings from the backend (default: `False`)
- `skip_memory_commit` (bool): Skip committing memory back to the backend after execution (default: `False`)

## Usage

> **v0.12.0 migration**: `DatabackendOptions` has been moved from `amrita_core.chatmanager.chat_object` to `amrita_core.contexts`. The old import path still works via backward-compatible re-exports, but updating to the new path is recommended.

```python
from amrita_core.contexts import DatabackendOptions

# Only load memory, skip everything else
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
