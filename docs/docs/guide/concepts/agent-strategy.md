# Agent Strategy

## Understanding Agent Strategy Architecture

AmritaCore implements a flexible Agent Strategy architecture that allows different execution patterns for AI agents. The core concept is the separation of agent behavior logic from the underlying execution framework, enabling developers to create custom agent behaviors while leveraging the robust infrastructure provided by AmritaCore.

### Strategy Categories

AmritaCore supports four distinct strategy categories, each designed for specific use cases:

#### 1. Agent Category (`"agent"`)

- **Execution Method**: `single_execute()`
- **Framework Control**: Full framework management of execution loop, call counting, and termination
- **Use Case**: Standard tool-calling agents that require framework-level control
- **Context**: Full conversation history with system message, memory, and user query

#### 2. RAG Category (`"rag"`)

- **Execution Method**: `run()`
- **Framework Control**: Minimal context only (system message + user query)
- **Use Case**: Retrieval-Augmented Generation scenarios where external knowledge retrieval is primary
- **Context**: Only system message and user query, no historical conversation context

#### 3. Workflow Category (`"workflow"`)

- **Execution Method**: `run()`
- **Framework Control**: Complete manual control over everything
- **Use Case**: Complex multi-step workflows with custom orchestration logic
- **Context**: Full conversation history with complete manual management

#### 4. Agent-Mixed Category (`"agent-mixed"`)

- **Execution Method**: `single_execute()`
- **Framework Control**: Framework-managed execution with dynamic mode switching
- **Use Case**: Agents that need to adapt between RAG and iterative tool calling based on context
- **Context**: Full conversation history with dynamic behavior adaptation

### Two Types of Strategies

AmritaCore supports **two complementary ways** to define agent strategies. Choose based on whether your strategy needs internal state.

#### Type 1: `type[AgentStrategy]` — Class-based Strategy

Pass a **class** to `ChatObject`. The framework instantiates a fresh copy for every request.

- ✅ Simple, stateless — write once, run everywhere
- ✅ Ideal for most common agent patterns (ReAct, RAG, etc.)
- ✅ No need to manage lifecycle — the framework handles it

```python
chat = ChatObject(
    ...,
    agent_strategy=ReActAgentStrategy,  # pass the class
)
```

#### Type 2: `StrategyLikedObject` — Instance-based Strategy

Pass a **pre-initialised instance**. The same object lives for the entire conversation, carrying its own state machine, resources, and configuration.

- ✅ Carries internal state across `single_execute()` / `run()` calls
- ✅ Pre-loads heavy resources (API clients, DB connections) once at creation
- ✅ Guarantees conversation isolation — each dialog gets its own instance
- ✅ Ideal for rate-limited, authenticated, or multi-step stateful workflows

```python
strategy = MyStatefulStrategy(api_key="sk-...", max_calls=5)
chat = ChatObject(
    ...,
    agent_strategy=strategy,  # pass the instance
)
```

> `ChatObject.agent_strategy` accepts **both** — `type[AgentStrategy]` OR `StrategyLikedObject` instance.

### Template Method Pattern Architecture

AmritaCore's agent strategy system has been enhanced with a **template method pattern** that provides a unified execution framework while allowing strategy-specific customization.

The `BaseReActAgentStrategy` abstract base class defines the common execution flow:

1. **Tool Call Generation**: Model generates tool calls based on current context
2. **Tool Execution Loop**: Each tool call is processed through a standardized flow
3. **Result Processing**: Strategy-specific logic handles how results are added to context
4. **Loop Detection**: Automatic detection and handling of reasoning loops
5. **Error Handling**: Common error patterns with strategy-specific recovery
6. **Post-Processing**: Optional `on_post_process()` hook for final modifications

This pattern ensures consistent behavior across all ReAct-style strategies while allowing customization through abstract methods like `_append_tool_result_to_context()` and `_handle_error_append()`.

### Unified Tool Interface

All agent strategies inherit the `call_tool()` method from the base `AgentStrategy` class. This provides a **unified interface for tool execution** that ensures consistency across all strategy implementations in AmritaCore.

Key characteristics of the unified tool interface:

- **Single-step execution**: Each call executes exactly one tool without modifying the agent's internal context
- **Consistent error handling**: Tools not found in the manager raise `RuntimeError`
- **Standardized response format**: Returns string responses or default messages for None returns
- **ToolContext integration**: Supports both simple function calls and advanced tool implementations with context access

This unified interface guarantees that regardless of which strategy category you implement, tool calling behavior remains consistent and predictable throughout the AmritaCore ecosystem.

