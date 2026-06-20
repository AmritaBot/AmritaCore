# AgentRuntime

AgentRuntime 类是 ChatObject 的高级包装器，提供可重用的 agent 操作接口。

该类封装了 ChatObject 的复杂性，并为 agent 交互提供了简化的 API。它维护会话状态、配置和策略设置，使其成为在同一上下文中多次 agent 操作的可重用对象。

## 属性

- `strategy` (type[AgentStrategy]): 用于执行的 agent 策略类
- `session_id` (str): agent 的会话 ID
- `slot` ([BackendSlots](BackendSlots.md)): 提供记忆和能力后端的后端插槽
- `preset` (ModelPreset): 模型预设配置
- `config` (AmritaConfig): Amrita 配置对象
- `train` (Message[str]): 训练数据（系统提示）
- `template` (Template): 用于渲染系统角色消息的 Jinja2 模板

## 构造函数参数

- `config` ([AmritaConfig](AmritaConfig.md)): 包含全局配置设置的 Amrita 配置对象
- `preset` ([ModelPreset](ModelPreset.md)): 定义基本模型参数和设置的模型预设配置
- `train` (dict[str, str] | [Message](Message.md)[str]): agent 的系统提示（字典或 Message 对象）
- `strategy` (type[AgentStrategy], 可选): agent 策略类，默认为 ReActAgentStrategy
- `template` (Template | str, 可选): 用于渲染系统提示的 Jinja2 模板，默认为 DEFAULT_TEMPLATE
- `session_id` (str | None, 可选): 会话标识符字符串。如果为 None，则生成新的基于 UUID 的 ID。session_id 会传递给此运行时创建的每个 ChatObject，允许 Backend 按会话隔离记忆和能力
- `backend` ([BackendSlots](BackendSlots.md) | None, 可选): 提供记忆和能力后端的后端插槽。如果为 None，则两个插槽都使用 `LegacyBackend`，它将数据存储在进程内全局容器中

## 方法

### set_strategy(strategy)

设置要用于执行的 agent 策略。

**参数**:

- `strategy` (type[AgentStrategy]): 要用于执行的 agent 策略

### get_chatobject(input, \*\*kwargs)

获取用于特定交互的聊天对象。

**参数**:

- `input` (USER_INPUT): 用户输入
- `**kwargs`: 传递给 ChatObject 构造函数的其他关键字参数

**返回**: [ChatObject](ChatObject.md) - 配置好的 ChatObject 实例，准备执行

## 使用示例

```python
from amrita_core import create_agent

# 使用工厂函数创建 agent
agent = create_agent(
    "https://api.example.com",
    "your-api-key",
    model="gpt-4",
    model_config={"temperature": 0.7}
)

# 获取用于交互的聊天对象
chat = agent.get_chatobject("你好，What can you do?")

# 执行交互
async with chat.begin():
    response = await chat.full_response()
    print(response)
```
