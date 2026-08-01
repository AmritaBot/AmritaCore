# 配置系统

AmritaCore 的行为由一个中央配置对象控制，该对象组合了三个不同的配置类。本页解释每个配置类的作用和使用时机。

## AmritaConfig — 总体配置

[AmritaConfig](../api-reference/classes/AmritaConfig.md) 类作为 AmritaCore 的中央配置对象。它组合了三个不同的配置类：

- `FunctionConfig`：定义智能体的行为方面
- `LLMConfig`：控制语言模型交互
- `CookieConfig`：处理安全方面
- `BuiltinAgentConfig`：内置 Agent 的策略控制

```python
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig, CookieConfig, BuiltinAgentConfig

# 完整配置
config = AmritaConfig(
    function_config=FunctionConfig(...),
    llm=LLMConfig(...),
    cookie=CookieConfig(...),
    builtin=BuiltinAgentConfig(...),
)

# 应用配置
from amrita_core.config import set_config
set_config(config)
```

## FunctionConfig — 功能配置

[FunctionConfig](../api-reference/classes/FunctionConfig.md) 类控制 AmritaCore 的主要功能行为。

### use_minimal_context — 上下文模式

`use_minimal_context` 标志决定使用最小上下文（系统提示 + 用户的最后一条消息）还是完整对话历史：

```python
from amrita_core.config import FunctionConfig

# 使用完整上下文（默认）
func_config_full = FunctionConfig(use_minimal_context=False)

# 使用最小上下文（更节省 token）
func_config_minimal = FunctionConfig(use_minimal_context=True)
```

### agent_mcp_client_enable — MCP 客户端配置

`agent_mcp_client_enable` 标志启用或禁用模型上下文协议（MCP）客户端功能：

```python
# 启用 MCP 客户端
func_config_mcp = FunctionConfig(
    agent_mcp_client_enable=True,
    agent_mcp_server_scripts=["script1.mcp", "script2.mcp"]
)
```

### tokenizer_used — 分词器选择

> **v0.9.0rc1 新增**：`FunctionConfig` 中的 `tokenizer_used` 字段选择用于 token 计数的分词器。

```python
from amrita_core.config import FunctionConfig

# 使用简单分词器（默认）
func_config = FunctionConfig(tokenizer_used="simple")

# 使用自定义注册的分词器
func_config = FunctionConfig(tokenizer_used="my_tokenizer")
```

分词器由 `TokenizerManager` 管理，可以通过 [BaseTokenizer](../../api-reference/classes/BaseTokenizer.md) 抽象类进行自定义。

## LLMConfig — 大语言模型配置

[LLMConfig](../api-reference/classes/LLMConfig.md) 类控制与语言模型的交互。

### enable_memory_abstract — 记忆抽象

`enable_memory_abstract` 属性启用对话历史的自动摘要，以管理 token 使用：

```python
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # 在达到 token 限制时摘要部分对话
)
```

### 其他模型参数

其他参数控制 token 使用量、超时和重试行为：

```python
llm_config = LLMConfig(
    max_tokens=100,                   # 响应中的最大 token 数
    llm_timeout=60,                   # 请求超时（秒）
    auto_retry=True,                  # 自动重试失败的请求
    max_retries=3,                    # 最大重试次数
    memory_length_limit=50            # 记忆上下文中消息的最大数量
)
```

## BuiltinAgentConfig — 内置 Agent 策略行为

### tool_calling_mode — 工具调用模式

`tool_calling_mode` 属性指定工具的调用方式：

- `"agent"`：智能体自主决定何时使用工具
- `"rag"`：工具主要用于检索增强生成（RAG），每个对话仅调用一次
- `"none"`：禁用工具

```python
# Agent 决定何时使用工具
func_config_agent = BuiltinAgentConfig(tool_calling_mode="agent")

# 主要用于 RAG 目的
func_config_rag = BuiltinAgentConfig(tool_calling_mode="rag")
```

### enable_builtin_agent — 内置 Agent

`enable_builtin_agent` 属性启用或禁用内置智能体实现：

```python
# 启用内置 Agent
config = BuiltinAgentConfig(enable_builtin_agent=True)

# 禁用内置 Agent，让用户提供自定义策略
config = BuiltinAgentConfig(enable_builtin_agent=False)
```
