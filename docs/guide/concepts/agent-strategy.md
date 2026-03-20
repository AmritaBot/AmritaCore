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

### Unified Tool Interface

All agent strategies inherit the `call_tool()` method from the base `AgentStrategy` class. This provides a **unified interface for tool execution** that ensures consistency across all strategy implementations in AmritaCore.

Key characteristics of the unified tool interface:
- **Single-step execution**: Each call executes exactly one tool without modifying the agent's internal context
- **Consistent error handling**: Tools not found in the manager raise `RuntimeError`
- **Standardized response format**: Returns string responses or default messages for None returns
- **ToolContext integration**: Supports both simple function calls and advanced tool implementations with context access

This unified interface guarantees that regardless of which strategy category you implement, tool calling behavior remains consistent and predictable throughout the AmritaCore ecosystem.

## Implementation Guide

### Creating Custom Agent Strategies

To create a custom agent strategy, extend the `AgentStrategy` abstract base class and implement the required methods:

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
        
    @classmethod
    def get_category(cls) -> Literal["agent"]:
        return "agent"
```

### Using Built-in Strategies

AmritaCore provides the `AmritaAgentStrategy` as a built-in implementation that supports the `"agent-mixed"` category:

```python
from amrita_core import create_agent
from amrita_core.builtins.agent import AmritaAgentStrategy

# Create agent with custom strategy
agent = create_agent(
    url="https://api.example.com",
    key="your-api-key",
    strategy=AmritaAgentStrategy
)

# Use the agent
chat = agent.get_chatobject("What can you do?")
async with chat.begin():
    response = await chat.full_response()
```

## Strategy Context

The `StrategyContext` provides all necessary information for strategy execution:

- `user_input`: The original user input
- `original_context`: Complete message context including system message, memory, and user query
- `chat_object`: Reference to the chat object for yielding responses

## Best Practices

1. **Choose the Right Category**: Select the strategy category that best matches your use case
2. **Leverage Framework Features**: Use built-in features like tool calling limits, error handling, and response streaming
3. **Handle Errors Gracefully**: Implement proper error handling in your strategy methods
4. **Use Built-in Strategies When Possible**: Start with `AmritaAgentStrategy` before creating custom implementations
5. **Test Thoroughly**: Ensure your strategy handles edge cases and error conditions properly

## Example: Custom RAG Strategy

```python
from amrita_core.agent.strategy import AgentStrategy
from typing import Literal

class RAGStrategy(AgentStrategy):
    async def run(self) -> None:
        # Retrieve relevant documents based on user query
        documents = self.retrieve_documents(self.ctx.user_input)
        
        # Construct context with retrieved documents
        rag_context = f"Based on the following documents:\n{documents}\n\nUser query: {self.ctx.user_input}"
        
        # Update the message context
        self.ctx.original_context.train.content += f"\n\nRetrieved context: {rag_context}"
        
        # Let the framework handle the rest
        pass
        
    @classmethod
    def get_category(cls) -> Literal["rag"]:
        return "rag"
```