### Built-in Strategy Implementations

#### ReActAgentStrategy

The standard implementation that follows OpenAI-compatible ToolCall-ToolResult pairing. It maintains strict message format compliance and is suitable for most LLM providers.

#### HybridReActAgentStrategy

A specialized implementation optimized for **Mixture of Experts (MoE) architecture models**. Instead of standard ToolCall-ToolResult pairs, it uses XML tags (`<TOOL_CALL>`, `<TOOL_RESULT>`) embedded directly in the conversation context as plain text messages.

This approach resolves state machine ambiguity issues in MoE models but requires careful security consideration due to potential prompt injection risks.

#### NoActionAgentStrategy

A minimal workflow strategy that performs no action, useful for skipping tool execution when needed.

## Implementation Guide

### Accessing DI Resources in Strategies (v0.12.6+)

Agent strategies extend `_StrategyBase` (via `AgentStrategy` or `StrategyLikedObject`), which provides **convenience properties** for accessing DI resources. Starting from v0.12.6, strategies should use these properties instead of reaching through `self.chat_object`.

**Available convenience properties:**

| Property                | Resolves from          | Fallback (if ctx field is None)         |
| ----------------------- | ---------------------- | --------------------------------------- |
| `self.preset`           | `ctx.preset`           | `self.chat_object.preset`               |
| `self.config`           | `ctx.config`           | `self.chat_object.config`               |
| `self.io_stream`        | `ctx.io_stream`        | `self.chat_object.io_stream`            |
| `self.train_content`    | `ctx.train_content`    | `self.chat_object.train.content`        |
| `self.stream_id`        | `ctx.stream_id`        | `self.chat_object.stream_id`            |
| `self.resp_extra_usage` | `ctx.resp_extra_usage` | `self.chat_object._di_resp.extra_usage` |

The `resp_extra_usage` property also supports a **setter**, allowing strategies to update usage tracking directly.

**Example — before (legacy):**

```python
class MyStrategy(AgentStrategy):
    async def single_execute(self) -> bool:
        preset = self.chat_object.preset          # reaches through ChatObject
        config = self.chat_object.config
        await self.chat_object.io_stream.yield_response(...)
        return True
```

**Example — after (v0.12.6+):**

```python
class MyStrategy(AgentStrategy):
    async def single_execute(self) -> bool:
        preset = self.preset                      # uses convenience property
        config = self.config
        await self.io_stream.yield_response(...)
        return True
```

> **How it works**: When `StrategyContext` DI fields are populated (either by `STRATEGY_INIT` node or by `_run_strategy`), the properties return them directly. Otherwise they fall back to `chat_object` for backward compatibility.

### Creating Custom Agent Strategies

To create a custom agent strategy, you have two options:

#### Option 1: Extend BaseReActAgentStrategy (Recommended for ReAct-style agents)

```python
from amrita_core.builtins.agent import BaseReActAgentStrategy
from typing import Literal

class MyCustomReActStrategy(BaseReActAgentStrategy):
    def __init__(self, ctx):
        super().__init__(ctx)
        # Initialize custom state

    async def _append_tool_result_to_context(self, tool_call, func_response, response_msg):
        # Implement how tool results are added to context
        pass

    async def _handle_error_append(self, function_name, error_content, tool_call_id, original_exception):
        # Implement error handling specific to your strategy
        pass

    async def _append_reasoning(self, response):
        # Implement reasoning step handling
        pass

    @classmethod
    def get_category(cls) -> Literal["agent-mixed"]:
        return "agent-mixed"
```

#### Option 2: Extend AgentStrategy directly (For completely custom behavior)

```python
from amrita_core.agent.strategy import AgentStrategy
from typing import Literal

class MyCustomAgentStrategy(AgentStrategy):
    def __init__(self, ctx):
        super().__init__(ctx)
        # Initialize custom state

    async def single_execute(self) -> bool:
        # Implement single step execution logic
        # Return True to continue, False to stop
        return True

    async def on_post_process(self) -> None:
        # Optional: Implement post-processing logic
        # Called after successful execution in agent/agent-mixed modes
        pass

    @classmethod
    def get_category(cls) -> Literal["agent"]:
        return "agent"
```

### Using Built-in Strategies

AmritaCore provides multiple built-in strategies for different use cases:

