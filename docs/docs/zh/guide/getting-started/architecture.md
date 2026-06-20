# 2.4 项目架构理解

## 2.4.1 架构图

### Core Architecture

```mermaid
graph TB
    subgraph "入口层"
        H[Agent运行时]
        Factory["create_agent()"]
    end

    subgraph "核心执行层"
        A[ChatObject]
        F[Agent核心]
        G[Agent策略]
    end

    subgraph "AmritaSense 运行时"
        WI[WorkflowInterpreter]
        MF[MatcherFactory]
        SOS[SuspendObjectStream]
        DI[依赖注入]
        NC[节点组合 >>]
    end

    subgraph "支撑系统"
        B[配置]
        D[工具管理器]
        E[记忆模型]
    end

    subgraph "外部集成"
        Adapter[适配器层]
        LLM[LLM提供商]
        MCP[MCP客户端]
    end

    用户输入 --> Factory
    Factory --> H
    H --> A
    A --> F
    F --> G
    G --> F
    F --> Adapter
    Adapter --> LLM
    F --> MCP

    A -.->|由 WI 驱动| WI
    A -.->|通过 MF 挂钩| MF
    A -.->|通过 SOS 流式| SOS
    MF -.->|解析| DI
    WI -.->|执行| NC

    B --> F
    D --> F
    E --> F

    F --> 响应流[响应流]
    响应流 --> 用户输出
    F --> E
```

### 后端架构与会话数据流

#### 后端驱动的数据管理

```mermaid
graph TB
    subgraph "入口层"
        AR[AgentRuntime]
    end

    subgraph "后端层"
        BS[BackendSlots]
        AB[AbilityBackend]
        MB[MemoryBackend]
    end

    subgraph "运行时状态"
        SC[StateContext]
        AC[AbilityContext]
        MM[MemoryModel]
    end

    subgraph "全局单例"
        G_Tools[全局 ToolsManager]
        G_Presets[全局 PresetManager]
        G_MCP[全局 MCP ClientManager]
    end

    AR -->|slot| BS
    BS -->|ability| AB
    BS -->|memory| MB
    AB -->|load_ability_all| AC
    MB -->|load_memory| MM
    SC -->|包含| AC
    SC -->|包含| MM
    AC -->|默认使用| G_Tools
    AC -->|默认使用| G_Presets
    AC -->|默认使用| G_MCP

    subgraph "内置实现"
        LB[LegacyBackend]
    end

    AB -.- LB
    MB -.- LB
```

`LegacyBackend` 同时实现了 `AbilityBackend` 和 `MemoryBackend`，使用进程内全局容器。自定义后端（如数据库支持的后端）可以独立替换任一槽位。

### 基于策略的执行流程

```mermaid
graph LR
    subgraph "策略类型"
        AgentMode[agent]
        RAGMode[rag]
        WorkflowMode[workflow]
        MixedMode[agent-mixed]
    end

    subgraph "执行方法"
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

## 2.4.2 AmritaSense — 运行时基座

AmritaCore 构建于 [**AmritaSense**](https://sense.amritabot.com) 之上，后者作为**运行时**为每一次 `ChatObject` 执行提供动力。可以将 AmritaSense 理解为 Agent 工作流的"操作系统"——它提供调度、组合和事件管道，而 AmritaCore 在其上定义领域特定的 Agent 逻辑。

### 运行时组件

| 组件                      | 在 ChatObject 中的角色                                                                                                                |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **`WorkflowInterpreter`** | 驱动节点链（`_load_state → _render_train → _limiting_memory → … → _commit_memory`）。每个节点是一个可组合的 `@Node` 装饰协程。        |
| **`MatcherFactory`**      | 管理事件系统。`PreCompletionEvent`、`CompletionEvent`、`FallbackContext` 通过 `@on_precompletion().handle()` 等注册的匹配器进行分发。 |
| **`SuspendObjectStream`** | 流式 I/O 主干。所有 LLM 块、工具调用通知和推理内容都通过这个内置挂起/恢复的双向流传输。                                               |
| **依赖注入**              | `WorkflowInterpreter` 解析节点签名中的 `Depends()` 标记，自动注入 `ChatObject`、配置和自定义依赖。                                    |
| **节点组合 (`>>`)**       | 节点通过 `>>` 操作符链接成 `NodeCompose` 图。解释器根据 `GOTO`/`WHILE`/`ALIAS` 指令进行控制流跳转。                                   |

### AmritaSense 如何驱动 ChatObject

```mermaid
sequenceDiagram
    participant CO as ChatObject
    participant WI as WorkflowInterpreter
    participant MF as MatcherFactory
    participant SOS as SuspendObjectStream
    participant Node as 工作流节点

    CO->>WI: run()
    loop 对链中的每个节点
        WI->>SOS: 检查挂起信号
        SOS-->>WI: 继续 / 阻塞
        WI->>Node: 使用 DI 解析的参数执行
        Node->>MF: trigger_event(PreCompletionEvent, ...)
        MF-->>Node: 事件处理完毕
        Node-->>WI: 结果
        WI->>WI: 评估 GOTO/WHILE/ALIAS
    end
    Note over CO,SOS: ChatObject 通过 io_stream 产出响应
    WI-->>CO: 执行完成
