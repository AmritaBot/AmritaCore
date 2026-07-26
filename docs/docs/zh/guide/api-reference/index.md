# API 参考

## 7.1 核心 API 函数

### 7.1.1 init() - 初始化（已废弃）

> **已废弃**：`init()` 函数从 v0.9.0rc1 起已废弃。现在是空操作存根，不再执行任何初始化。请改用 `load_amrita()` 进行异步初始化。

```python
from amrita_core import init

# 不再必要 — 现在是一个空操作
init()
```

**迁移**: 删除代码中所有 `init()` 调用。需要异步初始化时（例如 MCP 客户端设置）使用 `load_amrita()`。

### 7.1.2 load_amrita() - 加载框架

`load_amrita()` 函数异步加载 AmritaCore 组件，特别是启用了 MCP 客户端功能时。

```python
import asyncio
from amrita_core import load_amrita

async def main():
    await load_amrita()

asyncio.run(main())
```

**用途**: 加载额外的 AmritaCore 组件，特别是如果配置了 MCP 客户端。

**使用注意事项**:

- 必须在 `set_config()` 之后调用
- 应该被等待，因为它是一个异步函数

### 7.1.3 set_config() - 设置配置

`set_config()` 函数将配置应用到 AmritaCore。

```python
from amrita_core.config import AmritaConfig, set_config

config = AmritaConfig()
set_config(config)
```

**用途**: 设置 AmritaCore 的活动配置。

**参数**:

- `config` ([AmritaConfig](classes/AmritaConfig.md)): 要设置的配置对象

**使用注意事项**:

- 应该在 `load_amrita()` 之前调用
- 配置会影响所有后续操作

### 7.1.4 get_config() - 获取配置

`get_config()` 函数检索当前 AmritaCore 配置。

```python
from amrita_core.config import get_config

config = get_config()
print(config.function_config.use_minimal_context)
```

**返回**: [AmritaConfig](classes/AmritaConfig.md) - 当前配置对象

**使用注意事项**:

- 如果尚未调用 `set_config()` 则抛出 RuntimeError
- 初始化后调用是安全的

### 7.1.5 create_agent() - Agent 创建

`create_agent()` 函数通过自动创建临时预设，使用最少参数创建一个 agent。

```python
from amrita_core import create_agent

agent = create_agent(
    "https://api.example.com",
    "your-api-key",
    model="gpt-4",
    model_config={"temperature": 0.7}
)
```

**用途**: 通过仅需要 URL 和 API 密钥等基本参数来简化 agent 创建，自动创建临时预设以供立即使用。

**参数**:

- `url` (str): API 端点 URL
- `key` (str): 用于身份验证的 API 密钥
- `model` (str, 可选): 要使用的模型。默认为 `"auto"`。
- `model_config` ([ModelConfig](classes/ModelConfig.md) | dict | None, 可选): 可选的模型配置。默认为 None。
- `config` ([AmritaConfig](classes/AmritaConfig.md) | None, 可选): agent 的配置。默认为全局配置。
- `**kwargs`: 转发给 [AgentRuntime](classes/AgentRuntime.md) 的其他关键字参数（例如 `strategy`、`template`、`session_id`、`backend`）

**返回**: `AgentRuntime` - 配置好的 agent 运行时实例

**使用注意事项**:

- 这是快速创建 agent 进行基本用例的推荐方式
- 该函数自动处理初始化、配置和预设创建
- 对于需要细颗粒度控制的高级用例，请考虑直接使用 [ChatObject](classes/ChatObject.md)
- 创建的 agent 可以通过 `get_chatobject()` 方法重复用于多次交互

## 7.2 类和接口文档

### 7.2.1 ChatObject - 对话对象

[ChatObject](classes/ChatObject.md) 类是与 AI 对话的主要接口。

```python
from amrita_core import ChatObject
from amrita_core.types import Message

train = Message(content="You are a helpful assistant.", role="system")

chat = ChatObject(
    train=train.model_dump(),
    user_input="你好！",
    session_id="session_123",
)
```

**构造函数参数**:

- `train` (dict | [Message](classes/Message.md)): AI 的训练/提示数据
- `user_input` (str | Sequence[Content] | None): 用户的输入消息
- `context` ([StateContext](classes/StateContext.md) | None, 可选): 预构建的状态上下文（与 `session_id` 互斥）
- `session_id` (str | None, 可选): 会话的唯一标识符（与 `context` 互斥）
- `backend` ([BackendSlots](classes/BackendSlots.md) | None, 可选): 用于记忆和能力 I/O 的后端插槽（默认：LegacyBackend）
- `preset` ([ModelPreset](classes/ModelPreset.md) | None, 可选): 模型预设（运行时解析）

