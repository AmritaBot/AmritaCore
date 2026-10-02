# Message

Message 类表示对话中的单条消息。

## 属性

- `role` (Literal["user", "assistant", "system"])：消息的角色
- `content` (T)：消息的内容，T 是泛型参数
- `tool_calls` (list[`ToolCall`] | None)：工具调用列表，可选
- `reasoning_content` (str | None)：来自模型的推理/思考内容
- `reasoning_signature` (str | None)：Anthropic 思考签名

## 示例

```python
from amrita_core.types import Message

# 创建不同类型的消息
system_msg = Message(content="你是一个乐于助人的助手。", role="system")
user_msg = Message(content="你好，最近怎么样？", role="user")
assistant_msg = Message(content="我很好，谢谢！", role="assistant")
```

## 描述

Message 类继承自 BaseModel，并使用泛型来表示对话中的消息。它包含 role、content 以及可选的工具调用信息。
