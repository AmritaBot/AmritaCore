# API 参考

## 7.1 核心 API 函数

### 7.1.1 init() - 初始化

`init()` 函数初始化 AmritaCore 的核心组件，必须在任何其他操作之前调用。

```python
from amrita_core import init

# 初始化 AmritaCore
init()
```

**用途**: 准备 AmritaCore 的内部组件，初始化 Jieba 用于文本处理，加载内置模块并设置核心框架。

**使用注意事项**:

- 必须在任何其他 AmritaCore 函数之前调用
- 线程安全，可以多次调用（后续调用是无操作）
- 设置日志记录和内部状态

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

- 必须在 `init()`) 和 `set_config()` 之后调用
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

- 必须在 `init()` 之后但在 `load_amrita()` 之前调用
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

- 如果 AmritaCore 未初始化则抛出 RuntimeError
- 在初始化后调用是安全的

## 7.2 类和接口文档

### 7.2.1 ChatObject - 对话对象

[ChatObject](classes/ChatObject.md) 类是与 AI 对话的主要接口。

```python
from amrita_core import ChatObject
from amrita_core.types import MemoryModel, Message

context = MemoryModel()
train = Message(content="您是一个有用的助手。", role="system")

chat = ChatObject(
    context=context,
    session_id="session_123",
    user_input="你好！",
    train=train.model_dump()
)
```

**构造函数参数**:

- `context` ([MemoryModel](classes/MemoryModel.md)): 对话的内存上下文
- `session_id` (str): 会话的唯一标识符
- `user_input` (str): 用户的输入消息
- `train` (dict): AI 的训练/提示数据

**方法**:

- `begin()`: 执行对话
- `get_response_generator()`: 返回用于流式响应的异步生成器
- `full_response()`: 返回完整响应

**特殊方法**:

- `__await__`: 允许对象用作异步上下文管理器，我们建议使用它。

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

### 7.2.3 MemoryModel - 内存模型

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

    参数:
        a (int): 第一个数字
        b (int): 第二个数字
    """
    return a + b
```

**用途**: 注册一个简单工具

**使用注意事项**:

- 装饰器注册一个简单工具。
- 工具使用函数的名称进行注册。
- 每个参数的描述来自函数的文档字符串，它遵循文档字符串的相同格式。

### 7.3.2 @on_tools - 工具注册

`@on_tools` 装饰器将函数注册为代理可调用的工具。

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

**用途**: 将函数注册为代理可以调用的可用工具。

**使用注意事项**:

- 函数必须为参数提供适当的类型提示
- 函数文档字符串成为工具描述
- 注册的工具会自动对代理可用

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

@on_precompletion()
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

@on_completion()
async def postprocess_response(event: CompletionEvent):
    # 在从 LLM 接收后处理响应
    print(event)
```

**用途**: 在从 LLM 接收响应后运行，允许对响应进行后处理。

## 7.4 类型定义和异常

### 7.4.1 预定义类型

AmritaCore 提供了几个预定义类型以确保一致性:

- [BaseModel](classes/BaseModel.md): 所有数据模型的基类
- [Function](classes/Function.md): 在工具系统中表示一个可调用函数
- [FunctionDefinitionSchema](classes/FunctionDefinitionSchema.md): 函数参数的模式
- [MemoryModel](classes/MemoryModel.md): 存储对话历史
- [ModelConfig](classes/ModelConfig.md): 模型特定配置
- [ModelPreset](classes/ModelPreset.md): 特定模型的完整配置
- [TextContent](classes/TextContent.md): 表示消息中的文本内容
- [ToolCall](classes/ToolCall.md): 表示工具的调用
- [ToolContext](classes/ToolContext.md): 为工具执行提供上下文
- [ToolResult](classes/ToolResult.md): 表示工具调用的结果
- [ToolsManager](classes/ToolsManager.md): 管理注册的工具
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

此 API 参考提供了核心 AmritaCore 接口、类和装饰器的全面概述。每个组件都设计为协同工作，以提供一个灵活且强大的 AI 代理构建框架。