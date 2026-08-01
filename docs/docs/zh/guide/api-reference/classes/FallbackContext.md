# FallbackContext

`FallbackContext` 类表示 LLM 请求失败时预设回退事件的上下文。

## 构造函数

```python
FallbackContext(
    preset: ModelPreset,
    exc_info: BaseException,
    config: AmritaConfig,
    context: SendMessageWrap,
    term: int
)
```

## 属性

### preset

- **类型**：[`ModelPreset`](./ModelPreset.md)
- **描述**：失败请求使用的当前模型预设

### exc_info

- **类型**：`BaseException`
- **描述**：导致 LLM 请求失败的异常

### config

- **类型**：[`AmritaConfig`](./AmritaConfig.md)
- **描述**：当前的 Amrita 配置

### context

- **类型**：[`SendMessageWrap`](./SendMessageWrap.md)
- **描述**：失败发生时的消息上下文

### term

- **类型**：`int`
- **描述**：当前重试次数
