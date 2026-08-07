# Writing a Custom Agent Strategy

> **Where this fits**: you understand the [strategy contract](../concepts/agent-strategy.md)
> and want to write your own. This page is the hands-on guide — from choosing a
> base class to a complete runnable strategy.

## 1. Choose Your Base Class

| Base class               | When to use                                                           | How it is injected                                                                                                    |
| ------------------------ | --------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `AgentStrategy`          | Stateless strategy, describable by a class                            | The framework instantiates it: `agent.strategy(ctx)`                                                                  |
| `StrategyLikedObject`    | Stateful strategy instance (own state machine, pre-configured params) | You pass an **already-initialized instance** to `ChatObject`; the framework calls `strategy(ctx)` to bind the context |
| `BaseReActAgentStrategy` | A ReAct-style strategy (tool loop + reasoning)                        | Like `AgentStrategy` — extend and override template methods                                                           |

Both `AgentStrategy` and `StrategyLikedObject` inherit `_StrategyBase`, which
gives you:

- `self.ctx` — the `StrategyContext` (set via `_bind`)
- `self.chat_object` — the lifecycle-manager handle
- `self.tools_manager` — the tools manager
- convenience properties: `self.preset`, `self.config`, `self.io_stream`,
  `self.train_content`, `self.stream_id`, `self.resp_extra_usage`

> `StrategyLikedObject.__call__` must call `super().__call__(ctx)` first when
> overridden. `AgentStrategy` binds in `__init__`.

## 2. Declare the Category

`get_category()` decides **who owns the loop**:

| Category                    | The framework calls          | The framework does                       |
| --------------------------- | ---------------------------- | ---------------------------------------- |
| `"agent"` / `"agent-mixed"` | `single_execute()` per round | Runs the loop (limits, rollback, events) |
| `"rag"` / `"workflow"`      | `run()` once                 | Hands over full control                  |

## 3. A Complete `single_execute` Strategy

Here is a minimal but complete framework-managed strategy: one tool round per
call, streaming every step:

```python
from typing import Literal

from amrita_core.agent.strategy import AgentStrategy
from amrita_core.types import ToolCall, UniResponse


class LoggingAgentStrategy(AgentStrategy):
    """Agent strategy that logs each round and delegates tool calls to the
    framework's call_tool()."""

    async def single_execute(self) -> bool:
        if not self.tools:
            return False  # nothing to call -> stop

        # 1. Ask the model for the next tool call(s).
        from amrita_core.libchat import tools_caller

        response: UniResponse[None, list[ToolCall] | None] = await tools_caller(
            self.ctx.message.unwrap(),
            self.tools,
            tool_choice="auto",
            preset=self.preset,
        )

        if not response.tool_calls:
            return False  # model chose to answer directly -> stop

        # 2. Execute each call through the framework (validated args, unified
        #    error handling, ToolResult pairing).
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
        return True  # keep looping

    async def on_post_process(self) -> None:
        """Runs after the loop finishes successfully."""
        await self.io_stream.yield_response("(agent finished)")

    @classmethod
    def get_category(cls) -> Literal["agent"]:
        return "agent"
```

### Hooking it up

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

## 4. A Stateful `StrategyLikedObject` Strategy

When the strategy needs its own state across turns (budgets, counters,
pre-configured tools), pass an **instance**:

```python
from amrita_core.agent.strategy import StrategyLikedObject


class BudgetedStrategy(StrategyLikedObject):
    def __init__(self, max_rounds: int = 5):
        self.max_rounds = max_rounds
        self.rounds_used = 0

    async def single_execute(self) -> bool:
        self.rounds_used += 1
        return self.rounds_used < self.max_rounds  # hard budget

    @classmethod
    def get_category(cls) -> Literal["agent"]:
        return "agent"


# Pass the instance, not the class — either via the runtime:
agent.set_strategy(BudgetedStrategy)  # AgentStrategy-style (class)

# ...or directly on a ChatObject (for StrategyLikedObject instances):
from amrita_core.chatmanager import ChatObject

chat = ChatObject(
    train={"role": "system", "content": "You are a helpful assistant."},
    user_input="Do the task.",
    session_id="s1",
    agent_strategy=BudgetedStrategy(max_rounds=3),  # the instance
)
```

## 5. ReAct-Style: Extend `BaseReActAgentStrategy`

For a ReAct strategy, extend `BaseReActAgentStrategy` and override the
**template methods** — the shared `_execute_tool_loop` handles execution,
pairing and error handling:

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
        # Custom pairing — e.g. add a marker to the result text.
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

Key template methods: `_append_tool_result_to_context`,
`_handle_error_append`, `_append_reasoning`, `_build_stop_response_and_append`.
Override `single_execute` for full control (see the built-in
`ReActAgentStrategy` in `react_comm.py`).

> If you override `single_execute` on a step-loop strategy, keep
> `get_category()` returning `"agent-mixed"` and call
> `_execute_tool_loop(response_msg)` for the shared execution flow.

## 6. Rules of Thumb

- **Always** return a bool from `single_execute` (`True` = keep looping)
- Use `self.call_tool(tc)` instead of `tools_manager` directly — it gives you
  validated args + unified error handling
- Pair every assistant `tool_calls` message with its `ToolResult` (OpenAI
  requirement) — or use the base class's loop which does it for you
- `on_post_process()` runs after success for **all** categories
- `on_limited()` runs when the tool-call limit is hit
- `on_exception(exc)` runs on failure (default: pass)

## Next

- [Concepts → Agent Strategy](../concepts/agent-strategy.md) — the contract in depth
- [Advanced → Step Loop](../advanced/step-loop.md) — the built-in strategy's full machinery
