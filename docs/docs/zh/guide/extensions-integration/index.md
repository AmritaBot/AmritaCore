# 扩展与集成

## 5.1 扩展机制

### 5.1.1 简单工具

AmritaCore 提供了一种简单的方式来通过简单工具扩展其功能：

```python
from amrita_core import simple_tool

@simple_tool
def add(a: int, b: int) -> int:
    """相加两个数字

    Args:
        a (int): 第一个数字
        b (int): 第二个数字

    Returns:
        int: a 与 b 的和
    """
    return a + b
```

此工具将自动注册并可供Agent使用。

在工具的 `__doc__` 块）中，您可以按照 Google 格式为工具添加描述和参数。当调用工具时，这些参数将在 LLM 调用时用于描述参数。

**注册范围**: 使用 `@simple_tool` 注册的工具在模块加载期间被添加到全局容器中，并对所有会话都可用。

**支持的类型**: `@simple_tool` 装饰器现在支持丰富的类型注解，包括 Pydantic 模型、List[T] 和 Optional[T]。完整的类型支持详情请参阅[工具系统](../concepts/tool.md)文档。

### 5.1.2 工具系统扩展

AmritaCore 提供了一种灵活的方式来通过自定义工具扩展其功能。您可以创建新的工具，使Agent能够执行特定任务：

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

# 首先使用高级验证定义函数模式
calculate_math_tool = FunctionDefinitionSchema(
    name="calculate_math",
    description="计算数学表达式的结果",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "expression": FunctionPropertySchema(
                type="string",
                description="要计算的数学表达式",
                minLength=1,
                maxLength=1000,
                pattern=r"^[0-9+\-*/().\s]+$"  # 只允许安全的数学字符
            ),
            "precision": FunctionPropertySchema(
                type="integer",
                description="结果的小数位数",
                minimum=0,
                maximum=10,
                default=2
            )
        },
        required=["expression"]
    )
)

@on_tools(data=calculate_math_tool)
async def calculate_math(data: dict) -> str:
    """
    计算数学表达式的结果
    """
    # 在实际实现中，您需要使用安全的求值方法
    # 或专用的数学库来防止代码注入
    expression = data["expression"]
    precision = data.get("precision", 2)

    # 模式验证确保只包含安全字符
    try:
        result = eval(expression)
        return f"{float(result):.{precision}f}"  # 必须返回字符串！
    except Exception as e:
        return "0.0"
```

**注册范围**: 与 `@simple_tool` 类似，`@on_tools` 装饰器在模块加载期间将工具注册到全局容器中。

### 增强的验证功能

`FunctionPropertySchema` 支持全面的 JSON Schema 验证，包含类型特定的约束：

- **数值约束**：`minimum`、`maximum`、`exclusiveMinimum`、`exclusiveMaximum`、`multipleOf`
- **字符串约束**：`minLength`、`maxLength`、`pattern`、`format`
- **数组约束**：`items`、`minItems`、`maxItems`、`uniqueItems`
- **对象约束**：`properties`、`required`、`additionalProperties`
- **特殊值**：`enum`、`const`、`default`
- **联合类型**：`type` 可以是允许类型的列表（仅适用于手动模式定义，不适用于 `@simple_tool`）

当 LLM 生成工具调用时，这些约束会自动验证，确保只有有效的参数值传递给您的工具函数。

> **关于注册方法的说明**:
>
> - **装饰器**（`@simple_tool`、`@on_tools`）：在模块加载时注册到全局容器，对所有会话都可用
> - **直接管理器操作**：允许在运行时使用 `ToolsManager` 或 `MultiToolsManager` 实例进行会话特定的工具管理

### 5.1.3 高级工具模式

对于需要访问事件上下文或更高级处理的工具，您可以使用 `custom_run` 模式：

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
                description="描述当前动作的消息内容"
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
    await ctx.ctx.chat_object.yield_response(f"{content}\\n")

    # 返回处理结果
    return f"向用户发送了消息:\\n\\n```text\\n{content}\\n```\\n"
````

在自定义运行模式中：

- 函数接收 `ToolContext` 对象而不是原始参数
- `ToolContext` 包含:
  - `ctx.data`: 传递给工具的参数
  - `ctx.ctx`: 包含当前执行上下文的 [StrategyContext](../api-reference/classes/StrategyContext.md)，包括对聊天对象的访问
- 函数可以是同步或异步的
- 返回类型可以是 `str` 或 `None`

### 5.1.4 事件钩子扩展

事件钩子允许您拦截和修改处理管道：

```python
from amrita_core.hook.event import PreCompletionEvent, CompletionEvent
from amrita_core.hook.on import on_precompletion, on_completion
from amrita_core.types import Message