```python
import asyncio
from amrita_core import create_agent, minimal_init
from amrita_core.builtins.agent import (
    ReActAgentStrategy,
    HybridReActAgentStrategy,
    NoActionAgentStrategy
)

async def use_builtin_strategies():
    # Initialize AmritaCore
    await minimal_init()

    # Standard ReAct strategy (recommended for most cases)
    standard_agent = create_agent(
        base_url="https://api.openai.com",
        api_key="your-api-key",
        strategy=ReActAgentStrategy
    )

    # Hybrid strategy for MoE models
    hybrid_agent = create_agent(
        base_url="https://api.moemodel.com",
        api_key="your-api-key",
        strategy=HybridReActAgentStrategy
    )

    # No-action strategy to skip tool execution
    no_action_agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        strategy=NoActionAgentStrategy
    )

    # Use the agents
    chat = standard_agent.get_chatobject("What can you do?")

    chat.begin()
    async with chat:
        async for chunk in chat.io_stream.get_response_generator():
            content = chunk if isinstance(chunk, str) else chunk.get_content()
            print(content, end="", flush=True)
    # Chat is cleaned up automatically after exiting context
```

## Stateful Strategies with StrategyLikedObject

> **New in v0.9.0rc1**: `StrategyLikedObject` enables stateful agent strategies by passing pre-initialised instances instead of class types.

### Motivation

Standard `AgentStrategy` subclasses are instantiated by the framework for each request. This works well for stateless strategies but limits:

- **State machines**: Strategies that need to track state across calls
- **Pre-configured resources**: Strategies with pre-loaded API clients, database connections, or model instances
- **Conversation isolation**: Guaranteeing each conversation gets its own strategy instance with independent state

`StrategyLikedObject` solves these by allowing you to pass an **already-initialised instance** directly to `ChatObject`.

### Comparison: AgentStrategy vs StrategyLikedObject

| Aspect           | `AgentStrategy`              | `StrategyLikedObject`          |
| ---------------- | ---------------------------- | ------------------------------ |
| Passed as        | Class (`type`)               | Instance                       |
| Instantiation    | By framework per request     | By user, once                  |
| Stateful         | No (new instance each time)  | Yes (same instance throughout) |
| Resource loading | On every request             | Once, at creation              |
| Use case         | Stateless, simple strategies | Complex, stateful workflows    |

### Usage

```python
from amrita_core.agent.strategy import StrategyLikedObject
from amrita_core.agent.context import StrategyContext

class RateLimitedStrategy(StrategyLikedObject):
    def __init__(self, max_calls: int, api_key: str):
        self.max_calls = max_calls
        self.call_count = 0
        self.api_key = api_key
        self.client = MyAPIClient(api_key)  # Pre-loaded resource

    @classmethod
    def get_category(cls) -> str:
        return "agent"

    async def single_execute(self) -> bool:
        self.call_count += 1
        if self.call_count > self.max_calls:
            return False  # Stop
        # Use self.client for API calls...
        return True

    async def on_limited(self) -> None:
        await self.chat_object.yield_response(
            "I've reached my call limit for this conversation."
        )

# Pass an instance — not a class
strategy = RateLimitedStrategy(max_calls=5, api_key="sk-...")
chat_obj = ChatObject(
    train={"system": "You are a helpful assistant"},
    user_input="Hello",
    context=None,
    session_id="session_123",
    agent_strategy=strategy,  # Instance!
)
```

### Lifecycle

1. **Creation**: User instantiates `StrategyLikedObject` with custom parameters
2. **Registration**: Instance is passed to `ChatObject(agent_strategy=instance)`
3. **Initialisation**: Framework calls `strategy(ctx)` once context is ready
4. **Execution**: Same instance handles all `single_execute()` / `run()` calls
5. **Cleanup**: Instance is discarded when the conversation ends

### When to Use

- **Rate limiting**: Track per-conversation tool call counts
- **Authenticated clients**: Pre-initialise API clients with session tokens
- **Multi-step workflows**: Maintain state across workflow stages
- **Resource pooling**: Share connection pools across strategy instances

## Post-Process Hook

The `on_post_process()` method is a lifecycle hook that is called after all agent steps complete successfully. This hook is invoked for **all strategy categories** (`"agent"`, `"rag"`, `"workflow"`, `"agent-mixed"`) and can be used for:

- Adding final instructions to the context
- Context summarization or cleanup
- Final validation before completion

```python
async def on_post_process(self) -> None:
    """Called after successful agent execution"""
    if self.call_count >= 2:  # Only if tools were actually called
        self.ctx.message.append(
            Message(
                role="user",
                content="<END_OF_PROCESS>\nPlease answer me directly based on the information we got before.\n<END_OF_PROCESS>"
            )
        )
```
