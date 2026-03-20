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
  - `content`: Describe what needs to be done next (required).

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
- **Process Messages**: The `PROCESS_MESSAGE` tool is enabled when `config.function_config.agent_middle_message` is True.

## 9.2 Built-in Adapters

AmritaCore provides built-in adapters for multiple LLM providers, implementing the `ModelAdapter` interface.

### 9.2.1 OpenAIAdapter

`OpenAIAdapter` is the primary model adapter that implements communication protocols with the OpenAI API and compatible endpoints.

**Features**:

- **API Calls**: Asynchronous calls to OpenAI-compatible APIs to get chat responses
- **Streaming Responses**: Supports streaming responses for real-time content output with usage statistics
- **Tool Calling**: Full support for OpenAI's function calling capabilities with proper tool choice handling
- **Usage Statistics**: Tracks API call usage information including token counts
- **Error Handling**: Robust error handling with configurable retry logic

**Supported Protocols**: `"openai"`, `"__main__"`

### 9.2.2 AnthropicAdapter (Experimental)

`AnthropicAdapter` provides experimental support for Anthropic's Claude models.

**Features**:

- **API Calls**: Asynchronous calls to the Anthropic API
- **Streaming Responses**: Supports streaming with message stream handling
- **Token Tracking**: Proper input/output token tracking for Anthropic's usage model

**Supported Protocols**: `"anthropic"`, `"claude"`

**Note**: This adapter is experimental and may have limited functionality compared to the OpenAI adapter.

## 9.3 Built-in Agent System

AmritaCore includes a comprehensive intelligent agent system capable of autonomously using tools to complete tasks.

### 9.3.1 AmritaAgentStrategy

The `AmritaAgentStrategy` is the built-in agent strategy that implements the `"agent-mixed"` category, supporting both retrieval-augmented generation (RAG) and iterative tool calling within the same execution framework.

**Key Features**:

- **Dynamic Mode Switching**: Automatically adapts between RAG and agent modes based on configuration
- **Built-in Tool Integration**: Seamlessly integrates with all built-in tools (`STOP_TOOL`, `REASONING_TOOL`, `PROCESS_MESSAGE`)
- **Reasoning Support**: Optional reasoning step generation before tool execution
- **Error Handling**: Comprehensive error handling with user notifications
- **Session Management**: Full session state management with memory retention

**Configuration Options**:

- **Tool Calling Mode**: Configurable via `config.builtin.tool_calling_mode` (`"agent"`, `"rag"`, `"none"`)
- **Thought Mode**: Configurable via `config.builtin.agent_thought_mode` (`"reasoning"`, `"reasoning-required"`, etc.)
- **Tool Call Limits**: Automatic prevention of infinite loops through call counting
- **Intermediate Messages**: Controls visibility of processing messages and reasoning steps
- **Error Notifications**: Configurable error reporting to users

### 9.3.2 Agent Workflow

The built-in agent system follows this enhanced workflow:

1. **Initialization**: Create agent with `create_agent()` or `AgentRuntime`
2. **Context Setup**: Initialize conversation context with system prompt and memory
3. **Mode Detection**: Determine execution mode (RAG vs Agent) based on configuration
4. **Reasoning Phase** (Optional): Generate reasoning step if thought mode is enabled
5. **Tool Selection**: Select appropriate tools based on current situation and available tools
6. **Tool Execution**: Execute selected tools with proper error handling
7. **Result Processing**: Process tool results and update conversation context
8. **Iteration Control**: Manage iteration limits and termination conditions
9. **Completion**: Use `STOP_TOOL` to end the task or provide final response

### 9.3.3 Core API Functions

AmritaCore provides high-level factory functions for simplified agent creation:

#### create_agent()

A factory function that creates an `AgentRuntime` instance with minimal parameters:

```python
from amrita_core import create_agent, minimal_init

async def example():
    await minimal_init()
    agent = create_agent(
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-4",
        model_config={"temperature": 0.7}
    )
    chat = agent.get_chatobject("What can you do?")
    async with chat.begin():
        response = await chat.full_response()
    return response
```

**Parameters**:

- `base_url`: API endpoint URL
- `api_key`: Authentication API key
- `model`: Model name (defaults to "auto")
- `train`: Custom system prompt (optional)
- `model_config`: Model configuration parameters
- `config`: Amrita configuration object (optional)

#### AgentRuntime

The underlying runtime class that provides full control over agent configuration:

```python
from amrita_core import AgentRuntime, minimal_init
from amrita_core.config import get_config
from amrita_core.types import ModelPreset, ModelConfig

async def advanced_example():
    await minimal_init()
    config = get_config()
    preset = ModelPreset(
        name="custom_preset",
        base_url="https://api.example.com",
        api_key="your-api-key",
        model="gpt-4",
        config=ModelConfig(temperature=0.7, stream=True)
    )

    agent = AgentRuntime(
        config=config,
        preset=preset,
        train={"content": "You are a helpful assistant.", "role": "system"}
    )

    chat = agent.get_chatobject("Hello!")
    async with chat.begin():
        async for chunk in chat.get_response_generator():
            print(chunk, end="")
```

## 9.4 Built-in Security Features

### 9.4.1 Cookie Security Detection

AmritaCore includes built-in cookie security detection to prevent prompt injection attacks:

- **Automatic Cookie Generation**: Unique cookies are automatically generated for each session
- **Leakage Detection**: Monitors responses for cookie presence indicating potential injection
- **Automatic Response Blocking**: Blocks responses containing cookies and returns error messages

### 9.4.2 Session Isolation

Built-in session management ensures complete isolation between different users or conversations:

- **SessionsManager**: Singleton class managing session lifecycle
- **SessionData**: Per-session configuration, tools, and memory
- **Automatic Cleanup**: Sessions are automatically cleaned up when no longer needed

## 9.5 Built-in Event System

AmritaCore provides a comprehensive event-driven architecture with built-in event handlers:

### 9.5.1 PreCompletionEvent

Triggered before sending requests to LLM, allowing message modification and preset switching.

### 9.5.2 CompletionEvent

Triggered after receiving responses from LLM, enabling response processing and security checks.

### 9.5.3 FallbackContext

Handles LLM request failures with automatic retry logic and preset fallback mechanisms.

### 9.5.4 Built-in Event Handlers

- **Cookie Security Handler**: Automatically checks for cookie leaks in responses
- **Tool Call Notifications**: Provides real-time feedback on tool execution status
- **Error Propagation**: Ensures proper error handling across the execution pipeline

These built-in capabilities provide a solid foundation for developing sophisticated AI agents while maintaining security, performance, and extensibility.
