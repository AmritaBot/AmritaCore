# AgentStrategy

The AgentStrategy abstract base class defines how an agent should execute its workflow.

This class provides a unified interface for different types of agent execution strategies, allowing the system to support various agent patterns (basic tool calling, RAG, complex workflows).

## Strategy Categories

Different strategy categories have different execution patterns:

- **'agent'**: Uses `single_execute()` method for step-by-step tool calling, managed by the framework
- **'rag'**: Uses `run()` method with minimal context (only system message and user query)
- **'workflow'**: Uses `run()` method with full manual control over tool calling and context management
- **'agent-mixed'**: Uses `single_execute()` method but can handle both RAG and Agent modes dynamically

## Properties

- `session` (SessionData | None): The session data associated with the current chat session, or None if not available
- `tools_manager` (MultiToolsManager): Manager for handling available tools in the current context
- `chat_object` (ChatObject): The chat object for yielding responses and managing the conversation flow
- `ctx` (StrategyContext): The strategy context containing execution parameters and configuration

## Constructor Parameters

- `ctx` ([StrategyContext](StrategyContext.md)): Strategy context containing chat_object, configuration, and message context

## Abstract Methods

### get_category()

Get the category of the agent strategy.

**Returns**: Literal["agent", "workflow", "rag", "agent-mixed"] - The strategy category as a literal string indicating execution pattern.

## Methods

### single_execute()

Execute a single agent step for 'agent' and 'agent-mixed' category strategies.

This method is called by the framework to perform one iteration of tool calling. The framework handles the loop management, call counting, and termination conditions.

**Returns**: bool - True if should continue to next execution, False to stop.

**Note**: This method is used by 'agent' and 'agent-mixed' category strategies. 'rag' and 'workflow' category strategies should implement `run()` instead.

### run()

Run the complete agent strategy for 'rag' and 'workflow' category strategies.

This method gives full control to the strategy implementation for managing tool calling iterations, context construction, error handling, and response generation.

**Note**: This method is used by 'rag' and 'workflow' category strategies. 'agent' and 'agent-mixed' category strategies should implement `single_execute()` instead.

### on_limited()

Handle the event when the agent reaches its tool calling limit.

This method is called when the agent strategy has reached the maximum allowed number of tool calls as configured by the framework.

### on_exception(exc)

Handle exceptions that occur during strategy execution.

**Parameters**:
- `exc` (BaseException): The exception that occurred during execution