```

这种分离使得 AmritaCore 的 Agent 层保持轻量，专注于策略、会话、工具、MCP 和适配器——所有编排由 AmritaSense 处理。

## 2.4.3 核心组件关系

- **入口层**: 为用户提供简化的交互接口
  - `create_agent()`: 工厂函数，使用最少参数创建 `AgentRuntime`
  - `AgentRuntime`: 高级包装器，封装复杂性并提供可重用的agent操作

- **核心执行层**: 处理主要的处理逻辑
  - `ChatObject`: 管理单个对话的主要交互点，协调所有组件
  - `Agent核心`: `ChatObject` 内部的中央处理逻辑，执行完整的agent循环
  - `Agent策略`: 定义执行模式的抽象基类，支持四种策略类别

- **支撑系统**: 提供基本服务和数据管理
  - `配置`: 通过 `AmritaConfig` 控制系统行为
  - `事件系统`: 通过装饰器和依赖注入在处理流水线中启用钩子
  - `工具管理器`: 通过动态注册使用外部函数扩展功能
  - `记忆模型`: 在会话数据中维护对话上下文和历史

- **外部集成**: 处理与外部系统的通信
  - `适配器层`: 抽象LLM提供商通信，实现厂商无关集成
  - `MCP客户端`: 提供模型上下文协议支持，用于外部服务集成

- **数据后端**: 管理数据隔离与持久化
  - `BackendSlots`：持有 `AbilityBackend` + `MemoryBackend` 引用
  - `LegacyBackend`：内置内存后端，使用全局容器
  - 自定义后端可替换记忆或能力槽位，实现数据库/云端持久化

## 2.4.4 Agent 循环与后端数据流

```mermaid
sequenceDiagram
    participant User as 用户
    participant Entry as 入口层
    participant Core as 核心执行
    participant Support as 支撑系统
    participant External as 外部集成

    User->>Entry: create_agent(url, key, ...)
    Entry->>Entry: 创建 AgentRuntime
    Entry-->>User: 返回 AgentRuntime

    User->>Entry: get_chatobject("输入")
    Entry->>Core: 创建 ChatObject
    Core->>Core: 初始化 Agent 策略
    Core->>Support: Load ability and memory via BackendSlots
    Core->>External: 通过适配器发送请求
    External->>External: 使用 LLM/MCP 处理
    External-->>Core: 返回响应
    Core->>Support: 更新记忆，处理事件
    Core-->>User: 流式传输响应
```

### 基于策略的执行模式

1. **分层架构**: 系统遵循清晰的分层结构，具有明确的层次：
   - 入口层: 简化的用户界面
   - 核心执行层: 主要处理逻辑
   - **AmritaSense 运行时**: 工作流引擎、事件系统、流式处理、依赖注入——驱动执行的基座
   - 支撑系统: 基本服务（配置、工具、记忆）
   - 外部集成: 第三方通信（适配器、MCP）
   - 数据后端: 状态隔离与持久化

2. **策略模式实现**: 四种执行策略提供灵活的行为：
   - **'agent'**: 使用 `single_execute()` 进行迭代式工具调用，逐步执行
   - **'rag'**: 使用 `run()` 进行检索增强生成，使用最小上下文
   - **'workflow'**: 使用 `run()` 对工具调用和上下文管理进行完全手动控制
   - **'agent-mixed'**: 使用 `single_execute()` 进行动态模式处理，可在RAG和Agent模式之间切换

3. **会话隔离**: 每个对话通过独立的会话上下文保持完全隔离，同时在需要时共享全局资源。

4. **事件驱动设计**: 系统使用装饰器和事件处理器允许在不修改核心逻辑的情况下扩展行为。

5. **厂商无关性**: 适配器层确保相同的agent逻辑可以与不同的LLM提供商配合工作而无需代码更改。

6. **模板支持**: [Jinja2模板](/zh/guide/extensions-integration/jinja2-templates)基于上下文、记忆和配置启用动态提示构建。