@on_precompletion().handle()
async def inject_context(event: PreCompletionEvent):
    """在LLM处理之前注入自定义上下文"""
    event.messages.append(Message(
        role="system",
        content="请记住在回复中保持简洁和有用。"
    ))


@on_completion().handle()
async def log_response(event: CompletionEvent):
    """记录处理后的响应"""
    print(f"收到响应: {event.response[:100]}...")

```

### 5.1.5 协议适配器与自定义分词器

协议适配器允许 AmritaCore 与不同的 LLM 提供商或通信协议一起工作。分词器用于处理文本的分词，支持内存管理和上下文窗口控制。

适配器和分词器均支持 **两种注册机制**：

#### 机制一：通过子类化隐式注册（任意位置）

在任何位置继承 `ModelAdapter` 或 `BaseTokenizer` — 当模块被导入时，`__init_subclass__` 钩子会自动将类注册到对应的管理器（`AdapterManager` / `TokenizerManager`）。

```python
# my_project/adapters.py
from amrita_core.base.adapter import ModelAdapter
from amrita_core.base.tokenizer import BaseTokenizer

class MyCustomAdapter(ModelAdapter):
    # 手动导入此模块以触发注册
    ...

class MyCustomTokenizer(BaseTokenizer):
    # 手动导入此模块以触发注册
    ...
```

然后显式导入以触发注册：

```python
import my_project.adapters  # 触发 __init_subclass__ 注册
```

#### 机制二：命名空间包自动发现（推荐，用于内置风格）

AmritaCore 使用 Python 的**命名空间包**机制（PEP 420）在启动时自动发现适配器和分词器。只需将文件放入 `adapters/` 或 `tokenizers/` 目录且**不包含 `__init__.py`** — 该目录即成为命名空间包，`side_effect_import`（在 `amrita_core` 导入时调用）会自动发现并导入所有子模块。

```
src/amrita_core/
├── adapters/          # ← 绝对不能有 __init__.py
│   ├── openai.py      # 自动发现
│   ├── anthropic.py   # 自动发现
│   └── my_adapter.py  # ← 你的自定义适配器
├── tokenizers/        # ← 绝对不能有 __init__.py
│   ├── simple.py      # 自动发现
│   └── my_tokenizer.py # ← 你的自定义分词器
```

**导入时的执行流程：**

1. `import amrita_core` 运行 `side_effect_import(adapters)` 和 `side_effect_import(tokenizers)`
2. 这些函数扫描命名空间包目录中的所有 `.py` 文件（通过 `pkgutil.iter_modules`）
3. 每个发现的模块被导入，触发 `ModelAdapter` / `BaseTokenizer` 的 `__init_subclass__` 钩子
4. 类自动注册到 `AdapterManager` / `TokenizerManager`

**重要规则**：`adapters/` 和 `tokenizers/` 目录**绝对不能包含 `__init__.py`**。`__init__.py` 会将其变为常规包，破坏命名空间包的自动发现机制。

#### 示例：创建适配器

```python
# src/amrita_core/adapters/custom_protocol.py
from amrita_core.base.adapter import ModelAdapter
from amrita_core.types import ModelPreset
from collections.abc import AsyncGenerator, Iterable
from amrita_core.types import UniResponse

class CustomAdapter(ModelAdapter):
    def __init__(self, preset: ModelPreset):
        super().__init__(preset=preset)
        self.__override__ = True  # 允许覆盖现有适配器

    async def call_api(
        self, messages: Iterable
    ) -> AsyncGenerator[str | UniResponse[str, None], None]:
        # 在响应到达时产生响应块，最后产生一个 UniResponse
        yield "响应块"
        yield UniResponse(
            role="assistant",
            content="完整响应",
            usage=None,
            tool_calls=None,
        )

    @staticmethod
    def get_adapter_protocol() -> str | tuple[str, ...]:
        return "custom_protocol"  # 返回协议名称
