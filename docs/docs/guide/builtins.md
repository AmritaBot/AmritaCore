# Built-in Capabilities of AmritaCore

## 9.1 Built-in Tools

AmritaCore provides several built-in tools to support core behaviors of intelligent agents. These tools are internally defined in the framework and automatically available when using agent strategies.

### 9.1.1 STOP_TOOL (Stop Tool)

`STOP_TOOL` is a built-in tool used to indicate that the agent has collected sufficient information and is ready to form the final answer. When this tool is called, the agent should not call any other tools but directly provide the completion.

- **Name**: `agent_stop`
- **Description**: Call this tool to indicate that you have gathered enough information and are ready to formulate the final answer to the user. After calling this, you should NOT call any other tools, but directly provide the completion.
- **Parameters**:
  - `result` (optional): Briefly explains what was accomplished during the chat task.

### 9.1.2 REASONING_TOOL (Reasoning Tool)

`REASONING_TOOL` is used to think about what should be done next, typically called after completing a tool call to reflect on the next steps. This tool is crucial for implementing autonomous decision-making in intelligent agents.

- **Name**: `think_and_reason`
- **Description**: Think about what you should do next, always call this tool to think when completing a tool call.
- **Parameters**:
  - `last_step`: The last step you took (if there are no steps that you had done, please leave this blank).
  - `summary`: What are you thinking about (not your detailed reasoning) - a brief summary of your current focus or intention.

### 9.1.3 PROCESS_MESSAGE (Process Message Tool)

`PROCESS_MESSAGE` is used to describe what the agent is currently doing and express the agent's internal thoughts to the user. Use this tool when you need to communicate current operations or internal reasoning to the user, not for general completion.

- **Name**: `processing_message`
- **Description**: Describe what the agent is currently doing and express the agent's internal thoughts to the user. Use this when you need to communicate your current actions or internal reasoning to the user, not for general completion.
- **Parameters**:
  - `content`: Message content, described in the tone of system instructions what is being done or how the user is being interacted with (required).

### 9.1.4 Built-in Tools Configuration

Built-in tools are automatically enabled based on the agent configuration:

- **Agent Mode**: When `config.builtin.tool_calling_mode == "agent"`, both `STOP_TOOL` and `REASONING_TOOL` are available.
- **Thought Mode**: The `REASONING_TOOL` is only available when `config.builtin.agent_thought_mode` starts with "reasoning".
- **Process Messages**: The `PROCESS_MESSAGE` tool is used internally by the `HybridReActAgentStrategy` to communicate intermediate tool results to the user. It is **not** registered by `ReActAgentStrategy`; the `config.function_config.agent_middle_message` flag controls whether the agent may send intermediate notifications, but does not independently enable the `PROCESS_MESSAGE` tool.

## 9.2 Built-in Metadata Types

> **Since v0.9.1**: A new `amrita_core.builtins.types` module provides typed metadata classes (based on `MessageMetadataPayload`) for structured metadata in agent and hook workflows.

These typed metadata classes replace plain dictionaries, providing type safety and IDE autocompletion:

| Class                                   | Purpose                                                                           |
| --------------------------------------- | --------------------------------------------------------------------------------- |
| `AgentReasoningMetadata`                | Pre-resolve reasoning summaries (`last_step`, `summary`)                          |
| `AgentReasoningChunkMetadata`           | Streaming reasoning chunks (`content`)                                            |
| `AgentToolCallMetadata`                 | Tool call notifications (`function_name`, `is_done`, `tool_id`, `err`)            |
| `AgentLoopErrorMetadata`                | Loop detection errors (`chat_object_id`, `error`)                                 |
| `AgentMiddleMessageMetadata`            | LLM middle messages (`content`)                                                   |
| `HookErrorMetadata`                     | Hook-level error responses (`content`)                                            |
| `AgentStructuredReasoningChunkMetadata` | Per-step structured CoT reasoning metadata (`step_index`, `total_steps`, `phase`) |
| `AgentReflectionMetadata`               | Post-reasoning self-reflection results (`reflection_type`, `result`, `detail`)    |
| `AgentToolPredictionMetadata`           | Tool prediction during structured reasoning (`predicted_tools`)                   |

Base classes in `amrita_core.contents`:

- `MessageMetadataPayload` — base typed dict (`type`, `extra_type`)
- `MessageMetadataPayloadError` — error payloads (`error`)
- `MessageMetadataPayloadSystem` — system payloads (`message`)

## 9.3 Built-in Adapters

> **Note**: Since v0.9.0rc1, adapters have been moved from `amrita_core.builtins.adapter` to the `amrita_core.adapters` package with an **auto-discovery** mechanism. Adapters are automatically discovered and registered when their source files are loaded.

AmritaCore provides built-in adapters for multiple LLM providers, implementing the `ModelAdapter` interface from `amrita_core.base.adapter`.

