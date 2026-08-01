# 数据容器

AmritaCore 提供了一组类型化的数据容器，构成对话状态、消息传递和上下文管理的基石。这些容器定义在 `amrita_core.types` 包中，并与[数据后端](data-backend.md)集成以实现持久化。

## Message 类型

[`Message`](../api-reference/classes/Message.md) 类表示对话中的单条消息。它是一个按内容类型参数化的泛型 Pydantic 模型：

```python
from amrita_core.types import Message

# 创建系统消息
system_msg = Message(content="你是一个乐于助人的助手。", role="system")

# 创建用户消息
user_msg = Message(content="你好，最近怎么样？", role="user")

# 创建带多模态内容的助理消息
from amrita_core.types import TextContent, ImageContent
multi_msg = Message(role="user", content=[
    TextContent(text="这张图片里有什么？"),
    ImageContent(image_url=...)
])
```

**关键字段**：

- `role`：`"user"`、`"assistant"` 或 `"system"`
- `content`：字符串、`Content` 子类列表或 `None`
- `tool_calls`：可选的 [`ToolCall`](../api-reference/classes/ToolCall.md) 列表
- `reasoning_content` / `reasoning_signature`：推理/思考元数据（仅 assistant）

`Message` 使用 `model_config = ConfigDict(extra="allow")`，因此额外字段可以透明传递。

## Content 类型

AmritaCore 支持三种内置内容类型，注册在 `CT_MAP` 注册表中：

### TextContent

```python
from amrita_core.types import TextContent

content = TextContent(text="这是实际的消息文本")
```

### ImageContent

```python
from amrita_core.types import ImageContent, ImageUrl

content = ImageContent(image_url=ImageUrl(
    url="https://example.com/image.png",
    detail="auto"
))
```

### FileContent

```python
from amrita_core.types import FileContent, File

content = FileContent(file=File(
    file_id="file-abc123",
    # 或内联：filename="doc.pdf", file_data="...", type="application/pdf"
))
```

新的内容类型可以通过 `register_content()` 注册——参见[数据杂项](data-misc.md)。

## MemoryModel——对话记忆

[`MemoryModel`](../api-reference/classes/MemoryModel.md) 存储对话历史和上下文。它继承自 `DirtyAwareBaseModel`，该模型跟踪字段修改（**脏标记**模式）：

```python
from amrita_core.types import MemoryModel

memory = MemoryModel()

# 向记忆中追加消息
memory.messages.append(system_msg)
memory.messages.append(user_msg)
memory.messages.append(assistant_msg)

# 检查变更
print(memory.is_dirty("messages"))  # True
print(memory.get_dirty_vars())       # {"messages"}
memory.clean()                       # 重置脏跟踪
```

**关键字段**：

- `messages`：`list[Message | ToolResult]`——对话历史
- `abstract`：`str`——自动生成的摘要（由 `MemoryLimiter` 填充）
- `time`：`float`——时间戳

**脏标记**模式由 `DirtyAwareBaseModel` / `DirtyAwareModel` 提供。子容器（`DirtyList`、`DirtyDict`、`DirtySet`）自动将变更向上传播到父模型，实现类似 ORM 的变更跟踪。

## ToolResult

[`ToolResult`](../api-reference/classes/ToolResult.md) 表示工具调用的输出：

```python
from amrita_core.types import ToolResult

result = ToolResult(
    role="tool",
    name="calculator",
    content="42",
    tool_call_id="call_abc123"
)
```

`ToolResult` 可以与 `Message` 对象一起出现在 `memory.messages` 中——两者都是有效的 `CONTENT_LIST_TYPE_ITEM`。

```python
CONTENT_LIST_TYPE_ITEM = Message | ToolResult
CONTENT_LIST_TYPE = list[CONTENT_LIST_TYPE_ITEM]
```

## StateContext——运行时状态（自 v0.12.0 起已废弃）