```

## 5.2 MCP 客户端集成

### 5.2.1 什么是 MCP？

模型上下文协议 (MCP) 是用于将工具和数据源连接到 AI 模型的标准。它允许模型以结构化方式与外部系统交互，将其功能扩展到训练数据之外。

### 5.2.2 mcp.ClientManager MCP 客户端管理

`ClientManager` 类管理 MCP 客户端连接：

```python
from amrita_core.tools import mcp

# 为会话初始化 MCP 客户端
async def setup_mcp_clients():
    client_manager = mcp.ClientManager()
    scripts = [
        "/path/to/script1.mcp",
        "/path/to/script2.mcp"
    ]
    await client_manager.initialize_scripts_all(scripts)
```

### 5.2.3 MCP 脚本配置

在设置中配置 MCP 脚本：

```python
from amrita_core.config import AmritaConfig, FunctionConfig

config = AmritaConfig(
    function_config=FunctionConfig(
        agent_mcp_client_enable=True,
        agent_mcp_server_scripts=[
            "./mcp-scripts/weather.mcp",
            "./mcp-scripts/database.mcp",
            "./mcp-scripts/calendar.mcp"
        ]
    )
)
```

### 5.2.4 MCP 实际应用示例

现实世界中的 MCP 使用案例：

1. **数据库访问**: 通过 MCP 客户端查询数据库
2. **文件系统操作**: 安全地读取/写入文件
3. **API 集成**: 连接到第三方 API
4. **物联网设备**: 与物理设备接口

有关 MCP 服务集成、架构以及如何创建您自己的 MCP 服务器的详细信息，请参阅 [MCP 服务集成](./mcp-server-integration.md)。

## 5.3 自定义扩展开发

### 5.3.1 创建自定义工具

为特定功能开发自定义工具：

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema
from typing import Dict, Any
import json

# 为翻译定义函数模式
translate_tool = FunctionDefinitionSchema(
    name="translate_text",
    description="将文本翻译为目标语言",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "text": FunctionPropertySchema(
                type="string",
                description="要翻译的文本"
            ),
            "target_language": FunctionPropertySchema(
                type="string",
                description="目标语言代码（默认：en）",
                default="en"
            )
        },
        required=["text"]
    )
)

@on_tools(data=translate_tool)
async def translate_text(data: dict) -> str:
    """
    将文本翻译为目标语言
    """
    text = data["text"]
    target_language = data.get("target_language", "en")
    # 在实际实现中，连接到翻译 API
    # 对于此示例，我们将模拟翻译
    simulated_translation = f"[TRANSLATED TO {target_language.upper()}]: {text}"
    return simulated_translation

# 定义获取公司信息的函数模式
company_info_tool = FunctionDefinitionSchema(
    name="get_company_info",
    description="获取公司信息",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "company_name": FunctionPropertySchema(
                type="string",
                description="要查找的公司名称"
            )
        },
        required=["company_name"]
    )
)

@on_tools(data=company_info_tool)
async def get_company_info(data: dict) -> str:
    """
    获取公司信息
    """
    company_name = data["company_name"]
    # 这将在实际实现中连接到数据库或 API
    result = {
        "name": company_name,
        "status": "模拟",
        "info": f"关于 {company_name} 的信息"
    }
    return json.dumps(result)
```

### 5.3.2 创建自定义事件处理器

为专门处理构建自定义事件处理器：

```python
from amrita_core.hook.event import PreCompletionEvent
from amrita_core.hook.on import on_precompletion
from amrita_core.types import Message

@on_precompletion().handle()
async def security_check(event: PreCompletionEvent):
    """
    在处理之前执行安全检查
    """
    # 检查潜在有害内容
    for msg in event.messages:
        if msg.role == "user":
            # 在此处实施安全检查
            if "harmful" in msg.content.lower():
                # 修改消息以包含警告
                event.messages.append(Message(
                    role="system",
                    content="内容因安全原因被过滤"
                ))


```

### 5.3.3 创建自定义协议适配器

