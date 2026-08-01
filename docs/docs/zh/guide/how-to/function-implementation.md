# 函数实现

## 初始化与加载

### load_amrita() 异步加载

`load_amrita()` 函数在配置中启用 MCP 时异步加载 MCP 客户端。分词器和适配器已在导入时自动注册：

```python
import asyncio
from amrita_core import load_amrita

async def main():
    # 加载 MCP 客户端（仅在启用 MCP 时需要）
    await load_amrita()

asyncio.run(main())
```

### 配置设置与获取

#### set_config() 设置配置

`set_config()` 函数将配置应用到 AmritaCore：

```python
from amrita_core.config import AmritaConfig, set_config

# 创建并设置配置
config = AmritaConfig()
set_config(config)
```

#### get_config() 获取配置

`get_config()` 函数获取当前的 AmritaCore 配置：

```python
from amrita_core.config import get_config

# 获取当前配置
current_config = get_config()
print(current_config.function_config.use_minimal_context)
```

### 初始化过程详解

自 v0.9.0rc1 起，初始化过程已简化：

1. _(可选)_ 使用 `set_config()` 设置所需配置
2. 调用 `load_amrita()` 启动 MCP 客户端（仅在启用 MCP 时需要；分词器和适配器已在导入时注册）

```python
from amrita_core import load_amrita
from amrita_core.config import AmritaConfig, set_config

# 步骤 1：(可选) 设置配置
config = AmritaConfig()
set_config(config)

# 步骤 2：启动 MCP 客户端（仅在启用 MCP 时需要）
import asyncio
asyncio.run(load_amrita())
```

## Agent 策略生命周期方法

AmritaCore 中的 agent 策略实现了多个生命周期方法，在执行的各个阶段被调用。

### on_post_process() 后处理钩子

`on_post_process()` 方法是一个**后执行钩子**，在所有 agent 步骤成功完成后调用。此钩子适用于**所有策略类别**（`"agent"`、`"rag"`、`"workflow"`、`"agent-mixed"`）。

**目的**：此钩子允许策略执行最终的上下文修改、添加完成指令或在生成最终响应之前执行清理操作。

**使用示例**：

```python
async def on_post_process(self) -> None:
    """在 agent 成功执行后调用"""
    if self.call_count >= 2:  # 仅在确实调用了工具时
        self.ctx.message.append(
            Message(
                role="user",
                content="<END_OF_PROCESS>\n请根据之前获取的信息直接回答我。\n<END_OF_PROCESS>"
            )
        )
```

**关键特性**：

- 仅在成功执行（无异常发生）时调用
- 适用于**所有策略类别**
- 可以在最终完成前修改对话上下文
- 适用于添加最终指令或上下文总结

### 其他生命周期方法

- **`run()`**：`"workflow"` 和 `"rag"` 类别的主执行方法
- **`single_execute()`**：`"agent"` 和 `"agent-mixed"` 类别的单步执行方法
- **`on_exception(exc: BaseException)`**：在执行期间发生异常时调用。默认实现不执行任何操作（静默通过），而不是引发 `NoExceptionHandler`。自定义策略应重写此方法以实现特定的错误处理逻辑。

#### 异常处理最佳实践

默认的 `on_exception()` 方法不再默认抛出异常，为自定义错误处理提供了更多灵活性：

```python
from amrita_core.agent.strategy import AgentStrategy

class CustomAgentStrategy(AgentStrategy):
    async def on_exception(self, exc: BaseException) -> None:
        """自定义异常处理逻辑"""
        # 记录异常
        logger.error(f"Agent 执行失败：{exc}")

        # 可选地重新抛出特定异常
        if isinstance(exc, ValueError):
            raise exc

        # 或者优雅处理并继续
        self.ctx.message.append(
            Message(
                role="user",
                content="处理过程中发生错误，请重试。"
            )
        )
```

**重点**：

- 默认行为现在是**静默失败处理**——异常被捕获但不重新抛出
- 自定义策略应在 `on_exception()` 中实现自己的错误处理逻辑
- 如果需要旧行为（重新抛出异常），在自定义实现中显式调用 `raise exc`

## 对话交互流程

### 创建 ChatObject 对话对象

[ChatObject](../api-reference/classes/ChatObject.md) 类是对话的主要接口：

```python
from amrita_core import ChatObject
from amrita_core.types import MemoryModel, Message

# 创建记忆上下文
context = MemoryModel()

# 创建系统消息
train = Message(content="你是一个乐于助人的助手。", role="system")

# 创建 ChatObject
chat = ChatObject(
    context=context,
    session_id="session_123",
    user_input="你好，最近怎么样？",
    train=train.model_dump()
)
```

#### 使用预组合工作流（v0.12.6+）

你可以传递预组合的工作流来替换默认管道：

```python
from amrita_core import ChatObject
from amrita_core.builtins.workflows import SIMPLE_REACT, SIMPLE_CHAT

# 完整的 ReAct agent 管道
chat = ChatObject(
    train={"role": "system", "content": "你是一个乐于助人的助手。"},
    user_input="搜索最新的 AI 新闻。",
    session_id="session_123",
    workflow=SIMPLE_REACT,
)

# 纯聊天——无 agent，无工具调用
chat = ChatObject(
    train={"role": "system", "content": "你是一个乐于助人的助手。"},
    user_input="你好！",
    session_id="session_456",
    workflow=SIMPLE_CHAT,
)
```

