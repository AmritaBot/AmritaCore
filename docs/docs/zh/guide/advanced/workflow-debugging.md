# 工作流级调试

> AmritaCore 的 `ChatObject` 由**工作流引擎**驱动（由 [AmritaSense](https://sense.amritabot.com) 提供），该引擎逐步执行处理管道 — 模板渲染 → 记忆限制 → LLM 调用 → 记忆提交等。完整节点链参见[工作流引擎](workflow-engine.md)。

**注意：这是高级功能。大多数用户不需要直接接触工作流 — [事件与钩子](../tutorials/event-hooks.md)覆盖了大多数观测需求，[挂起](suspend.md)覆盖了生产环境断点需求。**

当您确实需要在工作流层面调试时 — 了解哪个节点正在运行、在步骤间检查内部状态、或向管道注入自定义逻辑 — 有两种 AmritaCore 原生的方法，两者都不需要学习单独的调试器 API。

## 选择您的方式

| 您想做什么                                          | 使用方式                                                                             |
| --------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 观测管道活动（日志、审计、告警）                    | [事件与钩子](../tutorials/event-hooks.md)                                            |
| 在特定点暂停执行，检查或修改状态，然后恢复          | [挂起与恢复](suspend.md)                                                             |
| 包裹整个工作流 — 查看每一步、计时每个节点、捕获错误 | [中间件注入](#中间件注入)                                                            |
| 在管道的特定点插入自定义检查逻辑                    | [存档节点注入](#存档节点注入)                                                        |
| 在 REPL 中逐步执行节点、设置断点、从崩溃中恢复      | [AmritaSense REPL 调试器](https://sense.amritabot.com/guide/practice/repl-debugging) |

- **事件用于观测** — 处理程序并行运行，绝不阻塞工作流。
- **挂起用于生产** — 基于协作和标签，可安全部署。
- **中间件和存档节点用于开发调试** — 它们让您能直接访问工作流，无需理解 AmritaSense 运行时。

## 背景：什么是工作流？

当您调用 `chat.begin()` 时，ChatObject 将其工作交给一个内部**解释器**，该解释器逐步执行预编译的节点图：

```text
[JINJA2_RENDER] → [_limiting_memory] → [BUILD_MESSAGE] → [_pre_runner]
→ [_run_strategy] → [LLM_COMPLETION] → [_post_runner] → [COMMIT_MEMORY]
```

每个方框是一个**节点** — 一个带有名称标记的 Python 函数，如 `"LLM_COMPLETION"`（这些与 `SuspendEnum` 使用的标签相同）。解释器按顺序运行它们，管理子工作流的调用栈（例如 agent 工具调用循环），并在节点边界处理异常。

您可以从任何 `ChatObject` 访问解释器：

```python
inter = chat._interpreter
```

以下两种调试方法都通过此解释器工作 — 但您无需直接调用它。ChatObject 的构造函数接受参数来连接您的调试代码。

## 中间件注入

`middleware` 参数是最直接的调试钩子：一个单独的异步函数，**包裹整个工作流执行**。在它内部，您可以在运行之前、期间和之后检查 `ChatObject` 上的任何内容。

### 基础：记录每一步

```python
import logging
from amrita_core import ChatObject

async def debug_middleware(chat_obj: ChatObject) -> None:
    """记录每次 ChatObject 执行的开始和结束。"""
    logging.info("[debug] 工作流开始 — session=%s", chat_obj.session_id)
    try:
        await chat_obj._interpreter.run()
    finally:
        logging.info("[debug] 工作流结束")

chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Hello!",
    session_id="session_123",
    middleware=debug_middleware,
)
```

关键行是 `await chat_obj._interpreter.run()` — 您的中间件负责驱动解释器。您拥有生命周期控制权：可以在之前添加设置、之后添加清理，甚至选择完全不运行它。

### 高级：在步骤间检查状态

由于解释器也可以通过 `run_step_by()` **逐步**运行，中间件可以在每个节点之后检查状态：

```python
async def step_by_step_middleware(chat_obj: ChatObject) -> None:
    """逐个节点运行工作流，在每个节点后打印状态。"""
    inter = chat_obj._interpreter
    async for _ in inter.run_step_by():
        node = inter.get_graph().calc.find_addr_safe(inter._pointer.base_addr)
        tag = getattr(node, 'tag', '<unknown>')
        depth = len(inter._ret_addr_stack)
        print(f"  ✓ [{tag}]  stack_depth={depth}")

chat = ChatObject(
    ...,
    middleware=step_by_step_middleware,
)
```

运行时的输出：

```
  ✓ [LOAD_STATE]  stack_depth=0
  ✓ [JINJA2_RENDER]  stack_depth=0
  ✓ [_limiting_memory]  stack_depth=0
  ✓ [LLM_COMPLETION]  stack_depth=0
  ✓ [_post_runner]  stack_depth=0
  ✓ [COMMIT_MEMORY]  stack_depth=0
```

这为您提供了解释器访问的每个节点的实时追踪，完全不需要 AmritaSense 调试器。

### 错误捕获

由于您的中间件拥有 `run()` 调用，您可以捕获来自任何节点的异常：

```python
async def safe_middleware(chat_obj: ChatObject) -> None:
    try:
        await chat_obj._interpreter.run()
    except Exception as exc:
        logging.error("[debug] 工作流在节点 %s 崩溃: %s",
                       chat_obj._interpreter._pointer, exc)
        # 解释器保留 panic 状态 — 您可以检查它
        raise
```

## 存档节点注入

有时您不想包裹所有内容 — 您想在管道的**特定位置**注入逻辑。`archived_nodes` 参数允许您将额外节点追加到标准管道的末尾。

一个节点就是一个用 `@Node` 装饰的异步函数。ChatObject 的依赖注入系统会自动连接其参数，因此您的节点会收到与内置节点相同的上下文对象（`MemoryContext`、`WorkingState` 等）。

### 示例：完成后转储状态

```python
from amrita_sense import Node
from amrita_sense.instructions import ARCHIVED_NODES

@Node("debug_dump_state")
async def dump_state(self, working: WorkingState, memory: MemoryContext):
    """工作流完成后转储内部状态。"""
    print("=== 调试转储 ===")
    print(f"响应: {working.response.content if working.response else 'none'}")
    print(f"记忆消息: {len(memory.memory.messages) if memory.memory else 0}")
    print(f"工具调用: {len(working.tool_calls) if hasattr(working, 'tool_calls') else 0}")
    print("================")

# 打包为存档存储
debug_nodes = ARCHIVED_NODES(dump_state)

chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Hello!",
    session_id="session_123",
    archived_nodes=debug_nodes,
)
```

`dump_state` 节点在标准管道**完成之后**运行，因为 `archived_nodes` 被追加到末尾。要在不同位置注入，可以组合自定义工作流（参见[预组合工作流](workflow-engine.md#预组合工作流-v0-12-6)）：

```python
from amrita_core.builtins.workflows import SIMPLE_CHAT
from amrita_sense import Node

@Node("pre_llm_inspection")
async def inspect_before_llm(self, working: WorkingState):
    print(f"[debug] 即将调用 LLM — 已准备 {len(working.messages)} 条消息")

# 在 LLM_COMPLETION 之前插入：（需要理解节点链；完整图参见工作流引擎）
```

### 节点参数（依赖注入）

您的节点函数可以声明内置 AmritaCore 节点使用的任何参数。解释器在运行时从 ChatObject 的 DI 上下文中解析它们。常见的有：

| 参数类型              | 提供的内容                   |
| --------------------- | ---------------------------- |
| `ChatObject` (`self`) | ChatObject 实例本身          |
| `WorkingState`        | 当前响应、工具调用、消息     |
| `MemoryContext`       | 记忆模型和消息历史           |
| `AbilityState`        | 配置、预设、后端             |
| `GeneralInput`        | 用户输入、系统提示、模板变量 |

如果需要此处未列出的参数，请查看 `src/amrita_core/contexts.py` 了解所有可用的 DI 类型。

### 限制

- `workflow` 和 `archived_nodes` **互斥** — 同时提供两者会引发 `ValueError`。
- 存档节点在正常执行期间被跳过。要从外部按需调用，需要使用 `call_sub(interrupt=True)` — 参见 AmritaSense 文档中的[外部中断调用](https://sense.amritabot.com/guide/advanced/external_interrupt)。

## 深入探索：AmritaSense REPL 调试器

如果中间件和存档节点还不够 — 例如，您需要在 Python REPL 中进行**交互式逐步执行**、在特定节点上设置**条件断点**、或**崩溃恢复**（跳过崩溃节点并继续）— AmritaSense 提供了专用的调试器模块：

```python
from amrita_sense.debugger import step, cont, break_at_tag, inspect, list_nodes

inter = chat._interpreter

list_nodes(inter)                      # 打印图中的每个节点
break_at_tag(inter, "LLM_COMPLETION")  # 设置断点
cont(inter)                            # 运行直到断点或结束
inspect(inter)                         # 完整状态转储
```

所有函数都是同步的（无需 `await`）— 可直接在 `python` 或 `ipython` 中调用。断点通过复合中间件注入，绝不修改运行时核心。

> **完整 API 和示例**：AmritaSense 文档中的 [REPL 调试](https://sense.amritabot.com/guide/practice/repl-debugging)。  
> **安全性**：在生产环境中设置 `REMOVE_DEBUGGER=true` 以物理移除调试器模块 — 任何导入会引发 `AttributeError`。
