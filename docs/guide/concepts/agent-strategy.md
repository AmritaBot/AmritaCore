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
        url="https://api.openai.com",
        key="your-api-key",
        strategy=ReActAgentStrategy
    )

    # Hybrid strategy for MoE models
    hybrid_agent = create_agent(
        url="https://api.moemodel.com",
        key="your-api-key",
        strategy=HybridReActAgentStrategy
    )

    # No-action strategy to skip tool execution
    no_action_agent = create_agent(
        url="https://api.example.com",
        key="your-api-key",
        strategy=NoActionAgentStrategy
    )

    # Use the agents
    chat1 = standard_agent.get_chatobject("What can you do?")
    chat2 = hybrid_agent.get_chatobject("Analyze this data")
    chat3 = no_action_agent.get_chatobject("Just respond directly")

    async with chat1.begin(), chat2.begin(), chat3.begin():
        response1 = await chat1.full_response()
        response2 = await chat2.full_response()
        response3 = await chat3.full_response()
```

### Post-Process Hook

The `on_post_process()` method is a new lifecycle hook that is called after all agent steps complete successfully. This hook is invoked for **all strategy categories** (`"agent"`, `"rag"`, `"workflow"`, `"agent-mixed"`) and can be used for:

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
