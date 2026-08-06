# 附录与设计哲学

## 设计哲学

以下决策塑造了整个框架。理解它们就明白了*为什么*代码长这样。

### ChatObject 是生命周期管理器——对话的基本单位

`ChatObject` 不是薄包装：它为一次对话拥有工作流、解释器、双向流和每个
DI 上下文。策略与钩子接收资源；ChatObject 把它们接线。这使它成为对话的
基本单位，也是挂载中间件、会话与生命周期的自然位置。

### Step 是提示词工程的单位

内置 ReAct 循环把每个 **Step**（一个 DAG 节点）当作显式的提示词工程单位：
进入 → 执行 → 摘要。没有硬编码的 planner 或 subagent 机制——LLM 分解为
**语义 DAG**，框架用 stdlib `graphlib` 按拓扑序走完它，执行保持线性。
DAG 是提示层，不是并行图。

### 一切可观测、可中断

每个边界都发出事件与元数据：step intro/leave、迭代、工具调用/返回。
Matcher 修改事件；`StepAbortError` 是控制流逃生舱。停滞检测在*循环内*运行，
卡住的 agent 会停止烧 token。

### 框架管循环，策略管 Step

`get_category()` 决定谁拥有循环：`agent`/`agent-mixed` → 框架循环并每轮调
`single_execute()`；`rag`/`workflow` → 策略全权。这让自定义策略保持小巧，
而框架的保证（上限、回滚、事件）统一。

### 不重复 Sense 专属知识

AmritaCore 在需要处内联回顾 AmritaSense 并外链其余。文档旅程镜像工程旅程：
跑 → 用 → 理解 → 扩展 → 调优 → 深入。

## 命名约定

### `*Manager` vs `Multi*Manager`

Manager 类遵循一条简单规则：

| 名称                                                            | 类型         | 作用域                                                               |
| --------------------------------------------------------------- | ------------ | -------------------------------------------------------------------- |
| `ToolsManager`、`ClientManager`、`PresetManager`                | **单例**     | 全局、进程级容器——所有人共享同一实例                                 |
| `MultiToolsManager`、`MultiClientManager`、`MultiPresetManager` | **普通容器** | 自行创建实例用于隔离（每会话工具、每会话 MCP 客户端、每会话 preset） |

无 `Multi` 前缀的 Manager 以单例实现（`__new__` + `_instance`），继承各自的
`Multi*` 基类；`Multi*` 版本是普通可实例化容器。示例：

- `@simple_tool` 注册进全局 `ToolsManager`
- `MultiToolsManager` 实例可挂到会话的 ability 上实现每会话工具
- `ClientManager()`（单例）就是 `load_amrita()` 驱动的那个；`MultiClientManager`
  实例给会话自己的 MCP 集合

### 其他前缀

- `Base*` —— 抽象基类（`BaseTokenizer`、`BaseReActAgentStrategy`）
- `Legacy*` —— 向后兼容实现（`LegacyBackend`）

## 术语表

| 术语                      | 含义                                                |
| ------------------------- | --------------------------------------------------- |
| **Agent**                 | 调用工具达成目标的策略驱动执行器                    |
| **ChatObject**            | 生命周期管理器——对话的基本单位                      |
| **Step**                  | 内置 step 循环的一个 DAG 节点（进入 → 执行 → 离开） |
| **Stall**                 | Step 内重复相同的工具签名                           |
| **`SuspendObjectStream`** | 工作流（producer）与调用方（consumer）之间的双向流  |
| **DI Context**            | 注入工作流节点的类型化状态（如 `AgentLoopState`）   |
| **工作流**                | 预编译的 AmritaSense 指令序列                       |
| **Matcher**               | 按类型字符串注册的事件处理器                        |
| **Preset**                | 端点 + 模型 + thinking 配置 + 工具的捆绑            |
| **后端**                  | `AbilityBackend` / `MemoryBackend` 实现             |
| **会话**                  | 按 `session_id` 键控的隔离对话历史                  |

## 缩写

API · JSON · HTTP · LLM · MCP（Model Context Protocol）· MoE（Mixture of
Experts）· VM（Virtual Machine）· DI（Dependency Injection）· DAG（Directed
Acyclic Graph）

## 项目资源

- **仓库**：[github.com/AmritaBot/AmritaCore](https://github.com/AmritaBot/AmritaCore)
- **Issues**：在 GitHub Issues 报告 bug 与功能请求
- **AmritaCore 站点**：[core.amritabot.com](https://core.amritabot.com)
- **AmritaSense 文档**：[sense.amritabot.com](https://sense.amritabot.com)
- **贡献**：见仓库 `CONTRIBUTING.md`