**方法**:

- `begin()`: 执行对话
- `full_response()`: 返回完整响应

**特殊方法**:

- `__await__`: 允许对象用作异步上下文管理器，我们建议使用它。

### 7.2.1b BackendSlots - 后端机制

[BackendSlots](classes/BackendSlots.md) 数据类将 [AbilityBackend](classes/AbilityBackend.md) 和 [MemoryBackend](classes/MemoryBackend.md) 捆绑用于数据 I/O。

```python
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend

slot = BackendSlots(
    ability=LegacyBackend(),
    memory=LegacyBackend(),
)
```

- [AbilityBackend](classes/AbilityBackend.md): 用于加载工具、MCP 客户端和预设的抽象基类
- [MemoryBackend](classes/MemoryBackend.md): 用于加载和提交记忆的抽象基类
- [LegacyBackend](classes/LegacyBackend.md): 默认的进程内实现
- [AbilityContext](classes/AbilityContext.md): 运行时能力状态（工具、预设、MCP 客户端）
- [StateContext](classes/StateContext.md): 运行时会话状态（session_id、memory、ability）
- [DatabackendOptions](classes/DatabackendOptions.md): 对后端获取/提交操作的细粒度控制
- [DirtyAwareBaseModel](classes/DirtyAwareBaseModel.md): 具有自动变更追踪的基础模型

### 7.2.2 Message - 消息类

[Message](classes/Message.md) 类表示对话中的单条消息。

```python
from amrita_core.types import Message

# 创建不同类型的消息
system_msg = Message(content="您是一个有用的助手。", role="system")
user_msg = Message(content="您好，您好吗？", role="user")
assistant_msg = Message(content="我很好，谢谢！", role="assistant")
```

**构造函数参数**:

- `content` (str): 消息内容
- `role` (str): 消息的角色（'system'、'user' 或 'assistant'）

### 7.2.3 MemoryModel - 记忆模型

[MemoryModel](classes/MemoryModel.md) 类存储对话历史和上下文。

```python
from amrita_core.types import MemoryModel, Message

memory = MemoryModel()
memory.messages.append(Message(content="你好", role="user"))
memory.messages.append(Message(content="你好", role="assistant"))
```

**属性**:

- `messages` (list): 对话中的消息列表

### 7.2.4 AmritaConfig - 配置类

[AmritaConfig](classes/AmritaConfig.md) 类是 AmritaCore 的中央配置对象。

```python
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig, CookieConfig

config = AmritaConfig(
    function_config=FunctionConfig(
        use_minimal_context=False,
        tool_calling_mode="agent"
    ),
    llm=LLMConfig(
        enable_memory_abstract=True
    ),
    cookie=CookieConfig(
        enable_cookie=True
    )
)
```

**属性**:

- `function_config` ([FunctionConfig](classes/FunctionConfig.md)): 功能行为配置
- `llm` ([LLMConfig](classes/LLMConfig.md)): 语言模型配置
- `cookie` ([CookieConfig](classes/CookieConfig.md)): 安全配置

## 7.3 装饰器参考

### 7.3.1 @simple_tool - 简单工具装饰器

`@simple_tool` 装饰器用于注册简单工具。

```python
from amrita_core import simple_tool


@simple_tool
def add(a: int, b: int) -> int:
    """添加数字

    Args:
        a (int): 第一个数字
        b (int): 第二个数字
    """
    return a + b
```

**用途**: 通过从类型注解和文档字符串自动推断模式来注册简单工具。

**支持的参数类型**:

- 基本类型: `str`, `int`, `float`, `bool`
- Literal 类型: `Literal["a", "b"]` → 自动生成 `string` + `enum` 约束；`Literal[1, 2, 3]` 同理支持 `integer` 枚举
- Pydantic BaseModel 类，用于复杂的嵌套结构
- 容器类型: `List[T]`（仅支持单层）
- 可选类型: `Optional[T]` 或 `T | None`

**不支持的类型**（会抛出 ValueError）:

- Dict 类型（请改用 Pydantic 模型）
- 嵌套容器（例如 `List[List[str]]`）
- 多类型联合（例如 `str | int`）
- `Any` 或 `object` 类型

**注册行为**:

- 工具在模块加载期间注册到**全局容器**
- 由于注册发生在会话创建之前，因此对所有会话都可用
- 对于会话特定的工具管理，请改用直接的 `MultiToolsManager` 操作

**使用注意事项**:

- 装饰器注册一个简单工具。
- 工具使用函数的名称进行注册。
- 每个参数的描述来自函数的文档字符串，它遵循文档字符串的相同格式。
- 所有函数参数都必须有类型注解（不允许无类型参数）。

