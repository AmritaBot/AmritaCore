# Project Architecture Understanding

## Architecture Diagram

### Core Architecture

```mermaid
graph TB
    subgraph "Entry Layer"
        H[Agent Runtime]
        Factory["create_agent()"]
    end

    subgraph "Core Execution Layer"
        A[ChatObject]
        F[Agent Core]
        G[Agent Strategy]
    end

    subgraph "AmritaSense Runtime"
        WI[WorkflowInterpreter]
        MF[MatcherFactory]
        SOS[SuspendObjectStream]
        DI[Dependency Injection]
        NC[Node Compose >>]
    end

    subgraph "Support System"
        B[Configuration]
        D[Tool Manager]
        E[Memory Model]
    end

    subgraph "External Integration"
        Adapter[Adapter Layer]
        LLM[LLM Provider]
        MCP[MCP Client]
    end

    UserInput --> Factory
    Factory --> H
    H --> A
    A --> F
    F --> G
    G --> F
    F --> Adapter
    Adapter --> LLM
    F --> MCP

    A -.->|driven by| WI
    A -.->|hooks via| MF
    A -.->|streams via| SOS
    MF -.->|resolves| DI
    WI -.->|executes| NC

    B --> F
    D --> F
    E --> F

    F --> ResponseStream[Response Stream]
    ResponseStream --> UserOutput
    F --> E
```

### Backend Architecture and Session Data Flow

#### Backend-Driven Data Management

```mermaid
graph TB
    subgraph "Entry Layer"
        AR[AgentRuntime]
    end

    subgraph "Backend Layer"
        BS[BackendSlots]
        AB[AbilityBackend]
        MB[MemoryBackend]
    end

    subgraph "Runtime State"
        SC[StateContext]
        AC[AbilityContext]
        MM[MemoryModel]
    end

    subgraph "Global Singletons"
        G_Tools[Global ToolsManager]
        G_Presets[Global PresetManager]
        G_MCP[Global MCP ClientManager]
    end

    AR -->|slot| BS
    BS -->|ability| AB
    BS -->|memory| MB
    AB -->|load_ability_all| AC
    MB -->|load_memory| MM
    SC -->|contains| AC
    SC -->|contains| MM
    AC -->|defaults to| G_Tools
    AC -->|defaults to| G_Presets
    AC -->|defaults to| G_MCP

    subgraph "Built-in Implementation"
        LB[LegacyBackend]
    end

    AB -.- LB
    MB -.- LB
```

The `LegacyBackend` implements both `AbilityBackend` and `MemoryBackend` using in-process global containers. Custom backends (e.g., database-backed) can replace either slot independently.

### Strategy-Based Execution Flow

```mermaid
graph LR
    subgraph "Strategy Categories"
        AgentMode[agent]
        RAGMode[rag]
        WorkflowMode[workflow]
        MixedMode[agent-mixed]
    end

    subgraph "Execution Methods"
        SingleExecute["single_execute()"]
        RunMethod["run()"]
    end

    AgentMode --> SingleExecute
    MixedMode --> SingleExecute
    RAGMode --> RunMethod
    WorkflowMode --> RunMethod

    SingleExecute --> AgentLoop[Agent Loop]
    RunMethod --> AgentLoop
```

## AmritaSense — The Runtime Substrate

