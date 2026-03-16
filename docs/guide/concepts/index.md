# Core Concepts

## Configuration System

### 3.1.1 AmritaConfig Overall Configuration

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

### 3.1.2 FunctionConfig Feature Configuration

The [FunctionConfig](../api-reference/classes/FunctionConfig.md) class controls the main functional behaviors of AmritaCore:

#### 3.1.2.1 use_minimal_context Context Mode

The `use_minimal_context` flag determines whether to use minimal context (system prompt + user's last message) or complete conversation history:

```python
from amrita_core.config import FunctionConfig

# Use full context (default)
func_config_full = FunctionConfig(use_minimal_context=False)

# Use minimal context (more token-efficient)
func_config_minimal = FunctionConfig(use_minimal_context=True)
```

#### 3.1.2.2 agent_mcp_client_enable MCP Client Configuration

The `agent_mcp_client_enable` flag enables or disables the Model Context Protocol (MCP) client functionality:

```python
# Enable MCP client
func_config_mcp = FunctionConfig(
    agent_mcp_client_enable=True,
    agent_mcp_server_scripts=["script1.mcp", "script2.mcp"]
)
```

### 3.1.3 LLMConfig Large Language Model Configuration

The [LLMConfig](../api-reference/classes/LLMConfig.md) class controls interactions with language models:

#### 3.1.3.1 enable_memory_abstract Memory Abstraction

The `enable_memory_abstract` property enables automatic summarization of conversation history to manage token usage:

```python
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # Summarize when reaching 15% of context length
)
```

#### 3.1.3.2 Other Model Parameters

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

### 3.1.4 BuiltinAgentConfig Built-in Agent Policy Behavior Adjustment

#### 3.1.4.2 tool_calling_mode Tool Calling Mode

The `tool_calling_mode` property specifies how tools are invoked:

- `"agent`: The Agent autonomously decides when to use tools
- `"rag`: Tools are primarily used for Retrieval-Augmented Generation (RAG), invoked only once per conversation
- `"none`: Tools are disabled

```python
# Agent decides when to use tools
func_config_agent = BuiltinAgentConfig(tool_calling_mode="agent")

# Primarily for RAG purposes
func_config_rag = BuiltinAgentConfig(tool_calling_mode="rag")
```

#### 3.1.4.3 agent_thought_mode Agent Thinking Mode

The `agent_thought_mode` property controls how the Agent processes information:

- `"reasoning`: Performs reasoning at the start of each user message
- `"chat`: Executes tasks directly without explicit reasoning
- `"reasoning-required`: Reasoning is required for each tool invocation
- `"reasoning-optional`: Reasoning is allowed but not required

```python
# Reasoning mode
func_config_reasoning = BuiltinAgentConfig(agent_thought_mode="reasoning")

# Direct chat mode
func_config_chat = BuiltinAgentConfig(agent_thought_mode="chat")
```

### 3.1.5 CookieConfig Security Configuration

The [CookieConfig](../api-reference/classes/CookieConfig.md) class handles security-related settings:

```python
from amrita_core.config import CookieConfig

security_config = CookieConfig(
    enable_cookie=True,               # Enable cookie leakage detection
    cookie="random_cookie_string"     # Cookie string used for security detection
)
```

### 3.1.6 Configuration Best Practices

- Use minimal context for simple queries to save tokens
- Enable memory abstraction for long conversations
- Adjust timeout and retry settings according to your LLM provider
- Keep security features enabled in production environments

## 3.5 Advanced Concepts

### 3.5.1 ChatObject Conversation Object

[ChatObject](../api-reference/classes/ChatObject.md) is the core class for managing individual conversations:

```python
import asyncio
from amrita_core import ChatObject

chat = ChatObject(
    context=memory_model,      # Memory context
    session_id="session_123",  # Unique session identifier
    user_input="Hello!",       # User input
    train=system_prompt        # System prompt
)

async def msg_getter(chatobj: ChatObject) -> None:
    async for message in chatobj.get_response_generator():
        print(message if isinstance(message, str) else message.get_content(), end="")
    print("\n")

async with chat.begin():
    await msg_getter(chat)
```

### 3.5.2 PresetManager Preset Manager

[PresetManager](../api-reference/classes/PresetManager.md) manages model presets:

```python
from amrita_core.preset import PresetManager, ModelPreset

preset_manager = PresetManager()

# Add preset
preset = ModelPreset(...)
preset_manager.add_preset(preset)
preset_manager.set_default_preset(preset.name)

# Get available presets
presets = preset_manager.get_presets()
```

### 3.5.3 Stream Processing Design

AmritaCore uses streaming for all responses to provide real-time feedback:

```python
# Responses are returned as asynchronous generators
async for chunk in chat.get_response_generator():
    # Process each chunk in real-time
    print(chunk, end="")
```

### 3.5.4 Callback-based Responses

AmritaCore supports callback-based responses:

```python
async def callback(chunk):
    print(chunk, end="")

chat.set_callback_func(callback)
await chat.begin()
```

### 3.5.5 Memory Summarization Mechanism

The memory summarization mechanism automatically compresses conversation history to manage token usage:

```python
# Configured via LLMConfig
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # Summarize when reaching 15% of context length
)
```