### 7.3.2 @on_tools - 工具注册

`@on_tools` 装饰器将函数注册为Agent可调用的工具。

```python
from typing import Any

from amrita_core import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

DEFINITION = FunctionDefinitionSchema(
    name="添加数字",
    description="添加两个数字",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "a": FunctionPropertySchema(type="number",description="第一个数字"),
            "b": FunctionPropertySchema(type="number",description="第二个数字"),
        },
        required=["a", "b"],
    ),
)

@on_tools(DEFINITION)
async def add(data: dict[str, Any]) -> str:
    """添加两个数字"""
    return str(data["a"] + data["b"])

```

**用途**: 将函数注册为Agent可以调用的可用工具，并对工具模式进行细粒度控制。

**注册行为**:

- 与 `@simple_tool` 类似，在模块加载期间注册到**全局容器**
- 提供对工具模式定义的显式控制
- 适用于 `@simple_tool` 不支持的复杂验证需求

**使用注意事项**:

- 函数必须为参数提供适当的类型提示
- 函数文档字符串成为工具描述
- 注册的工具会自动对Agent可用

### 7.3.3 @on_event - 事件监听器

`@on_event` 装饰器将函数注册为事件处理器。

```python
from amrita_core.hook.on import on_event

@on_event()
def my_event_handler(event):
    # 处理自定义事件
    pass
```

**用途**: 注册一个函数来处理处理流水线期间的特定事件。

### 7.3.4 @on_precompletion - 预完成钩子

`@on_precompletion` 装饰器注册在完成请求发送到 LLM 之前的运行函数。

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion().handle()
async def preprocess_request(event: PreCompletionEvent):
    # 在发送到 LLM 之前修改消息
    print(event)
```

**用途**: 在发送请求到 LLM 之前运行，允许修改消息或其他预处理。

### 7.3.5 @on_completion - 后完成钩子

`@on_completion` 装饰器注册在从 LLM 接收完成响应后运行的函数。

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion().handle()
async def postprocess_response(event: CompletionEvent):
    # 在从 LLM 接收后处理响应
    print(event)
```

**用途**: 在从 LLM 接收响应后运行，允许对响应进行后处理。

## 7.4 类型定义和异常

### 7.4.1 预定义类型

AmritaCore 提供了多种预定义类型以确保一致性：

- [BaseModel](classes/BaseModel.md): 所有数据模型的基类
- [Depends](classes/Depends.md): 用于声明事件处理器依赖项的依赖注入装饰器
- [DependsFactory](classes/DependsFactory.md): 用于包装和解析依赖函数的依赖工厂类
- [EmbeddingChunk](classes/EmbeddingChunk.md): 表示嵌入适配器返回的嵌入向量
- [Function](classes/Function.md): 表示工具系统中的可调用函数
- [FunctionDefinitionSchema](classes/FunctionDefinitionSchema.md): 函数参数的模式
- [MemoryModel](classes/MemoryModel.md): 存储对话历史
- [ModelConfig](classes/ModelConfig.md): 模型特定配置
- [ModelPreset](classes/ModelPreset.md): 特定模型的完整配置
- [SuspendEnum](classes/SuspendEnum.md): 用于挂起/恢复机制的标准化断点标签
- [SuspendObjectStream](classes/SuspendObjectStream.md): 具有挂起/恢复功能和流式响应处理的泛型基类
- [TextContent](classes/TextContent.md): 表示消息中的文本内容
- [ToolCall](classes/ToolCall.md): 表示工具的调用
- [ToolContext](classes/ToolContext.md): 为工具执行提供上下文
- [ToolResult](classes/ToolResult.md): 表示工具调用的结果
- [ToolsManager](classes/ToolsManager.md): 管理已注册的工具
- [UniResponse](classes/UniResponse.md): 响应的统一格式
- [UniResponseUsage](classes/UniResponseUsage.md): 响应的使用统计

### 7.4.2 异常类型

AmritaCore 可能引发以下异常:

- `RuntimeError`: 当在初始化之前访问配置时引发
- `ValueError`: 当为函数提供无效值时引发
- `TypeError`: 当向函数传递错误类型时引发

### 7.4.3 类型检查

AmritaCore 广泛使用 Pydantic 模型进行类型验证。创建自定义组件时，请确保适当的类型注解:

```python
from typing import Optional
from amrita_core.types import BaseModel

class CustomConfig(BaseModel):
    param1: str
    param2: Optional[int] = None
    param3: list[str] = []
```

此 API 参考提供了核心 AmritaCore 接口、类和装饰器的全面概述。每个组件都设计为协同工作，以提供一个灵活且强大的 AI Agent构建框架。