> **在 v0.12.0 中标记为 `@deprecated`**，将在 v0.13.x 中移除。该数据类承载了过多职责，已拆分为独立的 DI 上下文对象。

[`StateContext`](../api-reference/classes/StateContext.md) 是传递给每个 `ChatObject` 的运行时状态容器。它是一个 **dataclass**（非 Pydantic 模型）：

```python
from amrita_core.contexts import StateContext, AbilityContext

state = StateContext(
    session_id="session_abc",
    memory=MemoryModel(),
    ability=AbilityContext()
)
```

### 替代方案：DI 上下文对象

自 v0.12.0 起，ChatObject 内部使用以下 DI 上下文对象来替代 `StateContext` 的职责：

| DI 上下文                                                                          | 用途                        |
| ---------------------------------------------------------------------------------- | --------------------------- |
| `_di_session` (`SessionMetadata`)                                                  | 会话身份和时间              |
| `_di_memory` (`MemoryContext`)                                                     | 运行时对话记忆              |
| `_di_ability` (`AbilityState`)                                                     | 配置、预设、后端槽位        |
| `_di_input` (`GeneralInput`)                                                       | 用户输入、模板、Jinja2 变量 |
| `_di_working` (`WorkingState`)                                                     | 上下文消息包装器            |
| `_di_resp` (`RespState`)                                                           | LLM 响应和使用统计          |
| `_di_loop` (`AgentLoopState`)                                                      | Agent 循环状态              |
| `_di_opt` ([`DatabackendOptions`](../api-reference/classes/DatabackendOptions.md)) | 后端获取/提交控制           |
| `_di_agent` (`StrategyPayload`)                                                    | Agent 策略引用              |

这些 DI 对象由 `WorkflowInterpreter` 的依赖注入自动注入到工作流节点中，无需手动传递。

## AbilityContext

[`AbilityContext`](../api-reference/classes/AbilityContext.md) 将会话可用的"能力"分组：

```python
from amrita_core.contexts import AbilityContext

ability = AbilityContext(
    tools=ToolsManager(),       # 默认为全局 ToolsManager 单例
    presets=PresetManager(),    # 默认为全局 PresetManager 单例
    mcp=ClientManager(),        # 默认为全局 ClientManager 单例
    extra={}
)
```

当不提供参数时，所有字段默认为**全局单例**管理器 — 这是 `LegacyBackend` 的行为。

## 管理器模式 — Multi\* vs 单例管理器

AmritaCore 对管理器类使用两层模式：具有实例级状态的 **`Multi*Manager`** 基类，以及提供全局共享实例的**单例子类**。单例是 `AbilityContext` 和 `LegacyBackend` 使用的默认值。

### ToolsManager / MultiToolsManager

[`MultiToolsManager`](../api-reference/classes/MultiToolsManager.md) 是一个工具注册表，存储按函数名索引的 [`ToolData`](../api-reference/classes/ToolData.md) 条目。每个 `ToolData` 将 schema（`ToolFunctionSchema`）与异步可调用对象和可选的 `enable_if()` 谓词捆绑在一起。

```python
from amrita_core.tools.manager import ToolsManager, MultiToolsManager

# 全局单例（默认使用）
tm = ToolsManager()

# 或创建隔离实例
tm = MultiToolsManager()
```

**关键方法**：

| 方法                                       | 描述                                        |
| ------------------------------------------ | ------------------------------------------- |
| `has_tool(name)`                           | 检查工具是否已注册且启用                    |
| `get_tool(name)`                           | 获取完整的 `ToolData`（遵循 `enable_if()`） |
| `get_tool_meta(name)`                      | 仅获取 `ToolFunctionSchema`                 |
| `get_tool_func(name)`                      | 获取原始异步可调用对象                      |
| `get_tools()`                              | 获取所有已启用工具 `dict[str, ToolData]`    |
| `tools_meta()` / `tools_meta_dict()`       | 获取所有工具 schema 用于 LLM 请求           |
| `register_tool(tool)`                      | 注册 `ToolData`                             |
| `remove_tool(name)`                        | 移除并取消工具                              |
| `enable_tool(name)` / `disable_tool(name)` | 运行时启用/禁用切换                         |