> 所有可用工作流参见 [`builtins.workflows`](../guide/builtins#_9-6-built-in-workflows-v0-12-6)。

### begin() 执行对话

#### 基本用法

`begin()` 方法启动内部任务；然后你必须 await `ChatObject` 本身以等待完成（当使用回调函数时推荐此方式）：

```python
# 启动任务，然后等待其完成
chat.begin()
await chat
```

#### 作为上下文管理器使用（推荐）

> ⚠️ 退出上下文管理器将终止内部任务而非等待它。务必在块内 `await chat`：

```python
async with chat.begin():
    ...
    await chat  # 退出前等待任务完成
```

### full_response() 获取完整响应

`full_response()` 方法从对话中获取完整响应：

```python
# 获取完整响应
response = await chat.full_response()
print(response)
```

### 流式响应处理

AmritaCore 使用 **AnyIO 内存对象流**进行流式响应，提供内置的背压处理：

```python
# 处理流式响应
async for message in chat.io_stream.get_response_generator():
    content = message if isinstance(message, str) else message.get_content()
    print(content, end="")
```

### 响应回调

AmritaCore 支持响应回调以实现实时交互：

```python
async def response_callback(message):
    print(message)

chat.io_stream.set_callback_func(response_callback)
chat.begin()
await chat
```

::: warning

`get_response_generator()` 或 `full_response()` 是一次性操作。这意味着你只能调用 `full_response()` 或 `get_response_generator()` 一次，否则将引发 `RuntimeError`。

:::

### 对话生命周期

典型的对话生命周期包括：

1. 创建记忆上下文
2. 定义系统指令
3. 创建 ChatObject
4. 执行对话
5. 处理响应
6. 为后续交互更新上下文

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
    async for message in chat.io_stream.get_response_generator():
        print(message, end="")
    await chat  # 退出前等待任务完成

# 为下次交互更新上下文
context = chat.data
```

## 事件处理实现

### @on_event 事件监听器

事件监听器使用 `@on_event` 装饰器创建：

```python
from amrita_core.hook.on import on_event

@on_event()
def my_event_handler(event):
    print(f"收到事件：{event}")
```

### @on_precompletion 前置完成钩子

前置完成钩子在发送请求给 LLM 之前执行：

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion

@on_precompletion().handle()
async def preprocess_request(event: PreCompletionEvent):
    # 在发送给 LLM 之前修改消息
    event.messages.append(Message(role="system", content="请简洁回答"))
```

### @on_completion 后置完成钩子

后置完成钩子在收到 LLM 响应后执行：

```python
from amrita_core.hook.event import CompletionEvent
from amrita_core.hook.on import on_completion

@on_completion().handle()
async def postprocess_response(event: CompletionEvent):
    # 在返回给用户之前处理响应
    print(f"收到响应：{event.response[:50]}...")
```

### 事件处理最佳实践

- 使用前置完成钩子在 LLM 处理前修改消息
- 使用后置完成钩子处理或记录响应
- 执行异步操作时确保事件处理器是 async 的
- 从处理器返回事件对象以继续链式处理

## 工具调用实现

### 工具注册示例

注册供 agent 使用的工具，含全面的验证功能：

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    FunctionPropertySchema,
)

# 定义具有高级验证的函数 schema
weather_func = FunctionDefinitionSchema(
    name="get_current_weather",
    description="获取给定地点的当前天气",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "location": FunctionPropertySchema(
                type="string",
                description="城市和州，例如 北京，中国",
                minLength=2,
                maxLength=100,
                pattern=r"^[a-zA-Z\s,-]+$"
            ),
            "unit": FunctionPropertySchema(
                type="string",
                enum=["celsius", "fahrenheit"],
                description="温度单位"
            ),
            "forecast_days": FunctionPropertySchema(
                type="integer",
                description="预报天数（0 表示仅当前）",
                minimum=0,
                maximum=7,
                default=0
            )
        },
        required=["location"]
    )
)

@on_tools(data=weather_func)
async def get_current_weather(data: dict) -> str:
    """获取给定地点的当前天气"""
    location = data["location"]
    unit = data.get("unit", "celsius")
    forecast_days = data.get("forecast_days", 0)

    if forecast_days == 0:
        return f"{location} 当前天气晴朗，温度 22 度 {unit}。"
    else:
        return f"{location} 天气预报（{forecast_days} 天）：晴朗，温度范围 18-25 度 {unit}。"
```

### 增强的验证功能

`FunctionPropertySchema` 支持全面的 JSON Schema 验证：

- **数值约束**：`minimum`、`maximum`、`exclusiveMinimum`、`exclusiveMaximum`、`multipleOf`
- **字符串约束**：`minLength`、`maxLength`、`pattern`、`format`
- **数组约束**：`items`、`minItems`、`maxItems`、`uniqueItems`
- **对象约束**：`properties`、`required`、`additionalProperties`
- **特殊值**：`enum`、`const`、`default`
- **联合类型**：`type` 可以是允许类型的列表

当 LLM 生成工具调用时，这些约束会自动验证，确保只有有效的参数值被传递给你的工具函数。