### 9.3.1 OpenAIAdapter

`OpenAIAdapter` is the primary model adapter that implements communication protocols with the OpenAI API and compatible endpoints.

**Features**:

- **API Calls**: Asynchronous calls to OpenAI-compatible APIs to get chat responses
- **Streaming Responses**: Supports streaming responses for real-time content output with usage statistics
- **Tool Calling**: Full support for OpenAI's function calling capabilities with proper tool choice handling
- **Usage Statistics**: Tracks API call usage information including token counts
- **Error Handling**: Robust error handling with configurable retry logic
- **Reasoning/Thinking**: Supports OpenAI o-series reasoning through `ThinkingConfig` (streaming and non-streaming)
- **Embedding API**: Provides `call_embed()` method for generating text embeddings (vector retrieval workflows)

**Supported Protocols**: `"openai"`, `"__main__"`

### 9.3.2 AnthropicAdapter

> **Optional Dependency**: Starting from v0.9.0rc1, the Anthropic SDK is an optional dependency. Install it with `pip install amrita_core[anthropic]`.

`AnthropicAdapter` provides full support for Anthropic's Claude models.

**Features**:

- **API Calls**: Asynchronous calls to the Anthropic API
- **Streaming Responses**: Supports streaming with message stream handling
- **Token Tracking**: Proper input/output token tracking for Anthropic's usage model
- **Message Filtering**: Automatically filters out invalid messages to comply with Anthropic API requirements
- **Tool Calling**: Full support for Anthropic's tool use capabilities with proper tool choice handling
- **Extended Thinking**: Supports Anthropic's extended thinking feature through `ThinkingConfig`, with thinking delta streaming and signature tracking for API round-tripping

**Supported Protocols**: `"anthropic"`, `"claude"`

**Graceful Degradation**: If the Anthropic SDK is not installed, the adapter logs an info message and is not registered, avoiding import errors.

## 9.4 Built-in Agent System

AmritaCore includes a comprehensive intelligent agent system capable of autonomously using tools to complete tasks. The system has been significantly enhanced with a **template method pattern** architecture that provides unified execution flow while allowing strategy-specific customization.

### 9.4.1 BaseReActAgentStrategy (Abstract Base Class)

`BaseReActAgentStrategy` is the abstract base class that implements the template method pattern for ReAct-style agents. It provides shared functionality including:

- **Tool calling orchestration** and execution flow control
- **Reasoning message generation** and processing
- **Loop detection and recovery mechanisms** (detects excessive duplicate reasoning calls)
- **Tool call notification handling** with configurable user notifications
- **Common error handling patterns** with proper exception management
- **Unified stop state management** via the `_suggested_stop` flag

This abstract class defines the common execution framework that all ReAct-style strategies inherit from, ensuring consistent behavior while allowing customization through abstract methods.

### 9.4.2 ReActAgentStrategy

The `ReActAgentStrategy` is the standard implementation that inherits from `BaseReActAgentStrategy` and implements the `"agent-mixed"` category, supporting both retrieval-augmented generation (RAG) and iterative tool calling within the same execution framework.

**Key Features**:

- **Dynamic Mode Switching**: Automatically adapts between RAG and agent modes based on configuration
- **Built-in Tool Integration**: Seamlessly integrates with all built-in tools (`STOP_TOOL`, `REASONING_TOOL`, `PROCESS_MESSAGE`)
- **Standard ToolCall-ToolResult Pairing**: Maintains strict adherence to OpenAI-compatible message formats
- **Reasoning Support**: Optional reasoning step generation before tool execution
- **Error Handling**: Comprehensive error handling with user notifications
- **Session Management**: Full session state management with memory retention

**Configuration Options**:

- **Tool Calling Mode**: Configurable via `config.builtin.tool_calling_mode` (`"agent"`, `"rag"`, `"none"`)
- **Thought Mode**: Configurable via `config.builtin.agent_thought_mode` (`"reasoning"`, `"reasoning-required"`, etc.)
- **Tool Call Limits**: Automatic prevention of infinite loops through call counting
- **Intermediate Messages**: Controls visibility of processing messages and reasoning steps
- **Error Notifications**: Configurable error reporting to users

### 9.4.3 HybridReActAgentStrategy

`HybridReActAgentStrategy` is a specialized agent strategy **optimized for Mixture of Experts (MoE) architecture models**. It addresses the ambiguity in internal state machines of certain MoE models when distinguishing between Tool and Completion identifiers.

**Key Characteristics**:

- **ToolCall Triggering**: Initiates tool execution through standard ToolCall mechanisms
- **Context-Based Integration**: Appends tool results as plain text messages rather than structured ToolResult objects, avoiding MoE model state ambiguity
- **XML Tag Format**: Uses `<TOOL_CALL>` and `<TOOL_RESULT>` XML tags to represent tool interactions
- **MoE-Specific Optimization**: Resolves issues where MoE models struggle to differentiate between tool invocation states and completion states

