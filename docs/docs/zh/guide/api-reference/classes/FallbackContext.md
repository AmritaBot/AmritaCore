# FallbackContext

`FallbackContext` 类是所有预设回退事件的**基类**，由 `libchat` 网关层（`call_completion`、`tools_caller`、`call_embedding`）在请求失败时触发。它携带切换到备用预设所需的信息。

所有回退事件共享 `PRESET_FALLBACK` 事件类型；具体子类用于区分失败的网关调用，使 matcher 可以对不同类型的回退做出不同响应。

## 类层次

```text
FallbackContext（基类）
├── CompletionFallbackContext  # call_completion 失败
├── ToolsFallbackContext       # tools_caller 失败
└── EmbeddingFallbackContext   # call_embedding 失败
```

## 构造函数

```python
FallbackContext(
    preset: ModelPreset,
    exc_info: BaseException,
    config: AmritaConfig,
    context: SendMessageWrap | CONTENT_LIST_TYPE | Sequence[str],
    term: int
)
```

## 属性

### preset

- **类型**：[`ModelPreset`](./ModelPreset.md)
- **描述**：失败请求使用的当前模型预设

### exc_info

- **类型**：`BaseException`
- **描述**：导致请求失败的异常

### config

- **类型**：[`AmritaConfig`](./AmritaConfig.md)
- **描述**：当前的 Amrita 配置

### context

- **类型**：`SendMessageWrap | CONTENT_LIST_TYPE | Sequence[str]`
- **描述**：失败调用的载荷。具体类型取决于子类：
  - `CompletionFallbackContext`：校验后的消息列表（`CONTENT_LIST_TYPE`）
  - `ToolsFallbackContext`：校验后的消息列表（`CONTENT_LIST_TYPE`）
  - `EmbeddingFallbackContext`：输入文本序列（`Sequence[str]`）

### term

- **类型**：`int`
- **描述**：当前回退尝试次数（从 1 开始）

## 子类

### CompletionFallbackContext

当 `call_completion` 失败时触发。`context` 携带校验后的消息列表（`CONTENT_LIST_TYPE`）。

### ToolsFallbackContext

当 `tools_caller` 失败时触发。除 `context` 外，还暴露：

- `tools`（`list[ToolFunctionSchema] | None`）：失败调用的工具 schema。

### EmbeddingFallbackContext

当 `call_embedding` 失败时触发。`context` 携带输入文本序列（`Sequence[str]`）。

## 方法

### fail(reason: Any | None = None) -> Never

标记事件失败并终止重试流程。

**参数**：

- `reason`（Any | None）：可选的失败原因。

**抛出**：

- [`FallbackFailed`](../exceptions/FallbackFailed.md)：总是抛出此异常以终止回退流程。

### get_event_type() -> EventTypeEnum

获取事件类型枚举值。

**返回**：

- `EventTypeEnum.PRESET_FALLBACK`

## 使用示例

```python
from amrita_core.hook.event import CompletionFallbackContext, FallbackContext
from amrita_core.hook.on import on_preset_fallback


@on_preset_fallback().handle()
async def handle_fallback(event: FallbackContext):
    print(f"Request failed: {event.exc_info}")
    if event.term == 1:
        # 首次重试时切换到备用预设
        event.preset = get_alternative_preset()
    else:
        # 后续重试直接失败
        event.fail("No more fallback options")


@on_preset_fallback().handle()
async def handle_tools_fallback(event: ToolsFallbackContext):
    # 区分不同类型的回退
    print(f"Tool call failed: {event.tools}")
    event.preset = get_fallback_preset()
```
