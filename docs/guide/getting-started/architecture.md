# 2.4 Project Architecture Understanding

## 2.4.1 Architecture Diagram

### Core Architecture

```mermaid
graph TB
    subgraph "AmritaCore"
        A[ChatObject]
        B[Configuration]
        C[Events System]
        D[Tools Manager]
        F[Agent Core]
    end

    subgraph "Session Context"
        E[Memory Model]
    end

    UserInput[User Input] --> A
    A --> B
    A --> C
    A --> F
    B --> F
    C --> F
    D --> F
    E --> F
    F --> ResponseStream[Response Stream]

    ResponseStream --> UserOutput[User Output]
    F --> E

    LLM[LLM Provider] <---> Adapter[Adapter Layer]
    Adapter <---> F

    style AmritaCore fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    style F fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style Session_Context fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
```

### Session and Global Data Container Architecture

#### Global Container and Session Conversation Context

```mermaid
graph TB
    subgraph "Global Container"
        G_Tools[Global Tools]
        G_Presets[Global Presets]
        G_Config[Global Configuration]
    end

    subgraph "SessionsManager"
        S1[Session 1<br/>Conversation Context]
        S2[Session 2<br/>Conversation Context]
        SN[Session N<br/>Conversation Context]
    end

    subgraph "Single Session Structure"
        Mem[Memory Model<br/>Conversation History]
        Tools[Tools Manager<br/>Current Session Tools]
        Conf[Configuration<br/>Current Session Config]
        MCP[MCP Client<br/>Session-specific Clients]
    end

    G_Tools -.-> Tools
    G_Presets -.-> S1
    G_Config -.-> Conf

    style Global_Container fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style Session_Container fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style S1 fill:#bbdefb,stroke:#1565c0,stroke-width:1px
    style S2 fill:#bbdefb,stroke:#1565c0,stroke-width:1px
    style SN fill:#bbdefb,stroke:#1565c0,stroke-width:1px
```

## 2.4.2 Core Component Relationships

- **ChatObject**: The main interaction point that manages a single conversation and serves as the Agent Core execution unit
- **Configuration**: Controls how the core behaves (context usage, tool calling, security settings, etc.) through `AmritaConfig`
- **Events System**: Allows for hooks into the processing pipeline using decorators like `@on_precompletion` and `@on_completion`, with runtime dependency injection support
- **Tools Manager**: Extends the agent's capabilities with external functions through `MultiToolsManager`, supporting dynamic tool registration
- **Memory Model**: Maintains conversation context and history, stored within each Session's `SessionData`
- **Agent Core**: The central processing logic implemented within `ChatObject`, coordinating all components during the agent loop
- **SessionsManager**: Manages multiple isolated sessions using singleton pattern, each session containing independent `SessionData`
- **Session (Conversation Context)**: Stores all relevant information for a specific user or specific conversation, including memory model, tools, configurations, MCP clients, and presets
- **Adapter Layer**: Abstracts LLM provider communication through adapter pattern, enabling vendor-independent integration
- **MCP Client**: Provides Model Context Protocol client support for external service integration

## 2.4.3 Agent Loop and Session Isolation Mechanism

```mermaid
sequenceDiagram
    participant User1 as User1
    participant User2 as User2
    participant SM as SessionsManager
    participant S1 as Session 1<br/>(Conversation Context 1)
    participant S2 as Session 2<br/>(Conversation Context 2)
    participant Agent as Agent Core
    participant Adapter as Adapter Layer
    participant LLM as LLM Provider

    Note over User1,LLM: Agent Loop Begins
    User1->>SM: Request to create Session 1
    User2->>SM: Request to create Session 2
    SM-->>User1: Return Session ID 1
    SM-->>User2: Return Session ID 2

    Note over User1,User2: Each user interacts in their respective conversation context

    User1->>S1: Send message to Session 1
    S1->>S1: Initialize ChatObject
    S1->>Agent: Start Agent Loop to process request

    User2->>S2: Send message to Session 2
    S2->>S2: Initialize ChatObject
    S2->>Agent: Start Agent Loop to process request

    par Parallel Processing of Two Conversation Contexts
        Agent->>S1: Process in Session 1 Context
        Agent->>S2: Process in Session 2 Context

        Agent->>S1: Update Session 1 Memory Model
        Agent->>S2: Update Session 2 Memory Model
    end

    Agent->>Adapter: Send request (from Session 1)
    Adapter->>LLM: Forward to LLM Provider
    LLM-->>Adapter: Return response
    Adapter-->>Agent: Return processed response
    Agent-->>S1: Update Session 1 State
    S1-->>User1: Stream response

    Agent->>Adapter: Send request (from Session 2)
    Adapter->>LLM: Forward to LLM Provider
    LLM-->>Adapter: Return response
    Adapter-->>Agent: Return processed response
    Agent-->>S2: Update Session 2 State
    S2-->>User2: Stream response

    Note over User1,LLM: Each conversation context maintains independent history and state
```

1. **Session as Conversation Context**: Each Session represents an independent conversation context, storing all relevant information for a specific user or specific conversation within its `SessionData`
2. **Global Data Container**: SessionsManager manages all active conversation contexts, providing global resource sharing while maintaining session isolation
3. **Agent Loop**: Inside each conversation context, the Agent Core (implemented in ChatObject) executes the complete processing loop including event handling, tool calling, and memory management
4. **Context Isolation**: Data between different conversation contexts is completely isolated through separate `SessionData` instances, ensuring conversation histories don't mix
5. **Global Resource Sharing**: Each conversation context can access resources from the Global container (global tools, presets, configuration), but maintains its own independent state including session-specific tools, memory, and MCP clients
6. **Adapter Abstraction**: The Adapter Layer provides vendor-independent LLM integration, allowing the same agent logic to work with different LLM providers without code changes