AmritaCore is built on [**AmritaSense**](https://sense.amritabot.com), which serves as the **runtime** that powers every `ChatObject` execution. Think of AmritaSense as the "operating system" for agent workflows — it provides the scheduling, composition, and event plumbing, while AmritaCore defines the domain-specific agent logic on top.

### Runtime Components

| Component                 | Role in ChatObject                                                                                                                                                                                                                                                                   |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`WorkflowInterpreter`** | Drives the node chain (`LOAD_STATE → JINJA2_RENDER → _limiting_memory → BUILD_MESSAGE → … → LLM_COMPLETION → COMMIT_MEMORY`). Since v0.12.0, core workflow nodes have been extracted to the `amrita_core.components` package. Each node is a composable `@Node` decorated coroutine. |
| **`MatcherFactory`**      | Manages the event system. `PreCompletionEvent`, `CompletionEvent`, `FallbackContext` are dispatched through matchers registered via `@on_precompletion().handle()` etc.                                                                                                              |
| **`SuspendObjectStream`** | The streaming I/O backbone. All LLM chunks, tool call notifications, and reasoning content flow through this bidirectional stream with built-in suspend/resume.                                                                                                                      |
| **Dependency Injection**  | `WorkflowInterpreter` resolves type annotations and `Depends()` markers in node signatures, injecting `ChatObject`, DI context objects (`_di_ability`, `_di_memory`, `_di_input`, etc.), config, and custom dependencies automatically.                                              |
| **Node Compose (`>>`)**   | Nodes are chained with the `>>` operator into a `NodeCompose` graph. The interpreter follows `GOTO`/`WHILE`/`ALIAS` instructions for control flow.                                                                                                                                   |

### How AmritaSense Drives a ChatObject

```mermaid
sequenceDiagram
    participant CO as ChatObject
    participant WI as WorkflowInterpreter
    participant MF as MatcherFactory
    participant SOS as SuspendObjectStream
    participant Node as WorkflowNode

    CO->>WI: run()
    loop For each node in chain
        WI->>SOS: check suspend signal
        SOS-->>WI: proceed / block
        WI->>Node: execute with DI-resolved args
        Node->>MF: trigger_event(PreCompletionEvent, ...)
        MF-->>Node: event processed
        Node-->>WI: result
        WI->>WI: evaluate GOTO/WHILE/ALIAS
    end
    Note over CO,SOS: ChatObject yields responses via io_stream
    WI-->>CO: execution complete
```

This separation keeps AmritaCore's Agent layer thin and focused on strategy, sessions, tools, MCP, and adapters — all the orchestration is handled by AmritaSense.

## Core Component Relationships

- **Entry Layer**: Provides a simplified interaction interface for users
  - `create_agent()`: Factory function that creates an `AgentRuntime` with minimal parameters
  - `AgentRuntime`: High-level wrapper that encapsulates complexity and provides reusable agent operations

- **Core Execution Layer**: Handles the main processing logic
  - `ChatObject`: Manages the primary interaction point for a single conversation, coordinating all components
  - `Agent Core`: The central processing logic inside `ChatObject` that executes the complete agent loop
  - `Agent Strategy`: Abstract base class defining execution modes, supporting four strategy categories

- **Support System**: Provides essential services and data management
  - `Configuration`: Controls system behavior via `AmritaConfig`
  - `Event System`: Enables hooks in the processing pipeline through decorators and dependency injection
  - `Tool Manager`: Extends functionality via dynamic registration of external functions
  - `Memory Model`: Maintains conversation context and history within session data

- **External Integration**: Handles communication with external systems
  - `Adapter Layer`: Abstracts LLM provider communication, enabling vendor‑neutral integration
  - `MCP Client`: Provides Model Context Protocol support for external service integration

- **Data Backend**: Manages data isolation and persistence
  - `BackendSlots`: Holds `AbilityBackend` + `MemoryBackend` references
  - `LegacyBackend`: Built-in in-memory backend using global containers
  - Custom backends can replace memory or ability slots for database/cloud persistence

## Agent Loop and Backend Data Flow

```mermaid
sequenceDiagram
    participant User as User
    participant Entry as EntryLayer
    participant Core as CoreExecution
    participant Support as SupportSystem
    participant External as ExternalIntegration

    User->>Entry: create_agent(url, key, ...)
    Entry->>Entry: Create AgentRuntime
    Entry-->>User: Return AgentRuntime

    User->>Entry: get_chatobject("input")
    Entry->>Core: Create ChatObject
    Core->>Core: Initialize Agent Strategy
    Core->>Support: Load ability and memory via BackendSlots
    Core->>External: Send request via adapter
    External->>External: Process with LLM/MCP
    External-->>Core: Return response
    Core->>Support: Update memory, handle events
    Core-->>User: Stream response
```

### Strategy-Based Execution Modes

1. **Layered Architecture**: The system follows a clear hierarchical structure with well‑defined layers:
   - Entry Layer: Simplified user interface
   - Core Execution Layer: Main processing logic
   - **AmritaSense Runtime**: Workflow engine, event system, streaming, DI — the substrate that drives execution
   - Support System: Essential services (config, tools, memory)
   - External Integration: Third‑party communication (adapters, MCP)
   - Data Backend: State isolation and persistence

2. **Strategy Pattern Implementation**: Four execution strategies provide flexible behavior:
   - **'agent'**: Uses `single_execute()` for iterative tool calling and step‑by‑step execution
   - **'rag'**: Uses `run()` for retrieval‑augmented generation with minimal context
   - **'workflow'**: Uses `run()` for full manual control over tool calls and context management
   - **'agent-mixed'**: Uses `single_execute()` for dynamic mode switching between RAG and agent modes

3. **Backend-Driven Data**: Memory and ability resolution are delegated to `BackendSlots`. The default `LegacyBackend` stores data in in-process global containers, while custom backends enable persistence and distributed state.

4. **Event‑Driven Design**: The system uses decorators and event handlers to allow behavior extension without modifying core logic.

5. **Vendor Neutrality**: The adapter layer ensures that the same agent logic can work with different LLM providers without code changes.

6. **Template Support**: [Jinja2 templates](/guide/extensions-integration/jinja2-templates) enable dynamic prompt construction based on context, memory, and configuration.
