# 核心概念

## 配置系统

### 3.1.1 AmritaConfig 总体配置

[AmritaConfig](../api-reference/classes/AmritaConfig.md) 类作为 AmritaCore 的中央配置对象。它结合了三个不同的配置类：

- `FunctionConfig`: 定义Agent的行为方面
- `LLMConfig`: 控制语言模型交互
- `CookieConfig`: 处理安全方面

```python
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig, CookieConfig

# 完整配置
config = AmritaConfig(
    function_config=FunctionConfig(...),
    llm=LLMConfig(...),
    cookie=CookieConfig(...)
)

# 应用配置
from amrita_core.config import set_config
set_config(config)
```

### 3.1.2 FunctionConfig 功能配置

[FunctionConfig](../api-reference/classes/FunctionConfig.md) 类控制Agent的功能行为：

#### 3.1.2.1 use_minimal_context 上下文模式

`use_minimal_context` 标志决定是使用最小上下文（系统提示 + 用户最后的消息）还是完整对话历史：

```python
from amrita_core.config import FunctionConfig

# 使用完整上下文（默认）
func_config_full = FunctionConfig(use_minimal_context=False)

# 使用最小上下文（更节省Token）
func_config_minimal = FunctionConfig(use_minimal_context=True)
```

#### 3.1.2.2 tool_calling_mode 工具调用模式

`tool_calling_mode` 属性指定工具如何被调用：

- `"agent"`: Agent自主决定何时使用工具
- `"rag"`: 工具主要用于检索增强生成，只在一次对话中调用一次。
- `"none"`: 工具被禁用

```python
# Agent决定何时使用工具
func_config_agent = FunctionConfig(tool_calling_mode="agent")

# 主要用于RAG目的
func_config_rag = FunctionConfig(tool_calling_mode="rag")
```

#### 3.1.2.3 agent_thought_mode Agent思维模式

`agent_thought_mode` 属性控制Agent如何处理信息：

- `"reasoning"`: 在每次用户消息开始时进行推理
- `"chat"`: 直接执行任务而不进行明确推理
- `"reasoning-required"`: 每次工具调用都需要推理
- `"reasoning-optional"`: 允许推理但不要求

```python
# 推理模式
func_config_reasoning = FunctionConfig(agent_thought_mode="reasoning")

# 直接聊天模式
func_config_chat = FunctionConfig(agent_thought_mode="chat")
```

#### 3.1.2.4 agent_mcp_client_enable MCP 客户端配置

`agent_mcp_client_enable` 标志启用或禁用模型上下文协议 (MCP) 客户端功能：

```python
# 启用 MCP 客户端
func_config_mcp = FunctionConfig(
    agent_mcp_client_enable=True,
    agent_mcp_server_scripts=["script1.mcp", "script2.mcp"]
)
```

### 3.1.3 LLMConfig 大模型配置

[LLMConfig](../api-reference/classes/LLMConfig.md) 类控制与语言模型的交互：

#### 3.1.3.1 enable_memory_abstract 记忆抽象

`enable_memory_abstract` 属性启用对话历史的自动摘要以管理Token使用：

```python
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # 在达到上下文长度的 15% 时进行摘要
)
```

#### 3.1.3.2 其他模型参数

其他参数控制Token使用、超时和重试行为：

```python
llm_config = LLMConfig(
    max_tokens=100,                   # 响应中的最大Token数
    llm_timeout=60,                   # 请求超时（秒）
    auto_retry=True,                  # 自动重试失败的请求
    max_retries=3,                    # 最大重试次数
    memory_length_limit=50            # 记忆上下文中的最大消息数
)
```

### 3.1.4 CookieConfig 安全配置

[CookieConfig](../api-reference/classes/CookieConfig.md) 类处理与安全相关的设置：

```python
from amrita_core.config import CookieConfig

security_config = CookieConfig(
    enable_cookie=True,               # 启用 cookie 泄露检测
    cookie="random_cookie_string"     # 用于安全检测的 cookie 字符串
)
```

### 3.1.5 配置最佳实践

- 对简单查询使用最小上下文以节省Token
- 对长对话启用记忆抽象
- 根据您的 LLM 提供商调整超时和重试设置
- 在生产环境中保持安全功能启用

## 3.5 高级概念

### 3.5.1 ChatObject 对话对象

[ChatObject](../api-reference/classes/ChatObject.md) 是管理单个对话的核心类：

```python
import asyncio
from amrita_core import ChatObject



chat = ChatObject(
    context=memory_model,      # 记忆上下文
    session_id="session_123",  # 唯一会话标识符
    user_input="Hello!",       # 用户输入
    train=system_prompt        # 系统指令
)

async def msg_getter(chatobj: ChatObject) -> None:
    async for message in chatobj.get_response_generator():
        print(message if isinstance(message, str) else message.get_content(), end="")
    print("\n")

async with chat.begin():
    await msg_getter(chat)

```

### 3.5.2 PresetManager 预设管理器

[PresetManager](../api-reference/classes/PresetManager.md) 管理模型预设：

```python
from amrita_core.preset import PresetManager, ModelPreset

preset_manager = PresetManager()

# 添加预设
preset = ModelPreset(...)
preset_manager.add_preset(preset)
preset_manager.set_default_preset(preser.name)

# 获取可用预设
presets = preset_manager.get_presets()
```

### 3.5.3 流式处理设计

AmritaCore 对所有响应使用流式传输以提供实时反馈：

```python
# 响应以异步生成器形式返回
async for chunk in chat.get_response_generator():
    # 实时处理每个块
    print(chunk, end="")
```

### 3.5.4 回调式响应

AmritaCore 支持回调式响应：

```python
async def callback(chunk):
    print(chunk, end="")

chat.set_callback_func(callback)
await chat.begin()
```

### 3.5.5 记忆摘要机制

记忆摘要机制自动压缩对话历史以管理Token使用：

```python
# 通过 LLMConfig 配置
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # 达到上下文的 15% 时进行摘要
)
```