[`ToolsManager`](../api-reference/classes/ToolsManager.md) 是 `MultiToolsManager` 的**单例**子类 — 所有使用 `LegacyBackend` 的会话共享同一个全局工具注册表。通过 `@simple_tool` / `@on_tools` 注册的工具进入此全局实例。

### PresetManager / MultiPresetManager

[`MultiPresetManager`](../api-reference/classes/MultiPresetManager.md) 管理一组 [`ModelPreset`](data-misc.md#modelpreset-model-preset) 实例：

```python
from amrita_core.preset import PresetManager, MultiPresetManager

# 全局单例
pm = PresetManager()

# 或隔离实例
pm = MultiPresetManager()
```

**关键方法**：

| 方法                       | 描述                                               |
| -------------------------- | -------------------------------------------------- |
| `add_preset(preset)`       | 注册 `ModelPreset`（重名引发异常）                 |
| `get_preset(name)`         | 按名称查找（缺失引发 `ValueError`）                |
| `set_default_preset(name)` | 设置回退预设                                       |
| `get_default_preset()`     | 返回默认预设，或随机已注册的预设（若未设置默认值） |
| `get_all_presets()`        | 返回 `list[ModelPreset]`                           |
| `test_presets()`           | 异步生成器，为每个预设产出 `PresetReport`          |

[`PresetManager`](../api-reference/classes/PresetManager.md) 是**单例**子类 — 默认所有会话共享同一个预设目录。

### ClientManager / MultiClientManager（MCP）

[`MultiClientManager`](../api-reference/classes/MultiClientManager.md) 管理 [`MCPClient`](../api-reference/classes/MCPClient.md) 实例池，将外部 MCP 服务器桥接到工具系统中：

```python
from amrita_core.tools.mcp import ClientManager, MultiClientManager

# 全局单例
cm = ClientManager()

# 或隔离实例
cm = MultiClientManager()
```

**关键方法**：

| 方法                            | 描述                               |
| ------------------------------- | ---------------------------------- |
| `initialize_this(script)`       | 注册并连接单个 MCP 服务器          |
| `initialize_all()`              | 连接所有已注册的客户端             |
| `reinitialize_all()`            | 重新连接所有客户端（如配置更改后） |
| `unregister_client(script)`     | 断开连接并移除服务器               |
| `get_client_by_tool_name(name)` | 解析哪个 `MCPClient` 拥有给定工具  |
| `get_client_by_script(script)`  | 创建（但不注册）独立的 `MCPClient` |

当 MCP 服务器加载时，其工具自动注册到绑定的 `tools_manager` 中。名称冲突触发自动重映射。参见 [MCP 服务器集成](../extensions-integration/mcp-server-integration.md) 的端到端示例。

[`ClientManager`](../api-reference/classes/ClientManager.md) 是**单例**子类。每个 `MCPClient` 包装一个 MCP 服务器脚本并处理连接生命周期（连接、基于 TTL 的自动关闭、工具发现）。

### 总结表

| 管理器                                 | 管理内容           | 单例            | LegacyBackend 中的默认值 |
| -------------------------------------- | ------------------ | --------------- | ------------------------ |
| `MultiToolsManager` / `ToolsManager`   | `ToolData` 条目    | `ToolsManager`  | `AbilityContext.tools`   |
| `MultiPresetManager` / `PresetManager` | `ModelPreset` 条目 | `PresetManager` | `AbilityContext.presets` |
| `MultiClientManager` / `ClientManager` | `MCPClient` 池     | `ClientManager` | `AbilityContext.mcp`     |
