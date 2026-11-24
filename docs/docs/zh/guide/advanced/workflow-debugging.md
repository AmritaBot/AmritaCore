# 工作流调试

## 单步执行解释器

AmritaSense 的 `WorkflowInterpreter` 支持 `run_step_by()`——逐步产出每个节点
执行，而非跑完：

```python
async def debug(chat: ChatObject) -> None:
    interp = chat._interpreter
    async for result in interp.run_step_by():
        print(f"-> {result}")
```

结合[挂起点](suspend.md)在节点之间检查状态。

## 节点断点

`@Node(tag=...)` 标签兼作挂起点。外部代码可在流上 `wait_to_suspend(tag)`，
精确停在感兴趣的节点——例如 `"ChatObject::step_intro"` 在每次 Step 边界
暂停。

Step 边界的决策本身也是节点，可以直接下断点：`STEP_DECOMPOSE`（首次分解）、
`STEP_BEGIN_NODE` / `STEP_BEGIN_SIMPLE` / `STEP_BEGIN_BOUNDARY`（Step 选取）、
`STEP_PLAN_STATUS`（计划快照注入）、`STEP_SUMMARY`（Step 收尾摘要）。

## 中间件

用 `middleware` 包装整个工作流做粗粒度控制：

```python
async def trace_middleware(chat: ChatObject) -> None:
    print(f"[trace] start {chat.stream_id}")
    try:
        await chat._interpreter.run()
    finally:
        print(f"[trace] done {chat.stream_id}")


chat = ChatObject(..., middleware=trace_middleware)
```

## 常见检查点

| 检查什么       | 在哪                                         |
| -------------- | -------------------------------------------- |
| 当前 Step 状态 | `chat._di_loop.run_state`（`AgentRunState`） |
| 策略上下文     | `chat._di_loop.stg_ctx`                      |
| 消息列表       | `chat._di_working.context_wrap`              |
| 流事件         | `get_response_generator()` 的元数据条目      |
| 会话记忆       | `chat._di_memory.memory`                     |

> 用 AmritaSense 的术语，`run_step_by()` 与中间件是引擎特性——通用调试参考
> 见 [sense.amritabot.com](https://sense.amritabot.com)。

## 玄学问题救援：崩溃后进 REPL（Sense 1.2.0）

有些问题只在现场发生一次：某个节点里抛出一个谁也没预料到的异常，整条
对话就此失败，事后能拿到的只有一份 traceback。指针停在哪、返回栈里还有谁、
上下文栈是什么样，都在 unwind 时一并丢了。

Sense 1.2.0 的 `RESCUE_ON_PANIC` 把"抛出之前的那几十秒"留给你：panic 时
不再直接 unwind，而是停在崩溃现场，开一个 `(sdb)` 会话。

> 需要 `amrita-sense >= 1.2.0`。1.1.x 没有 `RESCUE_ON_PANIC`，设了也不会生效。

### 开启

```python
from amrita_sense._unsafe import __flags__

__flags__.RESCUE_ON_PANIC = True
```

它是 unsafe 标志，可以运行时切换，但请当作启动配置用。

### 两条路径

| 条件                         | 行为                                                                 |
| ---------------------------- | -------------------------------------------------------------------- |
| stdin 是交互终端             | 在当前进程里进入 `(sdb)`，阻塞到你 `q` / `k` / EOF                    |
| 没有终端（bot 进程、CI、管道） | 立即抛出，把 `PanicReport` 挂到异常的 `__sdb_report__` 上，3.11+ 另加一条 note |

TTY 判定不只看 `isatty()`：还要求进程是终端的前台进程组，`TERM` 不能是
`dumb`。两个环境变量可以覆盖：

```bash
SDB_REPL_DISABLE=1    # 强制不进（生产保护，优先级最高）
SDB_REPL_FORCE=1      # 强制进入（测试、手工排查）
SDB_REPL_TIMEOUT=300  # 无人输入多少秒后退出；0 表示不限
```

无论走哪条路，异常类型都不会被改写。救援只保留现场，不吞失败。

### 在 Core 里接住它

AmritaBot 这类进程通常没有终端，救援会走 `PanicReport` 分支。把报告落盘，
比让 traceback 随进程日志一起滚掉有用得多：

```python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


async def run_chat(chat: ChatObject) -> None:
    try:
        await chat.async_run()
    except Exception as exc:
        report = getattr(exc, "__sdb_report__", None)
        if report is not None:
            logger.error(report.summary())
            dump = Path("/var/log/amrita/panic")
            dump.mkdir(parents=True, exist_ok=True)
            (dump / f"{chat.stream_id}.txt").write_text(
                report.to_text(), encoding="utf-8"
            )
        raise
```

`summary()` 是一行日志安全的摘要（panic 类型、消息、pc、flags）；`to_text()`
带反汇编、backtrace 和上下文栈，适合单独存一份。

### 现场里做什么

| 命令                | 用在什么时候                                                     |
| ------------------- | ---------------------------------------------------------------- |
| `bt` / `x` / `i r`  | 先看清崩在哪：调用链、当前段反汇编、伪寄存器                     |
| `s`                 | 重跑崩溃节点（panic 状态在执行前清掉）                           |
| `skip`              | 跳过崩溃节点，只推进指针、不动栈                                 |
| `suppress`          | 结束救援并让 `run()` 正常返回                                    |
| `suppress continue` | 跳过失败节点，把剩余流程跑完                                     |
| `undo`              | 把调试器看到的 pc / 返回栈 / flags / panic 放回去                |
| `py`                | 打开真正的 Python 控制台，顶层 `await` 调度在解释器自己的循环上  |
| `q` / `k`           | 离开，原异常照旧上抛（`k` 额外关闭 workflow scope）              |

几个边界值得记住：

- `suppress` 是唯一让失败从上层视线里消失的路径。日志会留一条
  `panic suppressed by operator`，`inter.panic_suppressed` 置位，
  `inter.get_exception()` 仍然能回答"这次崩在哪"。
- `suppress continue` 期间再次 panic 不会被吞，命令会报出来并把现场留在会话里。
- `undo` 不是执行回滚：跑过的节点不会重跑，业务副作用不会撤销。
- `skip` 恰好跳过最后一个节点时，救援会明确告诉你工作流已结束，此时
  `s` / `c` 会被拒绝，不会从 `[0]` 重来。
- 救援默认等 300 秒；生产环境如果不希望进程停住，直接 `SDB_REPL_DISABLE=1`。
- 直接驱动 `run_step_by()` 的代码不会自动触发救援，需要自己调
  `rescue_on_panic()`。
