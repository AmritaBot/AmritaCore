<div v-pre />

# AmritaSense 集成

## 概述

[AmritaSense](https://sense.amritabot.com) 是一个**通用工作流编排引擎**，AmritaCore 使用它来驱动其处理管道。Sense 并非传统的节点-边图，而是将工作流编译为**线性指令序列**，由轻量级虚拟机执行——类似于 CPU 运行机器码。

```mermaid
graph TD
    subgraph AmritaCore
        COMP["components/<br/>llm.py · process.py · react.py"]
        CTX["contexts.py<br/>(dataclass 注入目标)"]
    end
    subgraph AmritaSense
        N["@Node"]
        VM["WorkflowInterpreter<br/>(VM 运行时)"]
        DI["依赖注入"]
        SS["挂起 / 恢复"]
        INS["IF · WHILE · GOTO · CALL · TRY · NOP"]
    end
    COMP --> N
    CTX --> DI
    N --> VM
    VM --> DI
    VM --> SS
    VM --> INS
```

## 指令集架构 vs 图模型

传统引擎定义显式的节点和边。Sense 将它们编译为由**程序计数器**（`PointerVector`）和**调用栈**驱动的指令。

```mermaid
flowchart LR
    subgraph Graph["传统图模型"]
        A["节点 A"] -- 边 --> B["节点 B"]
        B -- 边 --> C["节点 C"]
    end
    subgraph ISA["AmritaSense ISA"]
        D["节点 A >> 节点 B >> 节点 C"]
        D --> E["编译为指令"]
        E --> F["PC=0: A | PC=1: B | PC=2: C"]
    end
```

| 特性     | 图模型            | AmritaSense                       |
| -------- | ----------------- | --------------------------------- |
| 调度     | 图遍历 + 拓扑排序 | 程序计数器递增 / 跳转             |
| 控制流   | 通过路由边模拟    | 原生 `IF`、`WHILE`、`GOTO`、`TRY` |
| 调试     | 需要图可视化      | 通过 `run_step_by()` 逐步执行     |
| 中断     | 额外状态管理      | 原生基于 `Future` 的挂起/恢复     |
| 编译性能 | O(V+E) 遍历       | 100,000 节点约 200ms              |

## @Node 装饰器

`@Node` 将普通的 Python 函数转换为工作流节点。Sense 在装饰时捕获调用帧并存储所有必需的元数据。

```python
from amrita_sense import Node

@Node(
    tag="my_node",          # 可读标识符（默认：函数名）
    wrap_to_async=True,     # 自动包装同步 → 异步
    address_able=True,      # 可通过 GOTO / CALL 寻址
)
async def my_node(param1: int, param2: str) -> str:
    return f"{param1}: {param2}"
```

| 参数            | 类型          | 默认值 | 描述                                        |
| --------------- | ------------- | ------ | ------------------------------------------- |
| `tag`           | `str \| None` | 函数名 | 节点标识符；映射到 `SuspendEnum` 和 `ALIAS` |
| `wrap_to_async` | `bool`        | `True` | 包装同步函数用于异步执行                    |
| `address_able`  | `bool`        | `True` | 允许 `GOTO` / `CALL` 通过别名定位此节点     |

## WorkflowInterpreter——虚拟机

`WorkflowInterpreter` 接收编译后的图并通过其程序计数器驱动执行：

```python
from amrita_sense import Node, NOP, WorkflowInterpreter

@Node()
async def step_one() -> None:
    print("[1] 加载状态")

@Node()
async def step_two() -> None:
    print("[2] 处理")

# >> 链接节点；NOP 是终端哨兵
composition = step_one >> step_two >> NOP
rendered = composition.render()

interpreter = WorkflowInterpreter(rendered)
await interpreter.run()              # 完整运行
# 或者
async for result in interpreter.run_step_by():  # 步进调试
    print(f"→ {result}")
```

它管理一个**调用栈**（`Stack`）用于 `CALL` / `GOTO` / `INTERRUPT`，在每个节点边界处理异常，并在调用每个节点函数之前解析依赖。

## 依赖注入

节点通过**函数签名**声明依赖。在运行时，解释器将参数类型与已注册的 `@dataclass` 实例池进行匹配。

```mermaid
flowchart TD
    N["Node function(opt: DatabackendOptions, ability: AbilityState, ...)"] --> M{参数类型？}
    M -->|已知 dataclass| T[类型匹配注入]
    M -->|str / int / bool| K[通过 extra_kwargs 按名称匹配]
    M -->|Depends(wrapped)| D[特殊运行时对象]
    M -->|其他| P[通过 extra_args 按位置匹配]
    T --> I[依赖已解析]
    K --> I
    D --> I
    P --> I
```

AmritaCore 的入口节点清楚地展示了这一点：

```python
@Node(SuspendEnum.LOAD_STATE)
async def LOAD_STATE(
    opt: DatabackendOptions,   # 按类型注入
    ability: AbilityState,      # 按类型注入
    meta: SessionMetadata,     # 按类型注入
    mem: MemoryContext,         # 按类型注入
    rt_payload: WorkingState,  # 按类型注入
    ip: GeneralInput,           # 按类型注入
):
    ...
```

所有上下文对象都在 `contexts.py` 中以 `@dataclass` 定义。无需手动连接 — Sense 自动解析它们。

## 挂起 / 恢复

Sense 通过 `Future` 回调支持双向暂停和恢复。当外部钩子在 `SuspendEnum` 点发出挂起信号时，当前节点等待，其完整上下文被保留直到钩子发出恢复信号。

```mermaid
sequenceDiagram
    participant VM as WorkflowInterpreter
    participant N as Node
    participant S as SuspendObjectStream
    participant H as Hook / External

    VM->>N: execute
    H-->>VM: suspend(SuspendEnum.LLM_CALL)
    N->>S: await suspend
    Note over N,S: 节点已暂停<br/>上下文已保留
    H->>H: 检查/修改状态
    H-->>VM: resume
    S->>N: 恢复执行
    N->>VM: return result
```

AmritaCore 的 `SuspendEnum` 将每个节点映射到拦截点：

| SuspendEnum         | 节点                 | 拦截位置               |
| ------------------- | -------------------- | ---------------------- |
| `LOAD_STATE`        | LOAD_STATE           | 加载后端状态后         |
| `TRAIN_RENDER`      | JINJA2_RENDER        | Jinja2 渲染后          |
| `MESSAGES_PREPARED` | BUILD_MESSAGE        | SendMessageWrap 构建后 |
| `LLM_CALL`          | LLM_COMPLETION       | LLM API 调用期间       |
| `MEMORY`            | APPEND_RESPONSE      | 响应追加后             |
| `SINGLE_TOOL`       | SINGLE_STRATEGY_CALL | 工具执行期间           |
| `ADVANCE_COUNTER`   | REACT_COUNTER        | 计数器递增后           |
| `APPLY_CONTEXT`     | APPLY_CONTEXT        | 写回记忆前             |
| `COMMIT_MEMORY`     | COMMIT_MEMORY        | 持久化前               |

## 控制流指令

所有控制流编译为线性指令序列。以下是可用指令：

| 指令                          | 等价于                 | 用途                       |
| ----------------------------- | ---------------------- | -------------------------- |
| `IF(cond, then, else_)`       | if / else              | 条件分支                   |
| `WHILE(cond, body)`           | while 循环             | 前测循环                   |
| `DO(body, cond)`              | do-while               | 后测循环                   |
| `TRY(body, catch, then, fin)` | try / except / finally | 异常处理                   |
| `GOTO(target)`                | goto                   | 无条件跳转（PC 操作）      |
| `CALL(target)`                | 函数调用               | 子例程调用（压入返回地址） |
| `NOP`                         | pass                   | 哨兵/终止符                |
| `INTERRUPT`                   | —                      | 显式中断信号               |
| `TRIGGER_EVENT`               | —                      | 触发 `MatcherFactory` 事件 |

一个最小的分支示例：

```python
from amrita_sense import Node, IF, NOP

@Node()
def is_greeting(msg: str) -> bool:
    return msg.lower().startswith("hello")

@Node()
def greet(): print("Hi!")

@Node()
def echo(msg: str): print(f"Echo: {msg}")

flow = IF(is_greeting, greet, echo) >> NOP
```

## AmritaCore 如何使用 AmritaSense

### 完整的节点图

AmritaCore 跨三个模块定义了 11 个 `@Node` 函数：

```mermaid
graph TD
    LS["LOAD_STATE<br/>(入口)"]
    LS --> JR["JINJA2_RENDER"] --> BM["BUILD_MESSAGE"] --> LC["LLM_COMPLETION"]
    LS -.->|config, preset, memory| CHAIN[...]
    LC --> AR["APPEND_RESPONSE"] --> AC["APPLY_CONTEXT"] --> CM["COMMIT_MEMORY"]

    BM --> AE["AGENT_ENTRY"]
    AE --> RC["REACT_COUNTER"]
    RC -->|守卫通过| SC["SINGLE_STRATEGY_CALL"]
    SC -->|成功/回退| RC
    RC -->|BreakLoop| AP["AGENT_POST_PROCESS"]
```

### 模块分解

| 模块         | 节点                                                                               | 职责                    |
| ------------ | ---------------------------------------------------------------------------------- | ----------------------- |
| `llm.py`     | `JINJA2_RENDER`, `LLM_COMPLETION`                                                  | 模板渲染 & LLM API 调用 |
| `process.py` | `LOAD_STATE`, `BUILD_MESSAGE`, `APPEND_RESPONSE`, `APPLY_CONTEXT`, `COMMIT_MEMORY` | 状态生命周期 & 持久化   |
| `react.py`   | `AGENT_ENTRY`, `REACT_COUNTER`, `SINGLE_STRATEGY_CALL`, `AGENT_POST_PROCESS`       | Agent 工具调用循环      |

### 上下文 Dataclass

所有上下文都是 `contexts.py` 中的 `@dataclass` 定义，由 Sense 的 DI 解析：

| Dataclass            | 用途                     | 使用者                                                                                           |
| -------------------- | ------------------------ | ------------------------------------------------------------------------------------------------ |
| `AbilityState`       | 配置、后端槽位、活动预设 | 大多数节点                                                                                       |
| `MemoryContext`      | 会话消息历史             | LOAD_STATE, BUILD_MESSAGE, JINJA2_RENDER, APPLY_CONTEXT, COMMIT_MEMORY                           |
| `WorkingState`       | 消息上下文包装器         | BUILD_MESSAGE, LLM_COMPLETION, APPEND_RESPONSE, APPLY_CONTEXT, AGENT_ENTRY, SINGLE_STRATEGY_CALL |
| `GeneralInput`       | 用户输入、模板、渲染变量 | LOAD_STATE, BUILD_MESSAGE, JINJA2_RENDER                                                         |
| `RespState`          | 最终 LLM 响应            | LLM_COMPLETION, APPEND_RESPONSE                                                                  |
| `DatabackendOptions` | 加载/提交标志            | LOAD_STATE, COMMIT_MEMORY                                                                        |
| `SessionMetadata`    | 会话 ID 和时间戳         | LOAD_STATE, COMMIT_MEMORY                                                                        |
| `AgentLoopState`     | 策略、备份、计数器       | AGENT_ENTRY, REACT_COUNTER, SINGLE_STRATEGY_CALL, AGENT_POST_PROCESS                             |
| `StrategyPayload`    | 策略工厂                 | AGENT_ENTRY                                                                                      |

## 实际示例

### 添加内容过滤节点

```python
from amrita_sense import Node

@Node(tag="ContentFilter", wrap_to_async=False)
def content_filter(ip: GeneralInput, ab: AbilityState) -> None:
    blocked = ab.config.llm.extra_config.get("blocked_words", [])
    for word in blocked:
        ip.user_input = ip.user_input.replace(word, "***")
```

插入管道：`LOAD_STATE >> content_filter >> JINJA2_RENDER >> ...`

### 使用 IF 进行条件监控

```python
from amrita_sense import Node, IF, NOP
import time

@Node()
def should_monitor(ab: AbilityState) -> bool:
    return ab.config.llm.extra_config.get("enable_monitoring", False)

@Node()
def record_start(wok: WorkingState) -> None:
    wok.context_wrap._meta = {"start": time.monotonic()}

monitor_chain = IF(should_monitor, record_start, NOP)
```

### 延伸阅读

- [AmritaSense 源码](https://github.com/AmritaBot/AmritaSense)
- [AmritaCore 组件](https://github.com/AmritaBot/AmritaCore/tree/main/src/amrita_core/components)
- [组件节点参考（文档字符串）](https://github.com/AmritaBot/AmritaCore/tree/main/src/amrita_core/components)
