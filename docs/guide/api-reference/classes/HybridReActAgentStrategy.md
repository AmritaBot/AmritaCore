# HybridReActAgentStrategy

`HybridReActAgentStrategy` is a specialized agent strategy **optimized for Mixture of Experts (MoE) architecture models**.

This strategy addresses the ambiguity in internal state machines of certain MoE models when distinguishing between Tool and Completion identifiers. Unlike traditional toolchain approaches that rely on explicit ToolCall-ToolResult interactions, this hybrid approach uses ToolCall triggering combined with appending pure text directly to the context.

## Inheritance

- Extends: [BaseReActAgentStrategy](BaseReActAgentStrategy.md)
- Category: `"agent-mixed"`

## Key Characteristics

- **ToolCall Triggering**: Initiates tool execution through standard ToolCall mechanisms
- **Context-Based Integration**: Appends tool results as plain text messages rather than structured ToolResult objects
- **XML Tag Format**: Uses `<TOOL_CALL>` and `<TOOL_RESULT>` XML tags to represent tool interactions
- **MoE-Specific Optimization**: Resolves issues where MoE models struggle to differentiate between tool invocation states and completion states

## Properties

- `regexes` (ClassVar[list[tuple[re.Pattern, str]]]): Regular expressions for XML tag sanitization
- `_tool_call_jinja2` ([Template](https://jinja.palletsprojects.com/)): Jinja2 template for rendering tool calls and results
- `_process_message` (list[str]): Temporary storage for processed tool messages

## Constructor Parameters

- `ctx` ([StrategyContext](StrategyContext.md)): Strategy context containing chat_object, configuration, and message context

## Tool Function Schema

```xml
<!-- Tool Call -->
<TOOL_CALL name="tool">
    <PARAMS>
        <!-- Parameters are passed as key-value pairs -->
        <PARAM name="param1">value1</PARAM>
    </PARAMS>
</TOOL_CALL>

<!-- Tool Result -->
<TOOL_RESULT name="tool">
   Tool execution result content
</TOOL_RESULT>
```

## Security Considerations

**⚠️ Important Security Warning**:

- **Prompt Injection Risk**: Appending tool results as plain `user` messages may expose the model to injection attacks if tool outputs are untrusted or unsanitized
- **Minimal Sanitization**: This strategy only provides basic tag pair escaping and does **NOT** perform semantic-level filtering or content validation
- **Security Responsibility**: Users **MUST** implement comprehensive input validation, semantic analysis, and content sanitization for tool results in production environments

## Usage Example

```python
import asyncio
from amrita_core import create_agent, minimal_init
from amrita_core.builtins.agent import HybridReActAgentStrategy

async def use_hybrid_strategy():
    # Initialize AmritaCore
    await minimal_init()

    # Create agent with hybrid strategy for MoE models
    agent = create_agent(
        url="https://api.moemodel.com",
        key="your-api-key",
        strategy=HybridReActAgentStrategy
    )

    # Use the agent
    chat = agent.get_chatobject("Analyze this data using available tools")
    async with chat.begin():
        response = await chat.full_response()
```

## When to Use

Use `HybridReActAgentStrategy` when working with:

- **Mixture of Experts (MoE) models** like Mixtral, Qwen-MoE, etc.
- Models that exhibit inconsistent behavior with standard ToolCall-ToolResult message pairs
- Scenarios where the model's internal state machine has difficulty distinguishing between tool invocation and completion states

## When NOT to Use

Avoid `HybridReActAgentStrategy` when:

- Working with standard LLM providers (OpenAI, Anthropic, etc.) - use [ReActAgentStrategy](ReActAgentStrategy.md) instead
- Security is a primary concern and you cannot implement proper input validation
- You need strict OpenAI-compatible message formatting
