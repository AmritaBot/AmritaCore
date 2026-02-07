# 功能实现

## 4.1 初始化和加载

### 4.1.1 init() 初始化函数

`init()` 函数初始化 AmritaCore 的核心组件，必须在任何其他操作之前调用：

```python
from amrita_core import init

# 初始化 AmritaCore
init()
```

此函数执行几个关键任务：

- 设置内部日志
- 初始化 Jieba 用于文本处理（如果可用）
- 加载内置模块
- 准备核心框架以供使用

### 4.1.2 load_amrita() 异步加载

`load_amrita()` 函数异步加载 AmritaCore 组件，特别是在启用 MCP 客户端功能时：

```python
import asyncio
from amrita_core import load_amrita

async def main():
    # 加载 AmritaCore 组件
    await load_amrita()

asyncio.run(main())
```

### 4.1.3 配置设置和检索

#### 4.1.3.1 set_config() 设置配置

`set_config()` 函数将配置应用到 AmritaCore：

```python
from amrita_core.config import AmritaConfig, set_config

# 创建并设置配置
config = AmritaConfig()
set_config(config)
```

#### 4.1.3.2 get_config() 检索配置

`get_config()` 函数检索当前 AmritaCore 配置：

```python
from amrita_core.config import get_config

# 检索当前配置
current_config = get_config()
print(current_config.function_config.use_minimal_context)
```

### 4.1.4 初始化过程详情

初始化过程涉及：

1. 调用 `init()` 准备核心组件
2. 使用 `set_config()` 设置所需配置
3. 使用 `load_amrita()` 加载附加组件

```python
from amrita_core import init, load_amrita
from amrita_core.config import AmritaConfig, set_config

# 步骤 1: 初始化核心组件
init()

# 步骤 2: 设置配置
config = AmritaConfig()
set_config(config)

# 步骤 3: 加载附加组件
import asyncio
asyncio.run(load_amrita())
```

## 4.2 对话交互流程

### 4.2.1 创建 ChatObject 对话对象

`ChatObject` 类是对话的主要接口：

```python
from amrita_core import ChatObject
from amrita_core.types import MemoryModel, Message

# 创建记忆上下文
context = MemoryModel()

# 创建系统消息
train = Message(content="您是一个有用的助手。", role="system")

# 创建 ChatObject
chat = ChatObject(
    context=context,
    session_id="session_123",
    user_input="你好，你怎么样？",
    train=train.model_dump()
)
```

### 4.2.2 begin() 执行对话

#### 基本用法

`begin()` 方法执行对话并处理输入：

```python
# 执行对话
await chat.begin()

```

#### 用作上下文管理器（推荐）

```python

# 我们更喜欢使用上下文管理器：
async with chat.begin():
    ...

```

### 4.2.3 full_response() 获取完整响应

`full_response()` 方法从对话中检索完整响应：

```python
# 获取完整响应
response = await chat.full_response()
print(response)
```

### 4.2.4 流式响应处理

AmritaCore 支持流式响应以实现实时交互：

```python
# 处理流式响应
async for message in chat.get_response_generator():
    content = message if isinstance(message, str) else message.get_content()
    print(content, end="")
```

::: warning

`get_response_generator()` 或 `full_response()` 是一次性操作。这意味着您只能调用 `full_response()` 或 `get_response_generator()` 一次，否则将引发 `RuntimeError`。

:::

### 4.2.5 对话生命周期

典型的对话生命周期包括：

1. 创建记忆上下文
2. 定义系统指令
3. 创建 ChatObject
4. 执行对话
5. 处理响应
6. 更新上下文以进行后续交互

```python
# 完整对话生命周期
context = MemoryModel()
train = Message(content="你是一个乐于助人的助手。", role="system")

async with ChatObject(
    context=context,
    session_id="session_123",
    user_input="你好！",
    train=train.model_dump()
).begin() as chat:
    async for message in chat.get_response_generator():
        print(message, end="")

# 更新上下文以进行下次交互
context = chat.data
```

## 4.3 事件处理实现

### 4.3.1 @on_event 事件监听器

使用 `@on_event` 装饰器创建事件监听器：

```python
from amrita_core.hook.on import on_event

@on_event()
def my_event_handler(event):
    print(f"收到事件: {event}")

```

### 4.3.2 @on_precompletion 预完成钩子

预完成钩子在发送请求到 LLM 之前执行：

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion()
async def preprocess_request(event: PreCompletionEvent):
    # 在发送到 LLM 之前修改消息
    event.messages.append(Message(role="system", content="请在回复中保持简洁"))

```

### 4.3.3 @on_completion 后完成钩子

后完成钩子在从 LLM 接收响应后执行：

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion()
async def postprocess_response(event: CompletionEvent):
    # 在返回给用户之前处理响应
    print(f"收到响应: {event.response[:50]}...")

```

### 4.3.4 事件处理最佳实践

- 在 LLM 处理之前使用预完成钩子修改消息
- 使用后完成钩子处理或记录响应
- 在执行异步操作时确保事件处理器是异步的
- 从处理器返回事件对象以继续链

## 4.4 工具调用实现

### 4.4.1 工具注册示例

为Agent注册工具以供使用：

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

# 首先定义函数模式
weather_func = FunctionDefinitionSchema(
    name="get_current_weather",
    description="获取给定位置的当前天气",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "location": FunctionPropertySchema(
                type="string",
                description="城市和州，例如 旧金山，CA"
            ),
            "unit": FunctionPropertySchema(
                type="string",
                enum=["celsius", "fahrenheit"],
                description="温度单位"
            )
        },
        required=["location"]
    )
)

