# AmritaCore - Proj.Amrita Agent Core Module

## Project Overview

AmritaCore is the agent (Agent) core module of Proj.Amrita, a lightweight Python library focused on providing scalable and maintainable agent core implementations. As the core agent component of the project, it undertakes the main logical or control functions, providing a solid foundation for various agent application scenarios.

## Why AmritaCore?

AmritaCore aims to solve several key challenges in modern AI application development:

1. **Simplified Agent Development**: Provides high-level APIs like `create_agent()` factory function for rapid development, while maintaining full control through `AgentRuntime` class.

2. **Flexible Agent Strategy Architecture**: Supports four distinct execution strategies:
   - **Agent Mode**: Standard iterative tool calling with reasoning capabilities
   - **RAG Mode**: Retrieval-augmented generation for knowledge-intensive tasks
   - **Workflow Mode**: Sequential workflow execution for structured processes
   - **Agent-Mixed Mode**: Hybrid approach that dynamically adapts between modes

3. **Scalable Architecture**: Designed with extensibility in mind, supporting tool integration, event hooks, and protocol adapters that allow developers to extend agent capabilities as needed.

4. **Efficient Context Management**: Built-in intelligent memory summarization feature that automatically manages long conversation histories, balancing context completeness and token consumption.

5. **Native Async Streaming**: Every output is designed as an asynchronous stream ("Every is a stream"), enabling real-time response processing and better user experience.

6. **Provider-Independent Design**: Abstract data types and conversation management that work across different LLM providers without vendor lock-in.

7. **Comprehensive Security**: Built-in cookie security detection, session isolation, and content filtering mechanisms to protect against prompt injection and data leakage.

8. **Native Suspend/Resume Support**: Built-in mechanism to pause and resume agent execution flow at any point, enabling interactive applications with real-time user control

## Core Features

### Agent Strategy System

AmritaCore implements a flexible Agent Strategy architecture with four execution categories:

#### Agent Strategy (`"agent"`)

- Iterative tool calling with built-in reasoning support
- Automatic tool call limits to prevent infinite loops
- Full framework management of execution loop and termination

#### RAG Strategy (`"rag"`)

- Minimal context focusing on system message + user query
- Optimized for external knowledge retrieval scenarios
- No historical conversation context by default

#### Workflow Strategy (`"workflow"`)

- Complete manual control over execution flow
- Suitable for complex multi-step workflows with custom orchestration
- Full conversation history with manual management

#### Agent-Mixed Strategy (`"agent-mixed"`)

- Dynamic mode switching based on context requirements
- Combines RAG and iterative tool calling capabilities
- Implemented by the built-in `AmritaAgentStrategy`

### Configuration System

AmritaCore provides comprehensive configuration through modular systems:

#### FunctionConfig - Functional Configuration

- Configurable tool calling modes: `"agent"`, `"rag"`, `"workflow"`, `"none"`
- Reasoning modes: `"reasoning"`, `"reasoning-required"`, etc.
- Built-in tool configuration: stop tool, reasoning tool, process message tool
- MCP client integration for external tool expansion
- Session isolation and memory management settings

#### LLMConfig - Large Language Model Configuration

- Intelligent memory abstraction with automatic summarization
- Configurable token counting and window management
- Automatic retry logic with fallback preset support
- Streaming response configuration with usage statistics
- Provider-independent model preset system

### Core API Functions

AmritaCore provides both high-level and low-level APIs:

#### create_agent() Factory Function

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
    # Use agent.get_chatobject() for interactions
```

#### AgentRuntime Class

- Full control over agent configuration and lifecycle
- Session management with persistent memory
- Strategy customization and dynamic switching
- Advanced configuration options for production use

### Built-in Tools

AmritaCore includes three essential built-in tools:

- **STOP_TOOL** (`agent_stop`): Indicates task completion and readiness for final answer
- **REASONING_TOOL** (`think_and_reason`): Generates reasoning steps for autonomous decision-making
- **PROCESS_MESSAGE** (`processing_message`): Communicates internal thoughts and current actions to users

These tools are automatically enabled based on configuration and provide the foundation for intelligent agent behavior.

### Protocol Adapters

AmritaCore supports multiple LLM providers through protocol adapters:

- **OpenAIAdapter**: Full support for OpenAI-compatible APIs with streaming, tool calling, and usage tracking
- **AnthropicAdapter** (Experimental): Support for Anthropic Claude models with proper token handling

### Event System

Comprehensive event-driven architecture with multiple hook points:

- **PreCompletionEvent**: Modify messages before sending to LLM
- **CompletionEvent**: Process responses after receiving from LLM
- **FallbackContext**: Handle LLM request failures with automatic retry logic
- **Custom Events**: Extensible event system for custom integrations

### Tool System

Robust external tool integration system:

- **Decorator Registration**: Register tools using `@on_tools` decorator with full schema definition
- **Custom Run Mode**: Advanced tool execution with direct access to chat object via `ctx.ctx.chat_object`
- **Dynamic Discovery**: Automatic tool metadata collection and runtime discovery
- **Conditional Enablement**: Enable/disable tools based on runtime conditions
- **Type Safety**: Full type checking for tool parameters and return values

### Security Mechanisms

Multi-layered security architecture:

- **Cookie Security Detection**: Automatic detection of prompt injection attempts through cookie leakage
- **Session Isolation**: Complete isolation between user sessions with independent state management
- **Content Filtering**: Configurable content filtering for both input and output
- **Access Control**: Role-based access control and rate limiting support

## Applicable Scenarios

AmritaCore applies to various scenarios requiring agent capabilities:

- **Intelligent Chatbots**: Conversational agents with tool calling and reasoning capabilities
- **Automated Workflows**: Multi-step process automation with error handling
- **Research Assistants**: Knowledge-intensive tasks with RAG capabilities
- **Decision Support Systems**: Complex decision-making with reasoning traces
- **Customer Service Automation**: Enterprise-grade customer service with security and compliance
- **Personalized Recommendation Engines**: Context-aware recommendation systems

## Getting Started

Install AmritaCore:

```bash
pip install amrita-core
```

Basic usage:

```python
import asyncio
from amrita_core import create_agent, minimal_init

async def main():
    await minimal_init()
    agent = create_agent(
        base_url="https://api.openai.com/v1",
        api_key="your-openai-key",
        model="gpt-4"
    )

    chat = agent.get_chatobject("Hello! What can you do?")
    async with chat.begin():
        response = await chat.full_response()
        print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation

Please view [official documentation](https://amrita-core.suggar.top) for comprehensive guides, API references, and examples.
