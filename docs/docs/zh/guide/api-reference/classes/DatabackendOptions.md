# DatabackendOptions

控制 `ChatObject` 执行期间执行哪些后端获取和提交操作的选项。

## 字段

- `skip_memory_fetch` (bool)：跳过从后端加载记忆（默认：`False`）
- `skip_tools_fetch` (bool)：跳过从后端加载工具（默认：`False`）
- `skip_mcp_fetch` (bool)：跳过从后端加载 MCP 客户端（默认：`False`）
- `skip_presets_fetch` (bool)：跳过从后端加载预设（默认：`False`）
- `skip_ability_extra_setting` (bool)：跳过从后端加载额外能力设置（默认：`False`）
- `skip_memory_commit` (bool)：跳过执行后将记忆提交回后端（默认：`False`）

## 使用

```python
from amrita_core.contexts import DatabackendOptions

opts = DatabackendOptions(
    skip_tools_fetch=True,
    skip_mcp_fetch=True,
    skip_presets_fetch=True,
    skip_ability_extra_setting=True,
)

chat = ChatObject(
    train=train,
    user_input="你好",
    session_id="session_123",
    backend_options=opts,
)
```
