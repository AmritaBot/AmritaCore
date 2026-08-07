# AmritaSense 概览

**我们回顾 AmritaCore 所依赖的 AmritaSense 组件。** 完整文档在
[sense.amritabot.com](https://sense.amritabot.com)。

## 思想

AmritaSense 把工作流编译为**线性指令序列**，由轻量 VM 执行——就像 CPU 运行
机器码。节点用 `>>` 链接；控制流是原生指令（`IF`、`WHILE`、`GOTO`、`CALL`、
`TRY`、`NOP`）。

```python
from amrita_sense import Node, WorkflowInterpreter


@Node()
async def step_one() -> None:
    print("[1] load state")


@Node()
async def step_two() -> None:
    print("[2] process")


composition = step_one >> step_two
interpreter = WorkflowInterpreter(composition.render())
await interpreter.run()
```

## Core 使用了 Sense 的什么

| Sense 原语            | Core 的用途                                               |
| --------------------- | --------------------------------------------------------- |
| `@Node`               | 每个组件（`components/llm.py`、`process.py`、`react.py`） |
| `WorkflowInterpreter` | `ChatObject._interpreter` 运行对话管线                    |
| 依赖注入（类型匹配）  | 工作流节点接收 `AgentLoopState`、`AbilityState`……         |
| `SuspendObjectStream` | `ChatObject.io_stream`——双向流式                          |
| Matcher 事件          | 管线/step 钩子系统（见[事件](../concepts/event.md)）      |
| NATIVE 指令           | 内置 step 循环（`NATIVE_DO`/`NATIVE_WHILE`）              |

## VM

- **程序计数器**（`PointerVector`）+ 调用栈驱动执行
- 节点运行前解析依赖（DI）
- 每个节点边界捕获异常
- `run_step_by()` 逐步产出用于调试

见[工作流引擎](workflow-engine.md)了解 ChatObject 如何组合管线，以及
[sense.amritabot.com](https://sense.amritabot.com/guide/concepts/compose_and_exec)
的引擎参考。
