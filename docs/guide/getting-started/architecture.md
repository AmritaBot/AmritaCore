# 2.4 Project Architecture Understanding

## 2.4.1 Architecture Diagram

```mermaid
graph TB
    subgraph "AmritaCore"
        A[ChatObject]
        B[Configuration]
        C[Events System]
        D[Tools Manager]
        E[Memory Model]
        F[Agent Core]
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
    
    LLM[LLM Provider] <---> F
    
    style AmritaCore fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    style F fill:#fff3e0,stroke:#f57c00,stroke-width:2px
```

## 2.4.2 Core Component Relationships

- **ChatObject**: The main interaction point that manages a single conversation
- **Configuration**: Controls how the core behaves (context usage, tool calling, etc.)
- **Events System**: Allows for hooks into the processing pipeline
- **Tools Manager**: Extends the agent's capabilities with external functions
- **Memory Model**: Maintains conversation context and history
- **Agent Core**: The central processing unit coordinating all components

## 2.4.3 Data Flow Explanation

```mermaid
sequenceDiagram
    participant User as User
    participant CO as ChatObject
    participant Config as Configuration
    participant Events as Events System
    participant Tools as Tools Manager
    participant Agent as Agent Core
    participant LLM as LLM Provider
    participant Memory as Memory Model

    User->>CO: Send input message
    CO->>Config: Check configuration
    CO->>Events: Trigger input events
    CO->>Agent: Initialize processing
    Agent->>Memory: Load conversation context
    Agent->>Tools: Check for required tools
    Agent->>LLM: Format and send request
    LLM-->>Agent: Return response
    Agent->>Memory: Update conversation state
    Agent->>Events: Trigger output events
    CO-->>User: Stream response
```

1. User input enters through a ChatObject
2. Configuration determines processing behavior
3. The input triggers various events in the Events System
4. Agent Core loads the conversation context from Memory Model
5. Agent Core checks if any tools need to be called based on the input
6. The processed input is sent to the LLM Provider
7. The response from LLM is handled by Agent Core
8. Memory Model is updated with the new conversation state
9. Output events may intercept and modify the final response
10. The response is streamed back to the user via ChatObject