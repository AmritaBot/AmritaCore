"""Tests for the per-tool concurrency-safety flag and the tool round scheduler.

Covers the flag itself, how the tools manager resolves it without re-running
``enable_if``, how a round is split into pools, and that each pool honours the
configured in-flight limit while keeping the model's result order.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from amrita_core.agent.context import StrategyContext
from amrita_core.builtins.agent import ReActAgentStrategy
from amrita_core.builtins.tools import (
    PROCESS_MESSAGE,
    REASONING_TOOL,
    REFLECTION_TOOL,
    STOP_TOOL,
    UPDATE_STEP_TOOL,
)
from amrita_core.chatmanager import ChatObject
from amrita_core.config import AmritaConfig, FunctionConfig, LLMConfig, set_config
from amrita_core.contexts import AbilityContext
from amrita_core.tools.manager import MultiToolsManager
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    ToolData,
    ToolFunctionSchema,
)
from amrita_core.types import Message, SendMessageWrap, ToolCall


@pytest.fixture(autouse=True)
def setup_global_config():
    """Reset the global configuration before every test."""
    set_config(AmritaConfig())


def make_tool_data(
    name: str,
    func,
    concurrency_safe: bool | Any = True,
    enable_if=None,
) -> ToolData:
    """Build a minimal ToolData registration for one test tool."""
    schema = ToolFunctionSchema(
        function=FunctionDefinitionSchema(
            name=name,
            description=f"Test tool {name}",
            parameters=FunctionParametersSchema(type="object", properties={}),
        ),
        type="function",
        strict=False,
    )
    kwargs: dict[str, Any] = {"concurrency_safe": concurrency_safe}
    if enable_if is not None:
        kwargs["enable_if"] = enable_if
    return ToolData(data=schema, func=func, custom_run=False, **kwargs)


def make_tool_call(name: str, arguments: str = "{}", call_id: str = "call") -> ToolCall:
    """Build a ToolCall pointing at the named tool."""
    return ToolCall.model_validate(
        {"id": call_id, "function": {"name": name, "arguments": arguments}}
    )


@pytest.fixture
def strategy():
    """Build a ReAct strategy with a private tools manager and a stubbed stream."""
    config = AmritaConfig()
    config.function_config = FunctionConfig()
    config.llm = LLMConfig()
    config.builtin.tool_calling_mode = "agent"
    config.builtin.agent_thought_mode = "chat"

    chat_obj = MagicMock(spec=ChatObject)
    chat_obj.session_id = "test-session"
    chat_obj.preset = "default-preset"
    chat_obj.config = config
    chat_obj.io_stream = MagicMock()
    chat_obj.io_stream.yield_response = AsyncMock()
    chat_obj.io_stream.set_queue_done = AsyncMock()
    chat_obj._di_ability.ability = AbilityContext(tools=MultiToolsManager())
    chat_obj.train = Message(role="system", content="Test system message")

    user_msg = Message(role="user", content="test user input")
    ctx = StrategyContext(
        user_input="test user input",
        original_context=SendMessageWrap(
            train=Message(role="system", content="System message"),
            memory=[user_msg],
            user_query=user_msg,
        ),
        chat_object=chat_obj,
    )
    built = ReActAgentStrategy(ctx)
    built.tools_manager = MultiToolsManager()
    return built


class TestToolDataFlag:
    """The flag on ToolData, including the callable form."""

    def test_defaults_to_safe(self):
        tool = make_tool_data("t", AsyncMock(return_value="ok"), concurrency_safe=True)
        assert tool.concurrency_safe is True
        assert tool.is_concurrency_safe({}) is True

    def test_explicit_false(self):
        tool = make_tool_data("t", AsyncMock(return_value="ok"), concurrency_safe=False)
        assert tool.is_concurrency_safe({}) is False

    def test_callable_sees_arguments(self):
        seen: list[dict[str, Any]] = []

        def classify(arguments: dict[str, Any]) -> bool:
            seen.append(arguments)
            return arguments.get("read_only") is True

        tool = make_tool_data("t", AsyncMock(return_value="ok"), classify)
        assert tool.is_concurrency_safe({"read_only": True}) is True
        assert tool.is_concurrency_safe({"read_only": False}) is False
        assert seen == [{"read_only": True}, {"read_only": False}]

    def test_callable_raising_is_unsafe(self):
        def boom(arguments: dict[str, Any]) -> bool:
            raise ValueError("classifier failed")

        tool = make_tool_data("t", AsyncMock(return_value="ok"), boom)
        assert tool.is_concurrency_safe({}) is False

    def test_callable_must_return_literal_true(self):
        for value in (1, "yes", None, [True]):
            tool = make_tool_data(
                "t", AsyncMock(return_value="ok"), lambda _a, v=value: v
            )
            assert tool.is_concurrency_safe({}) is False


class TestManagerLookup:
    """The manager-side lookup used by the scheduler."""

    def test_absent_tool_is_unsafe(self):
        manager = MultiToolsManager()
        assert manager.is_concurrency_safe("missing", {}) is False

    def test_disabled_tool_is_unsafe(self):
        manager = MultiToolsManager()
        manager.register_tool(make_tool_data("t", AsyncMock(return_value="ok")))
        manager.disable_tool("t")
        assert manager.is_concurrency_safe("t", {}) is False

    def test_registered_flag_is_reported(self):
        manager = MultiToolsManager()
        manager.register_tool(
            make_tool_data("t", AsyncMock(return_value="ok"), concurrency_safe=False)
        )
        assert manager.is_concurrency_safe("t", {}) is False

    def test_enable_if_is_not_reevaluated(self):
        calls = 0

        def enable_if() -> bool:
            nonlocal calls
            calls += 1
            return True

        manager = MultiToolsManager()
        manager.register_tool(
            make_tool_data("t", AsyncMock(return_value="ok"), enable_if=enable_if)
        )
        assert manager.is_concurrency_safe("t", {}) is True
        assert calls == 0


class TestGrouping:
    """Splitting one round into ordered pools."""

    def test_builtin_tools_are_always_unsafe(self, strategy):
        for builtin in (
            STOP_TOOL,
            REASONING_TOOL,
            REFLECTION_TOOL,
            UPDATE_STEP_TOOL,
            PROCESS_MESSAGE,
        ):
            call = make_tool_call(builtin.function.name)
            assert strategy._tool_call_is_concurrency_safe(call) is False

    def test_malformed_arguments_are_unsafe(self, strategy):
        strategy.tools_manager.register_tool(
            make_tool_data("safe_tool", AsyncMock(return_value="ok"))
        )
        call = make_tool_call("safe_tool", arguments="{not json")
        assert strategy._tool_call_is_concurrency_safe(call) is False

    def test_mixed_calls_split_into_barriers(self, strategy):
        strategy.tools_manager.register_tool(
            make_tool_data("safe_a", AsyncMock(return_value="a"))
        )
        strategy.tools_manager.register_tool(
            make_tool_data("safe_b", AsyncMock(return_value="b"))
        )
        strategy.tools_manager.register_tool(
            make_tool_data("write", AsyncMock(return_value="w"), concurrency_safe=False)
        )
        calls = [
            make_tool_call("safe_a", call_id="1"),
            make_tool_call("safe_b", call_id="2"),
            make_tool_call("write", call_id="3"),
            make_tool_call("safe_a", call_id="4"),
        ]
        assert strategy._group_tool_calls(calls) == [[0, 1], [2], [3]]

    def test_all_safe_forms_one_pool(self, strategy):
        strategy.tools_manager.register_tool(
            make_tool_data("safe", AsyncMock(return_value="ok"))
        )
        calls = [make_tool_call("safe", call_id=str(i)) for i in range(4)]
        assert strategy._group_tool_calls(calls) == [[0, 1, 2, 3]]


class TestScheduling:
    """Execution of one round: limits, barriers and result order."""

    @staticmethod
    def _recorder(state: dict[str, Any], name: str, delay: float):
        async def run(_arguments: dict[str, Any]) -> str:
            state["peak"] = max(state.get("peak", 0), state["active"] + 1)
            state["active"] += 1
            state["order"].append(name)
            try:
                await asyncio.sleep(delay)
            finally:
                state["active"] -= 1
            return f"result:{name}"

        return run

    @pytest.mark.asyncio
    async def test_zero_limit_lets_the_whole_pool_overlap(self, strategy):
        state: dict[str, Any] = {"active": 0, "peak": 0, "order": []}
        for i in range(4):
            name = f"safe_{i}"
            strategy.tools_manager.register_tool(
                make_tool_data(name, self._recorder(state, name, 0.05))
            )
        strategy.config.function_config.agent_tool_parallel_limit = 0
        calls = [make_tool_call(f"safe_{i}", call_id=str(i)) for i in range(4)]

        results = await strategy._run_tool_calls_concurrently(calls)

        assert state["peak"] == 4
        assert [r[1] for r in results] == [f"result:safe_{i}" for i in range(4)]

    @pytest.mark.asyncio
    async def test_limit_caps_in_flight_calls(self, strategy):
        state: dict[str, Any] = {"active": 0, "peak": 0, "order": []}
        for i in range(6):
            name = f"safe_{i}"
            strategy.tools_manager.register_tool(
                make_tool_data(name, self._recorder(state, name, 0.05))
            )
        strategy.config.function_config.agent_tool_parallel_limit = 2
        calls = [make_tool_call(f"safe_{i}", call_id=str(i)) for i in range(6)]

        results = await strategy._run_tool_calls_concurrently(calls)

        assert state["peak"] == 2
        assert [r[0].id for r in results] == [str(i) for i in range(6)]
        assert [r[1] for r in results] == [f"result:safe_{i}" for i in range(6)]

    @pytest.mark.asyncio
    async def test_limit_of_one_is_serial(self, strategy):
        state: dict[str, Any] = {"active": 0, "peak": 0, "order": []}
        for i in range(3):
            name = f"safe_{i}"
            strategy.tools_manager.register_tool(
                make_tool_data(name, self._recorder(state, name, 0.01))
            )
        strategy.config.function_config.agent_tool_parallel_limit = 1
        calls = [make_tool_call(f"safe_{i}", call_id=str(i)) for i in range(3)]

        results = await strategy._run_tool_calls_concurrently(calls)

        assert state["peak"] == 1
        assert state["order"] == ["safe_0", "safe_1", "safe_2"]
        assert [r[1] for r in results] == [f"result:safe_{i}" for i in range(3)]

    @pytest.mark.asyncio
    async def test_unsafe_call_waits_for_the_pool_before_it(self, strategy):
        state: dict[str, Any] = {"active": 0, "peak": 0, "order": [], "finished": 0}
        for i in range(2):
            name = f"safe_{i}"
            strategy.tools_manager.register_tool(
                make_tool_data(name, self._recorder(state, name, 0.05))
            )

        async def writer(_arguments: dict[str, Any]) -> str:
            state["writer_saw_finished"] = state["finished"]
            return "wrote"

        strategy.tools_manager.register_tool(
            make_tool_data("write", writer, concurrency_safe=False)
        )
        original = strategy._run_tool_pool

        async def counting_pool(exec_one, tool_calls, group, results):
            await original(exec_one, tool_calls, group, results)
            state["finished"] = len([r for r in results if r is not None])

        strategy._run_tool_pool = counting_pool  # type: ignore[method-assign]
        calls = [
            make_tool_call("safe_0", call_id="1"),
            make_tool_call("safe_1", call_id="2"),
            make_tool_call("write", call_id="3"),
        ]

        results = await strategy._run_tool_calls_concurrently(calls)

        assert state["writer_saw_finished"] == 2
        assert [r[1] for r in results] == ["result:safe_0", "result:safe_1", "wrote"]

    @pytest.mark.asyncio
    async def test_one_failure_does_not_lose_sibling_results(self, strategy):
        async def failing(_arguments: dict[str, Any]) -> str:
            raise RuntimeError("tool exploded")

        strategy.tools_manager.register_tool(make_tool_data("bad", failing))
        strategy.tools_manager.register_tool(
            make_tool_data("good", AsyncMock(return_value="fine"))
        )
        strategy.config.function_config.agent_tool_parallel_limit = 1
        calls = [
            make_tool_call("good", call_id="1"),
            make_tool_call("bad", call_id="2"),
            make_tool_call("good", call_id="3"),
        ]

        results = await strategy._run_tool_calls_concurrently(calls)

        assert results[0][1] == "fine"
        assert results[1][1].startswith("ERR:")
        assert results[2][1] == "fine"


class TestDefaultRegistration:
    """Defaults kept for the shipped registration surfaces."""

    def test_on_tools_defaults_to_safe(self):
        manager = MultiToolsManager()
        from amrita_core.tools.manager import on_tools

        schema = FunctionDefinitionSchema(
            name="decorated",
            description="decorated tool",
            parameters=FunctionParametersSchema(type="object", properties={}),
        )

        @on_tools(data=schema, bound_to=manager)
        async def decorated(_arguments: dict[str, Any]) -> str:
            return "ok"

        tool = manager.get_tool("decorated")
        assert tool is not None
        assert tool.concurrency_safe is True

    def test_on_tools_forwards_false(self):
        manager = MultiToolsManager()
        from amrita_core.tools.manager import on_tools

        schema = FunctionDefinitionSchema(
            name="serial",
            description="serial tool",
            parameters=FunctionParametersSchema(type="object", properties={}),
        )

        @on_tools(data=schema, bound_to=manager, concurrency_safe=False)
        async def serial(_arguments: dict[str, Any]) -> str:
            return "ok"

        tool = manager.get_tool("serial")
        assert tool is not None
        assert tool.is_concurrency_safe({}) is False
