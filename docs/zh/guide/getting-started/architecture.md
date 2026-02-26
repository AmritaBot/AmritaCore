# 2.4 项目架构理解

## 2.4.1 架构图

### Core Architecture

```mermaid
graph TB
    subgraph "AmritaCore"
        A[ChatObject]
        B[配置]
        C[事件系统]
        D[工具管理器]
        F[Agent核心]
    end

    subgraph "Session上下文"
        E[记忆模型]
    end

    用户输入 --> A
    A --> B
    A --> C
    A --> F
    B --> F
    C --> F
    D --> F
    E --> F
    F --> 响应流[响应流]

    响应流 --> 用户输出
    F --> E

    LLM[LLM 提供商] <---> 适配器[适配器层]
    适配器 <---> F

    style AmritaCore fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    style F fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style Session_Container fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
```

### Session 与 Global 数据容器架构

#### Global 全局容器与 Session 对话上下文

```mermaid
graph TB
    subgraph "Global 全局容器"
        G_Tools[全局工具]
        G_Presets[全局预设]
        G_Config[全局配置]
    end

    subgraph "SessionsManager"
        S1[Session 1<br/>对话上下文]
        S2[Session 2<br/>对话上下文]
        SN[Session N<br/>对话上下文]
    end

    subgraph "单个 Session 结构"
        Mem[记忆模型<br/>对话历史]
        Tools[工具管理器<br/>当前会话工具]
        Conf[配置<br/>当前会话配置]
        MCP[MCP客户端<br/>会话专属客户端]
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

## 2.4.2 核心组件关系

- **ChatObject**: 管理单个对话的主要交互点，同时也是Agent核心的执行单元
- **配置**: 通过 `AmritaConfig` 控制核心行为（上下文使用、工具调用、安全设置等）
- **事件系统**: 允许通过装饰器（如 `@on_precompletion` 和 `@on_completion`）挂钩到处理流水线，支持运行时依赖注入
- **工具管理器**: 通过 `MultiToolsManager` 使用外部函数扩展Agent功能，支持动态工具注册
- **记忆模型**: 维护对话上下文和历史记录，存储在每个Session的 `SessionData` 中
- **Agent核心**: 在 `ChatObject` 内部实现的中央处理逻辑，在Agent循环期间协调所有组件
- **SessionsManager**: 使用单例模式管理多个隔离的会话，每个会话包含独立的 `SessionData`
- **Session（对话上下文）**: 保存特定用户或特定对话的所有相关信息，包括记忆模型、工具、配置、MCP客户端和预设
- **适配器层**: 通过适配器模式抽象LLM提供商通信，实现厂商无关集成
- **MCP客户端**: 提供模型上下文协议客户端支持，用于外部服务集成

## 2.4.3 Agent 循环与 Session 隔离机制

```mermaid
sequenceDiagram
    participant User1 as 用户1
    participant User2 as 用户2
    participant SM as SessionsManager
    participant S1 as Session 1<br/>(对话上下文1)
    participant S2 as Session 2<br/>(对话上下文2)
    participant Agent as Agent核心
    participant Adapter as 适配器层
    participant LLM as LLM 提供商

    Note over User1,LLM: Agent 循环开始
    User1->>SM: 请求创建 Session 1
    User2->>SM: 请求创建 Session 2
    SM-->>User1: 返回 Session ID 1
    SM-->>User2: 返回 Session ID 2

    Note over User1,User2: 每个用户在各自的对话上下文中交互

    User1->>S1: 发送消息到 Session 1
    S1->>S1: 初始化 ChatObject
    S1->>Agent: 启动 Agent 循环处理请求

    User2->>S2: 发送消息到 Session 2
    S2->>S2: 初始化 ChatObject
    S2->>Agent: 启动 Agent 循环处理请求

    par 并行处理两个对话上下文
        Agent->>S1: 在 Session 1 上下文中处理
        Agent->>S2: 在 Session 2 上下文中处理

        Agent->>S1: 更新 Session 1 记忆模型
        Agent->>S2: 更新 Session 2 记忆模型
    end

    Agent->>Adapter: 发送请求 (来自 Session 1)
    Adapter->>LLM: 转发到 LLM 提供商
    LLM-->>Adapter: 返回响应
    Adapter-->>Agent: 返回处理后的响应
    Agent-->>S1: 更新 Session 1 状态
    S1-->>User1: 流式传输响应

    Agent->>Adapter: 发送请求 (来自 Session 2)
    Adapter->>LLM: 转发到 LLM 提供商
    LLM-->>Adapter: 返回响应
    Adapter-->>Agent: 返回处理后的响应
    Agent-->>S2: 更新 Session 2 状态
    S2-->>User2: 流式传输响应

    Note over User1,LLM: 每个对话上下文保持独立的历史和状态
```

1. **Session 作为对话上下文**: 每个 Session 代表一个独立的对话上下文，在其 `SessionData` 中存储特定用户或特定对话的所有相关信息
2. **Global 数据容器**: SessionsManager 管理所有活动的对话上下文，提供全局资源共享的同时保持会话隔离
3. **Agent 循环**: 在每个对话上下文内部，Agent 核心（在 ChatObject 中实现）执行完整的处理循环，包括事件处理、工具调用和记忆管理
4. **上下文隔离**: 通过独立的 `SessionData` 实例实现不同对话上下文之间的数据完全隔离，确保对话历史不混淆
5. **全局资源共享**: 每个对话上下文可以访问 Global 容器中的资源（全局工具、预设、配置），但拥有各自独立的状态，包括会话专属的工具、记忆和 MCP 客户端
6. **适配器抽象**: 适配器层提供厂商无关的 LLM 集成，允许相同的 Agent 逻辑与不同的 LLM 提供商配合工作而无需代码更改