# StrategyContext

StrategyContext 类为 agent 策略提供执行上下文。

这个数据类包含 agent 策略执行其工作流所需的所有必要信息，包括用户输入、消息上下文和聊天对象引用。

## 属性

- `user_input` (USER_INPUT): 来自用户的输入
- `original_context` (SendMessageWrap): 包含系统消息、记忆和用户查询的原始消息上下文
- `chat_object` (ChatObject): 用于生成响应和管理对话流的聊天对象引用

## 构造函数参数

- `user_input` (USER_INPUT): 来自用户的输入
- `original_context` (SendMessageWrap): 原始消息上下文
- `chat_object` (ChatObject): 聊天对象引用

## 方法

### get_original_context()

获取原始消息上下文。

**返回**: [SendMessageWrap](SendMessageWrap.md) - 原始消息上下文

### get_user_input()

获取用户输入。

**返回**: USER_INPUT - 用户输入

## 使用示例

```python
from amrita_core.agent.context import StrategyContext

# 创建策略上下文
ctx = StrategyContext(
    user_input="What can you do?",
    original_context=message_context,
    chat_object=chat_obj
)

# 访问上下文属性
user_msg = ctx.get_user_input()
message_context = ctx.get_original_context()
```
