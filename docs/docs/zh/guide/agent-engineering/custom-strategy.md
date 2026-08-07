# 编写自定义 Agent 策略

> **位置**：你已理解[策略契约](../concepts/agent-strategy.md)，想自己写一个。
> 本页是实战指南——从选基类到完整可运行策略。

## 1. 选择基类

| 基类                     | 何时用                                   | 如何注入                                                                 |
| ------------------------ | ---------------------------------------- | ------------------------------------------------------------------------ |
| `AgentStrategy`          | 无状态策略，可用类描述                   | 框架实例化它：`agent.strategy(ctx)`                                      |
| `StrategyLikedObject`    | 有状态策略实例（自带状态机、预配置参数） | 你传**已初始化的实例**给 `ChatObject`；框架调 `strategy(ctx)` 绑定上下文 |
| `BaseReActAgentStrategy` | ReAct 风格策略（工具循环 + 推理）        | 同 `AgentStrategy`——继承并覆写模板方法                                   |

`AgentStrategy` 与 `StrategyLikedObject` 都继承 `_StrategyBase`，它给你：

- `self.ctx` —— `StrategyContext`（由 `_bind` 设置）
- `self.chat_object` —— 生命周期管理器句柄
- `self.tools_manager` —— 工具管理器
- 便捷属性：`self.preset`、`self.config`、`self.io_stream`、
  `self.train_content`、`self.stream_id`、`self.resp_extra_usage`

> `StrategyLikedObject.__call__` 被覆写时必须先调 `super().__call__(ctx)`。
> `AgentStrategy` 在 `__init__` 里绑定。

## 2. 声明类别

`get_category()` 决定**谁拥有循环**：

| 类别                        | 框架调用                | 框架负责                     |
| --------------------------- | ----------------------- | ---------------------------- |
| `"agent"` / `"agent-mixed"` | 每轮 `single_execute()` | 运行循环（上限、回滚、事件） |
| `"rag"` / `"workflow"`      | 一次 `run()`            | 完全移交控制                 |

## 3. 一个完整的 `single_execute` 策略

下面是完整但最小化的框架托管策略：每次调用一轮工具，逐步流式输出：

```python
from typing import Literal

from amrita_core.agent.strategy import AgentStrategy
from amrita_core.types import ToolCall, UniResponse


class LoggingAgentStrategy(AgentStrategy):
    """记录每轮并把工具调用委托给框架 call_tool() 的 agent 策略。"""

    async def single_execute(self) -> bool:
        if not self.tools:
            return False  # 没有工具 -> 停止

        # 1. 请模型给出下一个工具调用。
        from amrita_core.libchat import tools_caller

        response: UniResponse[None, list[ToolCall] | None] = await tools_caller(
            self.ctx.message.unwrap(),
            self.tools,
            tool_choice="auto",
            preset=self.preset,
        )

        if not response.tool_calls:
            return False  # 模型选择直接作答 -> 停止

        # 2. 通过框架执行每个调用（校验参数、统一错误处理、ToolResult 配对）。
        for tc in response.tool_calls:
            result = await self.call_tool(tc)
            self.ctx.message.append(
                Message(
                    role="assistant",
                    content=None,
                    tool_calls=[tc],
                )
            )
            self.ctx.message.append(
                ToolResult(
                    role="tool",
                    name=tc.function.name,
                    content=result,
                    tool_call_id=tc.id,
                )
            )
        return True  # 继续循环

    async def on_post_process(self) -> None:
        """循环成功后运行。"""
        await self.io_stream.yield_response("(agent finished)")

    @classmethod
    def get_category(cls) -> Literal["agent"]:
        return "agent"
```

### 挂接

```python
from amrita_core import create_agent, minimal_init

await minimal_init()
agent = create_agent(base_url=..., api_key=..., model=...)
agent.set_strategy(LoggingAgentStrategy)

chat = agent.get_chatobject("What is 17*3? Use the calculate tool.")
async with chat.begin():
    async for msg in chat.io_stream.get_response_generator():
        print(msg, end="", flush=True)
```

## 4. 有状态的 `StrategyLikedObject` 策略

策略需要跨轮次自有状态（预算、计数器、预配置工具）时，传**实例**：

```python
from amrita_core.agent.strategy import StrategyLikedObject


class BudgetedStrategy(StrategyLikedObject):
    def __init__(self, max_rounds: int = 5):
        self.max_rounds = max_rounds
        self.rounds_used = 0

    async def single_execute(self) -> bool:
        self.rounds_used += 1
        return self.rounds_used < self.max_rounds  # 硬预算

    @classmethod
    def get_category(cls) -> Literal["agent"]:
        return "agent"


# 传实例而非类——要么通过运行时：
agent.set_strategy(BudgetedStrategy)  # AgentStrategy 风格（类）

# ...要么直接在 ChatObject 上（StrategyLikedObject 实例）：
from amrita_core.chatmanager import ChatObject

chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Do the task.",
    session_id="s1",
    agent_strategy=BudgetedStrategy(max_rounds=3),  # 实例
)
```

## 5. ReAct 风格：继承 `BaseReActAgentStrategy`

ReAct 策略继承 `BaseReActAgentStrategy` 并覆写**模板方法**——共享的
`_execute_tool_loop` 处理执行、配对与错误处理：

```python
from amrita_core.builtins.agent.react_base import BaseReActAgentStrategy
from amrita_core.types import ToolCall, UniResponse


class MyReActStrategy(BaseReActAgentStrategy):
    async def _append_tool_result_to_context(
        self,
        tool_call: ToolCall,
        func_response: str,
        response_msg: UniResponse[None, list[ToolCall] | None],
    ):
        # 自定义配对——例如给结果文本加标记。
        self.ctx.message.append(
            Message(role="assistant", content=None, tool_calls=[tool_call])
        )
        self.ctx.message.append(
            ToolResult(
                role="tool",
                name=tool_call.function.name,
                content=f"[custom] {func_response}",
                tool_call_id=tool_call.id,
            )
        )
```

关键模板方法：`_append_tool_result_to_context`、`_handle_error_append`、
`_append_reasoning`、`_build_stop_response_and_append`。需要完全控制时覆写
`single_execute`（参考 `react_comm.py` 里的内置 `ReActAgentStrategy`）。

> 在 step 循环策略上覆写 `single_execute` 时，保持 `get_category()` 返回
> `"agent-mixed"`，并调用 `_execute_tool_loop(response_msg)` 走共享执行流。

## 6. 经验法则

- `single_execute` **始终**返回 bool（`True` = 继续循环）
- 用 `self.call_tool(tc)` 而非直接操作 `tools_manager`——它给你校验参数 +
  统一错误处理
- 每条带 `tool_calls` 的 assistant 消息必须配对其 `ToolResult`（OpenAI
  要求）——或用基类循环，它会替你完成
- `on_post_process()` 在成功后对**所有**类别运行
- `on_limited()` 在工具调用上限触发时运行
- `on_exception(exc)` 在失败时运行（默认 pass）

## 下一步

- [核心概念 → Agent 策略](../concepts/agent-strategy.md)——深入契约
- [进阶 → Step 循环](../advanced/step-loop.md)——内置策略的完整机制