为不同 LLM 提供商构建适配器。关于两种注册机制（隐式子类化和命名空间包自动发现），请参见 [5.1.5 协议适配器与自定义分词器](#515-协议适配器与自定义分词器)。

```python
from amrita_core.base.adapter import ModelAdapter
from amrita_core.types import ModelPreset, UniResponse
from collections.abc import AsyncGenerator, Iterable
import aiohttp

class CustomLLMAdapter(ModelAdapter):
    def __init__(self, preset: ModelPreset):
        super().__init__(preset=preset)
        self.__override__ = True  # 允许覆盖现有注册

    async def call_api(
        self, messages: Iterable
    ) -> AsyncGenerator[str | UniResponse[str, None], None]:
        """
        调用自定义 LLM API
        """
        headers = {
            'Authorization': f'Bearer {self.preset.api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'messages': list(messages),
            'model': self.preset.model,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.preset.base_url}/chat/completions",
                                   json=payload, headers=headers) as response:
                result = await response.json()

                # 在到达时产生响应块（用于流式传输）
                # 为了简化此示例，我们将产生完整响应

                content = result['choices'][0]['message']['content']
                yield content  # 这逐块产生内容

                # 最后，产生完整的 UniResponse
                yield UniResponse(
                    role="assistant",
                    content=content,
                    usage=result.get('usage', {}),
                    tool_calls=None,
                )

    @staticmethod
    def get_adapter_protocol() -> str | tuple[str, ...]:
        return "custom_llm_protocol"  # 返回协议标识符
```

### 5.3.4 发布和共享扩展

要共享您的扩展：

1. 将它们打包为单独的 Python 模块
2. 记录功能和用法
3. 发布到 PyPI 或托管在 Git 存储库中
4. 提供示例和最佳实践

## 5.4 第三方集成

### 5.4.1 常见 LLM 提供商集成

与各种 LLM 提供商集成：

```python
# OpenAI 兼容端点
from amrita_core.types import ModelPreset, ModelConfig

openai_preset = ModelPreset(
    model="gpt-4",
    base_url="https://api.openai.com/v1",
    api_key="your-openai-api-key",
    config=ModelConfig(stream=True)
)

# Azure OpenAI
azure_preset = ModelPreset(
    model="your-deployment-name",
    base_url="https://your-resource.openai.azure.com",
    api_key="your-azure-api-key",
    config=ModelConfig(stream=True)
)
```

### 5.4.2 数据库连接

使用工具连接到数据库：

```python
import sqlite3
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema

# 定义函数模式
query_db_tool = FunctionDefinitionSchema(
    name="query_database",
    description="查询 SQLite 数据库",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "query": FunctionPropertySchema(
                type="string",
                description="要执行的 SQL 查询"
            )
        },
        required=["query"]
    )
)

@on_tools(data=query_db_tool)
async def query_database(data: dict) -> str:
    """
    查询 SQLite 数据库
    """
    query = data["query"]
    try:
        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        return str(results)
    except Exception as e:
        return f"执行查询时出错: {str(e)}"
```

### 5.4.3 API 集成

与外部 API 集成：

```python
from amrita_core.tools.manager import on_tools
from amrita_core.tools.models import FunctionDefinitionSchema, FunctionParametersSchema, FunctionPropertySchema
import aiohttp

# 定义函数模式
get_weather_tool = FunctionDefinitionSchema(
    name="get_weather_data",
    description="从外部 API 获取天气数据",
    parameters=FunctionParametersSchema(
        type="object",
        properties={
            "city": FunctionPropertySchema(
                type="string",
                description="要获取天气的城市"
            )
        },
        required=["city"]
    )
)

@on_tools(data=get_weather_tool)
async def get_weather_data(data: dict) -> str:
    """
    从外部 API 获取天气数据
    """
    city = data["city"]
    api_key = "your-weather-api-key"
    url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={city}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return f"天气在 {city}: {data['current']['condition']['text']}, {data['current']['temp_c']}°C"
            else:
                return f"无法检索 {city} 的天气"
```

### 5.4.3 其他框架集成

将 AmritaCore 与其他框架结合：

```python
# 示例: 与 FastAPI 集成为 Web 服务
from fastapi import FastAPI
from amrita_core import ChatObject, init
from amrita_core.config import AmritaConfig
from amrita_core.types import MemoryModel, Message

app = FastAPI()

# 启动应用时初始化 AmritaCore
init()
from amrita_core.config import set_config
set_config(AmritaConfig())

@app.post("/chat/")
async def chat_endpoint(user_input: str, session_id: str):
    context = MemoryModel()
    train = Message(content="您是一个有用的助手。", role="system")

    async with ChatObject(
        context=context,
        session_id=session_id,
        user_input=user_input,
        train=train.model_dump()
    ).begin() as chat:
        response = await chat.full_response()

    return {"response": response}
```

本节介绍了使用各种系统、工具和服务扩展和集成 AmritaCore 的多种方式。框架的模块化设计使其易于添加新功能，同时保持与核心架构的兼容性。
