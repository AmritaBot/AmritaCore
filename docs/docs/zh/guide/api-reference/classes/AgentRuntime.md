# AgentRuntime

AgentRuntime 类是 ChatObject 的高级包装器，提供可复用的 agent 操作接口。通过 `create_agent()` 工厂函数创建。

## 属性

- `strategy` (type[AgentStrategy])：用于执行的 agent 策略类
- `session_id` (str)：agent 的会话 ID
- `slot` ([BackendSlots](BackendSlots.md))：提供记忆和能力后端的后端槽位
- `preset` (ModelPreset)：模型预设配置
- `config` (AmritaConfig)：Amrita 配置对象
- `train` (Message[str])：训练数据（系统提示词）
- `template` (Template)：用于渲染系统角色消息的 Jinja2 模板

## 构造函数参数

- `config` ([AmritaConfig](AmritaConfig.md))：Amrita 配置对象
- `preset` ([ModelPreset](ModelPreset.md))：模型预设配置
- `train` (dict[str, str] | [Message](Message.md)[str])：系统提示词
- `strategy` (type[AgentStrategy], optional)：agent 策略类，默认为 ReActAgentStrategy
- `template` (Template | str, optional)：Jinja2 模板，默认为 DEFAULT_TEMPLATE
- `session_id` (str | None, optional)：会话标识符
- `backend` ([BackendSlots](BackendSlots.md) | None, optional)：后端槽位

## 方法

### set_strategy(strategy)

设置要用于执行的 agent 策略。

### get_chatobject(input, \*\*kwargs)

获取特定交互的聊天对象。

**返回**：[ChatObject](ChatObject.md) - 配置好的 ChatObject 实例

## 使用示例

```python
from amrita_core import create_agent

agent = create_agent(
    "https://api.example.com",
    "your-api-key",
    model="gpt-4",
    model_config={"temperature": 0.7}
)

chat = agent.get_chatobject("你好，你能做什么？")

async with chat.begin():
    response = await chat.full_response()
    await chat
    print(response)
```
