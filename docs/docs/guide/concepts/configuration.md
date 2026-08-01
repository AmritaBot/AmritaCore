# Configuration System

AmritaCore's behavior is controlled through a central configuration object that combines three distinct configuration classes. This page explains what each one does and when to use it.

## AmritaConfig — Overall Configuration

The [AmritaConfig](../api-reference/classes/AmritaConfig.md) class serves as the central configuration object for AmritaCore. It combines three distinct configuration classes:

- `FunctionConfig`: Defines behavioral aspects of the Agent
- `LLMConfig`: Controls language model interactions
- `CookieConfig`: Handles security aspects
- `BuiltinAgentConfig`: Policy control for built-in Agents

```python
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig, CookieConfig, BuiltinAgentConfig

# Complete configuration
config = AmritaConfig(
    function_config=FunctionConfig(...),
    llm=LLMConfig(...),
    cookie=CookieConfig(...),
    builtin=BuiltinAgentConfig(...),
)

# Apply configuration
from amrita_core.config import set_config
set_config(config)
```

## FunctionConfig — Feature Configuration

The [FunctionConfig](../api-reference/classes/FunctionConfig.md) class controls the main functional behaviors of AmritaCore.

### use_minimal_context — Context Mode

The `use_minimal_context` flag determines whether to use minimal context (system prompt + user's last message) or complete conversation history:

```python
from amrita_core.config import FunctionConfig

# Use full context (default)
func_config_full = FunctionConfig(use_minimal_context=False)

# Use minimal context (more token-efficient)
func_config_minimal = FunctionConfig(use_minimal_context=True)
```

### agent_mcp_client_enable — MCP Client Configuration

The `agent_mcp_client_enable` flag enables or disables the Model Context Protocol (MCP) client functionality:

```python
# Enable MCP client
func_config_mcp = FunctionConfig(
    agent_mcp_client_enable=True,
    agent_mcp_server_scripts=["script1.mcp", "script2.mcp"]
)
```

### tokenizer_used — Tokenizer Selection

> **New in v0.9.0rc1**: The `tokenizer_used` field in `FunctionConfig` selects which tokenizer to use for token counting.

```python
from amrita_core.config import FunctionConfig

# Use the simple tokenizer (default)
func_config = FunctionConfig(tokenizer_used="simple")

# Use a custom registered tokenizer
func_config = FunctionConfig(tokenizer_used="my_tokenizer")
```

Tokenizers are managed by the `TokenizerManager` and can be customised via the [BaseTokenizer](../../api-reference/classes/BaseTokenizer.md) abstract class.

## LLMConfig — Large Language Model Configuration

The [LLMConfig](../api-reference/classes/LLMConfig.md) class controls interactions with language models.

### enable_memory_abstract — Memory Abstraction

The `enable_memory_abstract` property enables automatic summarization of conversation history to manage token usage:

```python
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # Summarize a portion of the conversation when reaching the token limit.
)
```

### Other Model Parameters

Additional parameters control token usage, timeouts, and retry behavior:

```python
llm_config = LLMConfig(
    max_tokens=100,                   # Maximum number of tokens in response
    llm_timeout=60,                   # Request timeout (seconds)
    auto_retry=True,                  # Automatically retry failed requests
    max_retries=3,                    # Maximum number of retries
    memory_length_limit=50            # Maximum number of messages in memory context
)
```

## BuiltinAgentConfig — Built-in Agent Policy Behavior

### tool_calling_mode — Tool Calling Mode

The `tool_calling_mode` property specifies how tools are invoked:

- `"agent"`: The Agent autonomously decides when to use tools
- `"rag"`: Tools are primarily used for Retrieval-Augmented Generation (RAG), invoked only once per conversation
- `"none"`: Tools are disabled

```python
# Agent decides when to use tools
func_config_agent = BuiltinAgentConfig(tool_calling_mode="agent")

# Primarily for RAG purposes
func_config_rag = BuiltinAgentConfig(tool_calling_mode="rag")
```

### agent_thought_mode — Agent Thinking Mode

The `agent_thought_mode` property controls how the Agent processes information:

- `"reasoning"`: Performs reasoning at the start of each user message
- `"chat"`: Executes tasks directly without explicit reasoning
- `"reasoning-required"`: Reasoning is required for each tool invocation
- `"reasoning-optional"`: Reasoning is allowed but not required

```python
# Reasoning mode
func_config_reasoning = BuiltinAgentConfig(agent_thought_mode="reasoning")

# Direct chat mode
func_config_chat = BuiltinAgentConfig(agent_thought_mode="chat")
```

## CookieConfig — Security Configuration

The [CookieConfig](../api-reference/classes/CookieConfig.md) class handles security-related settings:

```python
from amrita_core.config import CookieConfig

security_config = CookieConfig(
    enable_cookie=True,               # Enable cookie leakage detection
    cookie="random_cookie_string"     # Cookie string used for security detection
)
```

## BuiltinName — Internal Aliases

> **New in v0.9.0rc1**: `BuiltinName` provides symbolic aliases used by the [workflow engine](../advanced/workflow-engine.md).

```python
from amrita_core.chatmanager import BuiltinName

BuiltinName.AGENT_STRATEGY  # "ChatObject::__agent_main__"
```

These aliases enable the workflow interpreter to locate and invoke specific nodes by name, supporting the composable workflow architecture.

## Configuration Best Practices

- Use minimal context for simple queries to save tokens
- Enable memory abstraction for long conversations
- Adjust timeout and retry settings according to your LLM provider
- Keep security features enabled in production environments
