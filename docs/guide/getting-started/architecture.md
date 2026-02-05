
# 2.4 Project Architecture Understanding

## 2.4.1 Architecture Diagram

```plaintext
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │───▶│  AmritaCore      │───▶│  LLM Provider   │
│                 │    │                  │    │                 │
└─────────────────┘    │  ┌─────────────┐ │    └─────────────────┘
                       │  │ ChatObject  │ │
                       │  └─────────────┘ │
                       │  ┌─────────────┐ │
                       │  │  Config     │ │
                       │  └─────────────┘ │
                       │  ┌─────────────┐ │
                       │  │   Events    │ │
                       │  └─────────────┘ │
                       │  ┌─────────────┐ │
                       │  │    Tools    │ │
                       │  └─────────────┘ │
                       └──────────────────┘
```

## 2.4.2 Core Component Relationships

- **ChatObject**: The main interaction point that manages a single conversation
- **Configuration**: Controls how the core behaves (context usage, tool calling, etc.)
- **Events**: Allow for hooks into the processing pipeline
- **Tools**: Extend the agent's capabilities with external functions
- **Memory Model**: Maintains conversation context and history

## 2.4.3 Data Flow Explanation

1. User input enters through a ChatObject
2. Configuration determines processing behavior
3. The input is formatted and sent to the LLM
4. Events may intercept and modify the flow
5. Tools may be called based on the input
6. The response is streamed back to the user
7. Memory is updated with the new conversation state