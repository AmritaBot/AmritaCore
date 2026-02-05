# AmritaCore - Proj.Amrita Agent Core Module

## Project Overview

AmritaCore is the agent (Agent) core module of Proj.Amrita, a lightweight Python library focused on providing scalable and maintainable agent core implementations. As the core agent component of the project, it undertakes the main logical or control functions, providing a solid foundation for various agent application scenarios.

## Why AmritaCore?

AmritaCore aims to solve several key challenges in modern AI application development:

1. **Simplified Agent Development**: Provides a concise API that allows developers to quickly build and deploy agent applications without worrying about underlying complex implementations.

2. **Flexible Configuration System**: Through modular configuration systems, developers can adjust agent behavior according to their needs, adapting to different scenarios through context management and tool calling.

3. **Scalable Architecture**: Designed with scalability in mind, supporting tool integration, event hooks and other features that allow developers to extend agent capabilities as needed.

4. **Efficient Context Management**: Built-in intelligent memory summarization feature that can effectively manage long conversation histories, balancing context completeness and token consumption.

5. **Asynchronous Processing Support**: Native asynchronous processing for better user experience.

6. **Every is a stream**: Asynchronous streaming message output design, efficient and explicit data processing approach.

7. **Cookie Security Detection**: Will detect prompt leaks during agent output.

## Core Features

### Configuration System

AmritaCore provides a modular configuration system, mainly divided into two parts:

#### FunctionConfig - Functional Configuration

- Configurable context usage strategy to balance token consumption and context integrity
- Supports multiple tool calling modes, including Agent and RAG modes
- Provides multiple reasoning modes, adapting to different complexity task requirements
- Supports MCP clients, facilitating integration with other systems

#### LLMConfig - Large Language Model Configuration

- Built-in intelligent memory summarization feature that automatically manages long conversation history
- Configurable token counting modes to adapt to different model requirements
- Supports automatic retries and timeout controls, enhancing system stability
- Provides session-level token window management

### Data Types and Conversation Management

AmritaCore defines a unified set of data types and conversation management patterns:

- **Message**: Unified message representation, containing role and content information
- **MemoryModel**: Intelligent memory model storing conversation history and summaries
- **ChatObject**: Core conversation processing unit supporting asynchronous streaming processing
- **ModelPreset/ModelConfig**: Model configuration system with "Provider-independent" mechanism

ChatObject is one of AmritaCore's core components, responsible for processing individual conversation sessions. It implements asynchronous streaming response processing, supporting real-time output during processing. ChatObject manages response streams through queue mechanisms, ensuring ordered delivery of responses. It also integrates context management and memory limitation functions, automatically handling lengthy conversation histories.

### Event System

AmritaCore provides a flexible event system that allows developers to inject custom logic at key nodes in the processing flow:

- **PreCompletionEvent**: Triggered before completion, allowing modification of context or processing of user input
- **CompletionEvent**: Triggered after completion, usable for processing final responses or logging
- The event system is managed and triggered through MatcherManager, supporting dynamic registration and matching rules

### Tool System

AmritaCore's tool system supports external tool integration:

- **Decorator Registration**: Easily register new tools using the `@on_tools` decorator
- **Dynamic Discovery**: Automatic collection of tool metadata, supporting runtime discovery of available tools
- **Conditional Enablement**: Supports enabling or disabling tools based on conditions
- **Type Safety**: Tool parameter and return value type safety checks

### Extension Mechanisms

AmritaCore designs flexible extension mechanisms:

- **Tool System**: Supports external tool integration, extending agent capabilities
- **Event Hooks**: Allows injection of custom logic at key nodes in the processing flow
- **Protocol Adapters**: Supports protocol adaptation for different AI models
- **MCP Client**: Easily integrate other tools, achieving cross-system integration

### Security Mechanisms

AmritaCore includes multiple security measures:

- **Cookie Detection**: Detects prompt leaks during agent output
- **Content Filtering**: Supports configuring content filtering mechanisms
- **Session Isolation**: Independent session state management, preventing cross-session data leakage
- **Access Control**: Supports configuring access permissions and restrictions

## Applicable Scenarios

AmritaCore applies to various scenarios requiring agent capabilities:

- Chatbots and virtual assistants
- Automated workflows
- Decision support systems
- Intelligent customer service systems
- Personalized recommendation engines

## Documentation Under Construction

This documentation is still under construction, for more details please refer to the source code and examples.