@on_tools(data=weather_func)
async def get_current_weather(data: dict) -> str:
    """
    获取给定位置的当前天气
    """
    location = data["location"]
    unit = data.get("unit", "celsius")  # 如果未提供，默认为摄氏度

    # 模拟天气查询
    return f"{location}的天气是晴朗的，温度是{22}度{unit}。"
```

### 4.4.2 工具执行流程

工具执行流程包括：

1. 在 LLM 响应中检测工具
2. 参数提取
3. 工具执行
4. 结果整合到对话中

### 4.4.3 错误处理

工具实现中的适当错误处理：

```python
from typing import Any
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

# 定义函数模式
divide_func = FunctionDefinitionSchema(
    name="safe_divide",
    description="安全地除两个数",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "dividend": FunctionPropertySchema(
                type="number",
                description="除法中的被除数"
            ),
            "divisor": FunctionPropertySchema(
                type="number",
                description="除法中的除数"
            )
        },
        required=["dividend", "divisor"]
    )
)

@on_tools(data=divide_func)
async def safe_divide(data: dict) -> str:
    """
    安全地除两个数
    """
    try:
        dividend = data["dividend"]
        divisor = data["divisor"]

        if divisor == 0:
            return "错误：不能除以零"

        result = dividend / divisor
        return f"{dividend} 除以 {divisor} 等于 {result}"
    except Exception as e:
        return f"发生错误：{str(e)}"
```

### 4.4.4 自定义运行模式

某些工具可能需要访问事件上下文或需要更高级的处理。为此，可以启用 `custom_run` 选项：

````python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema, ToolContext
from amrita_core.logging import logger

# 定义函数模式
process_message_tool = FunctionDefinitionSchema(
    name="processing_message",
    description="描述Agent当前正在做什么，并向用户表达Agent的内部想法",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "content": FunctionPropertySchema(
                type="string",
                description="描述当前操作的消息内容"
            )
        },
        required=["content"]
    )
)

@on_tools(data=process_message_tool, custom_run=True)
async def process_message(ctx: ToolContext) -> str | None:
    """
    处理消息并通过聊天对象发送给用户
    """
    content = ctx.data["content"]
    logger.debug(f"[LLM-ProcessMessage] {content}")

    # 直接向聊天对象发送消息
    await ctx.event.chat_object.yield_response(f"{content}\n")

    # 返回处理结果
    return f"向用户发送了消息:\n\n```text\n{content}\n```\n"
````

在自定义运行模式中：

- 函数接收 `ToolContext` 对象而不是原始参数
- `ToolContext` 包含：
  - `ctx.data`: 传递给工具的参数
  - `ctx.event`: 当前事件，允许访问聊天对象
  - `ctx.matcher`: 与事件关联的匹配器
- 函数可以是同步或异步的
- 返回类型可以是 `str` 或 `None`

## 4.5 记忆管理

### 4.5.1 MemoryModel 记忆结构

`MemoryModel` 类结构：

```python
from amrita_core.types import MemoryModel, Message

# 创建和使用记忆模型
memory = MemoryModel()
memory.messages.append(Message(role="user", content="你好"))
memory.messages.append(Message(role="assistant", content="你好！"))
```

### 4.5.2 上下文窗口管理

使用配置管理上下文窗口：

```python
from amrita_core.config import LLMConfig

# 限制记忆中的消息数量
llm_config = LLMConfig(
    memory_length_limit=50  # 只保留最后 50 条消息
)
```

### 4.5.3 消息摘要功能

自动消息摘要：

```python
from amrita_core.config import LLMConfig

# 启用记忆摘要
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # 在上下文长度的 15% 时进行摘要
)
```

### 4.5.4 长对话处理

高效处理长对话：

```python
from amrita_core.config import FunctionConfig, LLMConfig, AmritaConfig

# 长对话的配置
long_convo_config = AmritaConfig(
    function_config=FunctionConfig(
        use_minimal_context=True  # 使用最小上下文以节省Token
    ),
    llm=LLMConfig(
        enable_memory_abstract=True,  # 启用摘要
        memory_length_limit=100       # 增加记忆限制
    )
)
```

### 4.5.5 记忆优化技术

- 在适当时候使用最小上下文
- 为长时间运行的会话启用记忆摘要
- 实施会话清理策略
- 定期监控Token使用情况

## 4.6 日志和调试

### 4.6.1 Logger 日志系统

使用内置日志记录器：

```python
from amrita_core.logging import logger

# 记录信息消息
logger.info("开始对话...")

# 记录调试信息
logger.debug("处理消息: %s", user_input)

# 记录错误
logger.error("处理请求失败: %s", error)
```

### 4.6.2 @debug_log 调试日志

`@debug_log` 装饰器已弃用，推荐使用标准日志记录器：

```python
# 使用 logger 而不是 @debug_log
from amrita_core.logging import logger

def my_function(param):
    logger.debug(f"处理参数: {param}")
    # 函数实现
```

### 4.6.3 get_last_response() 获取最后响应

从对话中检索最后的响应：

```python
from amrita_core.libchat import get_last_response

# 获取最后的响应
last_resp = get_last_response(chat_object)
print(last_resp)
```

### 4.6.4 get_tokens() 获取Token使用情况

监控Token使用情况：

```python
from amrita_core.libchat import get_tokens

# 获取Token计数
tokens_used = get_tokens()
print(f"使用的Token: {tokens_used}")
```

### 4.6.5 调试技巧

- 在开发期间启用调试日志
- 监控Token使用情况以防止超出限制
- 使用流式响应进行实时反馈
- 为健壮的应用程序实现适当的错误处理