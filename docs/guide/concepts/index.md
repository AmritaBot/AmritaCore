# Core Concepts

## Configuration System

### 3.1.1 AmritaConfig Overall Configuration

The [AmritaConfig](../api-reference/classes/AmritaConfig.md) class serves as the central configuration object for AmritaCore. It combines three distinct configuration classes:

- `FunctionConfig`: Defines behavioral aspects of the agent
- `LLMConfig`: Controls language model interactions
- `CookieConfig`: Handles security aspects

```python
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig, CookieConfig

# Complete configuration
config = AmritaConfig(
    function_config=FunctionConfig(...),
    llm=LLMConfig(...),
    cookie=CookieConfig(...)
)

# Apply configuration
from amrita_core.config import set_config
set_config(config)
```

### 3.1.2 FunctionConfig Function Configuration

The [FunctionConfig](../api-reference/classes/FunctionConfig.md) class controls how the agent behaves functionally:

#### 3.1.2.1 use_minimal_context Context Mode

The `use_minimal_context` flag determines whether to use a minimal context (system prompt + user's last message) or the full conversation history:

```python
from amrita_core.config import FunctionConfig

# Using full context (default)
func_config_full = FunctionConfig(use_minimal_context=False)

# Using minimal context (more token-efficient)
func_config_minimal = FunctionConfig(use_minimal_context=True)
```

#### 3.1.2.2 tool_calling_mode Tool Calling Mode

The `tool_calling_mode` property specifies how tools are invoked:

- `"agent"`: The agent autonomously decides when to use tools
- `"rag"`: Tools are used primarily for Retrieval-Augmented Generation, only call one time in a conversation.
- `"none"`: Tools are disabled

```python
# Agent decides when to use tools
func_config_agent = FunctionConfig(tool_calling_mode="agent")

# Primarily for RAG purposes
func_config_rag = FunctionConfig(tool_calling_mode="rag")
```

#### 3.1.2.3 agent_thought_mode Agent Thinking Mode

The `agent_thought_mode` property controls how the agent processes information:

- `"reasoning"`: Performs reasoning on each start of a user message
- `"chat"`: Directly executes tasks without explicit reasoning
- `"reasoning-required"`: Requires reasoning for each tool call
- `"reasoning-optional"`: Allows reasoning but doesn't require it

```python
# Reasoning mode
func_config_reasoning = FunctionConfig(agent_thought_mode="reasoning")

# Direct chat mode
func_config_chat = FunctionConfig(agent_thought_mode="chat")
```

#### 3.1.2.4 agent_mcp_client_enable MCP Client Configuration

The `agent_mcp_client_enable` flag enables or disables the Model Context Protocol (MCP) client functionality:

```python
# Enable MCP client
func_config_mcp = FunctionConfig(
    agent_mcp_client_enable=True,
    agent_mcp_server_scripts=["script1.mcp", "script2.mcp"]
)
```

### 3.1.3 LLMConfig Large Model Configuration

The [LLMConfig](../api-reference/classes/LLMConfig.md) class controls interactions with the language model:

#### 3.1.3.1 enable_memory_abstract Memory Abstraction

The `enable_memory_abstract` property enables automatic summarization of conversation history to manage token usage:

```python
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # Summarize at 15% of context length
)
```

#### 3.1.3.2 Other Model Parameters

Additional parameters control token usage, timeouts, and retry behavior:

```python
llm_config = LLMConfig(
    max_tokens=100,                   # Maximum tokens in response
    llm_timeout=60,                   # Request timeout in seconds
    auto_retry=True,                  # Automatically retry failed requests
    max_retries=3,                    # Maximum number of retries
    memory_length_limit=50            # Max messages in memory context
)
```

### 3.1.4 CookieConfig Security Configuration

The [CookieConfig](../api-reference/classes/CookieConfig.md) class handles security-related settings:

```python
from amrita_core.config import CookieConfig

security_config = CookieConfig(
    enable_cookie=True,               # Enable cookie leak detection
    cookie="random_cookie_string"     # Cookie string for security detection
)
```

### 3.1.5 Configuration Best Practices

- Use minimal context for simple queries to save tokens
- Enable memory abstraction for long conversations
- Adjust timeout and retry settings based on your LLM provider
- Keep security features enabled in production environments

## 3.5 Advanced Concepts

### 3.5.1 ChatObject Conversation Object

The [ChatObject](../api-reference/classes/ChatObject.md) is the core class for managing individual conversations:

```python
import asyncio
from amrita_core import ChatObject



chat = ChatObject(
    context=memory_model,      # Memory context
    session_id="session_123",  # Unique session identifier
    user_input="Hello!",       # User's input
    train=system_prompt        # System instructions
)

async def msg_getter(chatobj: ChatObject) -> None:
    async for message in chatobj.get_response_generator():
        print(message if isinstance(message, str) else message.get_content(), end="")
    print("\n")

async with chat.begin():
    await msg_getter(chat)

```

### 3.5.2 PresetManager Preset Manager

The [PresetManager](../api-reference/classes/PresetManager.md) manages model presets:

```python
from amrita_core.preset import PresetManager, ModelPreset

preset_manager = PresetManager()

# Add a preset
preset = ModelPreset(...)
preset_manager.add_preset(preset)
preset_manager.set_default_preset(preser.name)

# Get available presets
presets = preset_manager.get_presets()
```

### 3.5.3 Streaming Processing Design

AmritaCore uses streaming for all responses to provide real-time feedback:

```python
# Responses come as an async generator
async for chunk in chat.get_response_generator():
    # Process each chunk in real-time
    print(chunk, end="")
```

### 3.5.4 Response Callback

AmritaCore provides a callback mechanism for handling responses:

```python
async def callback(chunk):
    print(chunk, end="")
chat.set_callback_func(callback)
await chat.begin()
```

### 3.5.5 Memory Summary Mechanism

The memory summary mechanism automatically condenses conversation history to manage token usage:

```python
# Configured via LLMConfig
llm_config = LLMConfig(
    enable_memory_abstract=True,
    memory_abstract_proportion=0.15  # Summarize when 15% of context is reached
)
```