**Tool Function Schema**:

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

**Known Limitations and Security Considerations**:

- **Prompt Injection Risk**: Appending tool results as plain `user` messages may expose the model to injection attacks if tool outputs are untrusted or unsanitized
- **Minimal Sanitization**: This strategy only provides basic tag pair escaping and does **NOT** perform semantic-level filtering or content validation
- **Security Responsibility**: Users **MUST** implement comprehensive input validation, semantic analysis, and content sanitization for tool results in production environments

### 9.4.4 NoActionAgentStrategy

`NoActionAgentStrategy` is a simple workflow strategy that performs no action. It can be used to give up the tool calling process when needed.

- **Category**: `"workflow"`
- **Use Case**: When you need to skip tool execution entirely
- **Implementation**: Empty `run()` method that returns immediately

### 9.4.5 Agent Workflow and Template Method Pattern

The built-in agent system follows an enhanced workflow using the template method pattern:

1. **Initialization**: Strategy context is created with user input and conversation history
2. **Tool Preparation**: Available tools are determined based on configuration
3. **Reasoning Phase** (optional): If configured, reasoning step is generated
4. **Tool Execution Loop**:
   - Tools are called based on model decisions
   - Results are processed according to strategy-specific logic
   - Loop detection prevents infinite reasoning cycles
5. **Post-Processing**: The `on_post_process()` hook is called for final context modifications
6. **Completion**: Final response is generated

The template method pattern ensures that steps 1-4 and 6 follow a consistent flow across all strategies, while step 5 (result processing) and error handling are customized per strategy implementation.

### 9.4.6 Strategy Selection Guidelines

Choose the appropriate built-in strategy based on your use case:

- **Standard LLM Providers** (OpenAI, Anthropic, etc.): Use `ReActAgentStrategy`
- **MoE Architecture Models** (Mixtral, Qwen-MoE, etc.): Use `HybridReActAgentStrategy`
- **Skip Tool Execution**: Use `NoActionAgentStrategy`
- **Custom Behavior**: Extend `BaseReActAgentStrategy` or implement your own `AgentStrategy`

## 9.5 Built-in Event Hooks

AmritaCore provides built-in event hooks for common scenarios:

### 9.5.1 Cookie Security Hook

The cookie security hook automatically detects if sensitive cookie values appear in model responses and terminates the session to prevent data leakage.

- **Activation**: Enabled when `config.cookie.enable_cookie = True`
- **Detection**: Scans model responses for configured cookie values
- **Response**: Terminates session and returns generic error message on detection

### 9.5.2 Post-Process Hook

The `on_post_process()` hook is called after successful strategy execution and can be used for final context modifications or cleanup operations.

- **Timing**: Called after all tool executions complete successfully
- **Applicability**: Available for **all strategy categories** (`"agent"`, `"rag"`, `"workflow"`, `"agent-mixed"`)
- **Use Cases**: Adding final instructions, context summarization, or cleanup operations

## 9.6 Built-in Workflows (v0.12.6+)

AmritaCore ships pre-composed workflow pipelines in `amrita_core.builtins.workflows`. These are ready-to-use `NodeComposeRendered` graphs that can be passed to `ChatObject(workflow=...)` to replace the default execution pipeline.

### Available Workflows

| Workflow       | Description                                                                                                                 |
| -------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `REACT_BLOCK`  | ReAct loop block: `STRATEGY_INIT >> AGENT_ENTRY >> WHILE(SINGLE_STRATEGY_CALL).ACTION(REACT_COUNTER) >> AGENT_POST_PROCESS` |
| `SIMPLE_REACT` | Full ReAct pipeline: `LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> REACT_BLOCK >> LLM_COMPLETION >> COMMIT_MEMORY`       |
| `REACT_ONLY`   | ReAct pipeline without final LLM call: `LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> REACT_BLOCK`                        |
| `SIMPLE_CHAT`  | Plain chat (no agent): `LOAD_STATE >> JINJA2_RENDER >> BUILD_MESSAGE >> LLM_COMPLETION >> COMMIT_MEMORY`                    |

### Usage

```python
from amrita_core import ChatObject
from amrita_core.builtins.workflows import SIMPLE_REACT, SIMPLE_CHAT

# Full ReAct agent pipeline
chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="What is the weather today?",
    session_id="session_123",
    workflow=SIMPLE_REACT,
)

# Plain chat — no agent, no tool calling
chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Hello!",
    session_id="session_456",
    workflow=SIMPLE_CHAT,
)
```

> **Important**: `workflow` and `archived_nodes` are mutually exclusive — providing both raises `ValueError`. When neither is supplied, the built-in default pipeline is used.
