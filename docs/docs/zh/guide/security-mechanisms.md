# 安全机制

## Cookie 安全检测

AmritaCore 可检测模型响应中的敏感 cookie 值并终止会话防止数据泄露：

- **启用**：`config.cookie.enable_cookie = True`（默认值）
- **检测**：模型**答案**与**推理内容**都会被扫描配置的 cookie 值。推理是模型输出
  的一部分，且会以 `reasoning_chunk` 事件送达消费者，因此只扫描答案会让「在思考里
  引用 cookie」的模型通过检查
- **响应**：命中后本次运行以通用错误消息终止，同时替换事件的响应与推理内容，使该值
  不会留在响应对象或对话历史中

守卫针对的是**system prompt 泄露**：金丝雀位于 system prompt 内部，因此任何复现它的
运行都意味着 system 内容已进入模型输出——无论是提示注入导致的，还是模型自己引用了
标记。对推理一并触发是刻意的：推理与答案一样会流式送达消费者。

> 已经交给流式消费者的 chunk 无法收回。追加到流中的错误载荷是本次运行失败的标记，
> 因此会渲染 `reasoning_chunk` 事件的消费者应在收到 `error` 事件时停止。

```python
from amrita_core.config import AmritaConfig

config = AmritaConfig()
config.cookie.enable_cookie = True
# 配置要保护的 cookie 值
```

## 提示注入考量

工具结果与 peer 消息以文本进入模型上下文。把它们当作不可信输入：

- **内置策略**把工具结果存为配对的 `ToolResult` 消息，而不是以纯文本内联，
  从而让不可信输出不进入承载指令的文本流。
- **Peer 消息**（`send_to_producer`）以 `[peer message]` 标记追加——设计
  system prompt 时把该标记当作数据而非指令。
- **自定义工具**：结果来自外部源时，返回前先校验工具输出。

## 上下文中的敏感数据

- 策略持有 `chat_object` 作为生命周期句柄——不要记录它
- `MemoryModel` 承载完整对话与计费记录——序列化时视为敏感

## 模板安全

Jinja2 模板变量不得与内置名冲突（`train`、`memory`、`chatobj`、`config`）
——冲突抛 `TypeError`（见 [Jinja2 模板](agent-engineering/jinja2-templates.md)）。

## 会话隔离

记忆按 `session_id` 键控；不同 id 完全隔离。多租户部署使用唯一、不可猜测的
会话 id。
