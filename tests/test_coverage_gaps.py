"""Targeted tests for uncovered branches after ChatObject DI refactor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from unittest.mock import MagicMock

import pytest
from jinja2 import Template

from amrita_core.agent.context import StrategyContext
from amrita_core.agent.strategy import AgentStrategy, StrategyLikedObject
from amrita_core.base.backend import BackendSlots
from amrita_core.builtins.backends import LegacyBackend
from amrita_core.chatmanager import ChatObject
from amrita_core.config import AmritaConfig, set_config
from amrita_core.contexts import (
    AbilityContext,
    AbilityState,
    DatabackendOptions,
    GeneralInput,
    MemoryContext,
    RespState,
    SessionMetadata,
    StateContext,
    WorkingState,
)
from amrita_core.types import (
    Message,
    ModelPreset,
    SendMessageWrap,
    ToolCall,
    UniResponse,
    UniResponseUsage,
)
from amrita_core.types.memory import MemoryModel
from amrita_core.types.tool import Function

if TYPE_CHECKING:
    pass


@pytest.fixture(autouse=True)
def setup_global() -> None:
    set_config(AmritaConfig())


def _make_chat_obj(**overrides) -> ChatObject:
    preset = ModelPreset(model="gpt-3.5", name="t", api_key="k")
    kwargs: dict = {
        "train": {"role": "system", "content": "sys"},
        "user_input": "hello",
        "session_id": "di-test",
        "preset": preset,
    }
    kwargs.update(overrides)
    return ChatObject(**kwargs)


class _CallToolTestAgent(AgentStrategy):
    async def single_execute(self) -> bool:  # type: ignore[override]
        return False

    async def run(self) -> None:  # type: ignore[override]
        pass

    @classmethod
    def get_category(cls) -> Literal["workflow"]:
        return "workflow"


class _TestStrategyLiked(StrategyLikedObject):
    async def single_execute(self) -> bool:  # type: ignore[override]
        return False

    async def run(self) -> None:  # type: ignore[override]
        pass

    @classmethod
    def get_category(cls) -> Literal["workflow"]:
        return "workflow"


def _simple_ip() -> GeneralInput:
    return GeneralInput(
        user_input="hi",
        train=Message(role="system", content="sys"),
        template=Template(""),
        jinja2_vars={},
    )


def _make_ability_context() -> AbilityContext:
    """AbilityContext with a valid presets manager so get_default_preset works."""
    from amrita_core.preset import PresetManager

    pm = PresetManager()
    try:
        pm.add_preset(ModelPreset(model="gpt-3.5", name="cov-gap-default", api_key="k"))
    except ValueError:
        pass  # already registered from previous test
    return AbilityContext(presets=pm)


# ============================================================================
# 1. ChatObject property delegation
# ============================================================================


class TestChatObjectDIProperties:
    def test_stream_id_property(self):
        co = _make_chat_obj()
        assert co.stream_id == co._di_session.stream_id

    def test_stream_id_setter(self):
        co = _make_chat_obj()
        co.stream_id = "custom-stream"
        assert co._di_session.stream_id == "custom-stream"

    def test_timestamp_and_time(self):
        co = _make_chat_obj()
        assert co.timestamp == co._di_session.timestamp
        assert co.time == co._di_session.time

    def test_config_setter(self):
        co = _make_chat_obj()
        new_cfg = AmritaConfig()
        co.config = new_cfg
        assert co._di_ability.config is new_cfg

    def test_preset_setter_then_getter(self):
        co = _make_chat_obj()
        new_preset = ModelPreset(model="gpt-4", name="t2", api_key="k2")
        co.preset = new_preset
        assert co.preset is new_preset

    def test_preset_getter_asserts_when_none(self):
        co = _make_chat_obj()
        co._di_ability.preset = None
        with pytest.raises(AssertionError, match="preset has not been loaded"):
            _ = co.preset

    def test_slot_delegates_to_ability(self):
        co = _make_chat_obj()
        assert co.slot is co._di_ability.slot

    def test_strategy_setter(self):
        co = _make_chat_obj()

        class DummyStg(AgentStrategy):
            async def single_execute(self) -> bool:  # type: ignore[override]
                return False

            async def run(self) -> None:  # type: ignore[override]
                pass

            @classmethod
            def get_category(cls) -> Literal["workflow"]:
                return "workflow"

        co.strategy = DummyStg
        assert co._di_agent.strategy is DummyStg

    def test_state_setter_syncs_to_di(self):
        co = _make_chat_obj()
        state = StateContext(session_id="from-state")
        co.state = state
        assert co._state is state
        assert co._di_memory.memory is state.memory
        assert co._di_ability.ability is state.ability
        assert co._di_session.session_id == "from-state"

    def test_state_getter_synthesizes(self):
        co = _make_chat_obj()
        co._state = None
        co._di_memory.memory = None
        co._di_ability.ability = None
        s = co.state
        assert isinstance(s, StateContext)
        assert s.session_id == co._di_session.session_id

    def test_user_input_property(self):
        co = _make_chat_obj()
        assert co.user_input == "hello"

    def test_train_setter(self):
        co = _make_chat_obj()
        new_train = Message(role="system", content="new sys")
        co.train = new_train
        assert co._di_input.train is new_train

    def test_template_and_jinja2_vars(self):
        tmpl = Template("hello {{ name }}")
        co = _make_chat_obj(train_template=tmpl, jinja2_vars={"name": "world"})
        assert co.template is tmpl
        assert co.jinja2_vars == {"name": "world"}

    def test_data_setter_non_existent_di_memory(self):
        co = _make_chat_obj()
        del co._di_memory
        co.data = MemoryModel()
        assert co._di_memory.memory is not None

    def test_data_getter_raises_when_memory_none(self):
        co = _make_chat_obj()
        co._di_memory.memory = None
        with pytest.raises(RuntimeError, match="Memory not initialized"):
            _ = co.data


# ============================================================================
# 2. StrategyLikedObject.__call__ and AgentStrategy.call_tool
# ============================================================================


class TestStrategyLikedCall:
    def test_call_binds_context(self):
        co = MagicMock(spec=ChatObject)
        co.io_stream = MagicMock()
        wrap = SendMessageWrap(
            train=Message(role="system", content="sys"),
            memory=[Message(role="user", content="hi")],
            user_query=Message(role="user", content="hi"),
        )
        ctx = StrategyContext(user_input="hi", original_context=wrap, chat_object=co)
        inst = _TestStrategyLiked()
        result = inst(ctx)
        assert result is inst
        assert inst.ctx is ctx
        assert inst.chat_object is co
        assert inst.tools_manager is not None


class TestCallTool:
    @pytest.mark.asyncio
    async def test_tool_not_found(self):
        tm = MagicMock()
        tm.get_tool.return_value = None
        state = StateContext(session_id="s1", ability=AbilityContext(tools=tm))
        co = MagicMock()
        co.state = state
        co.io_stream = MagicMock()
        wrap = SendMessageWrap(
            train=Message(role="system", content="sys"),
            memory=[Message(role="user", content="x")],
            user_query=Message(role="user", content="x"),
        )
        ctx = StrategyContext(user_input="x", original_context=wrap, chat_object=co)
        inst = _CallToolTestAgent(ctx)
        tc = ToolCall(
            id="call-1",
            type="function",
            function=Function(name="nonexistent", arguments="{}"),
        )
        with pytest.raises(RuntimeError, match="Received unexpected tool call"):
            await inst.call_tool(tc)

    @pytest.mark.asyncio
    async def test_custom_run_returns_none(self):
        async def _none(tc) -> str | None:
            return None

        fake = MagicMock()
        fake.custom_run = True
        fake.func = _none
        tm = MagicMock()
        tm.get_tool.return_value = fake
        state = StateContext(session_id="s1", ability=AbilityContext(tools=tm))
        co = MagicMock()
        co.state = state
        co.io_stream = MagicMock()
        wrap = SendMessageWrap(
            train=Message(role="system", content="sys"),
            memory=[Message(role="user", content="x")],
            user_query=Message(role="user", content="x"),
        )
        ctx = StrategyContext(user_input="x", original_context=wrap, chat_object=co)
        inst = _CallToolTestAgent(ctx)
        tc = ToolCall(
            id="call-1",
            type="function",
            function=Function(name="custom-tool", arguments="{}"),
        )
        r = await inst.call_tool(tc)
        assert r == "(this tool returned no content)"

    @pytest.mark.asyncio
    async def test_normal_path(self):
        async def _tool(args: dict) -> str:
            return "result"

        fake = MagicMock()
        fake.custom_run = False
        fake.func = _tool
        tm = MagicMock()
        tm.get_tool.return_value = fake
        state = StateContext(session_id="s1", ability=AbilityContext(tools=tm))
        co = MagicMock()
        co.state = state
        co.io_stream = MagicMock()
        wrap = SendMessageWrap(
            train=Message(role="system", content="sys"),
            memory=[Message(role="user", content="x")],
            user_query=Message(role="user", content="x"),
        )
        ctx = StrategyContext(user_input="x", original_context=wrap, chat_object=co)
        inst = _CallToolTestAgent(ctx)
        tc = ToolCall(
            id="call-1",
            type="function",
            function=Function(name="normal-tool", arguments="{}"),
        )
        r = await inst.call_tool(tc)
        assert r == "result"


# ============================================================================
# 3. Components direct func call coverage
# ============================================================================


class TestProcessComponents:
    @pytest.mark.asyncio
    async def test_load_state_skip_mcp_tools(self):
        from amrita_core.components.process import LOAD_STATE

        opt = DatabackendOptions(skip_mcp_fetch=True, skip_tools_fetch=True)
        ab = AbilityState(
            config=AmritaConfig(),
            slot=BackendSlots(LegacyBackend(), LegacyBackend()),
        )
        ab.ability = _make_ability_context()
        await LOAD_STATE.func(
            opt=opt,
            ability=ab,
            meta=SessionMetadata(session_id="partial"),
            mem=MemoryContext(),
            rt_payload=WorkingState(),
            ip=_simple_ip(),
        )
        assert ab.ability is not None

    @pytest.mark.asyncio
    async def test_load_state_skip_all(self):
        from amrita_core.components.process import LOAD_STATE

        opt = DatabackendOptions(
            skip_mcp_fetch=True,
            skip_tools_fetch=True,
            skip_presets_fetch=True,
            skip_memory_fetch=True,
        )
        slot = BackendSlots(LegacyBackend(), LegacyBackend())
        ab = AbilityState(config=AmritaConfig(), slot=slot)
        ab.ability = _make_ability_context()
        mem = MemoryContext()
        await LOAD_STATE.func(
            opt=opt,
            ability=ab,
            meta=SessionMetadata(session_id="skip-all"),
            mem=mem,
            rt_payload=WorkingState(),
            ip=_simple_ip(),
        )
        assert mem.memory is None

    @pytest.mark.asyncio
    async def test_load_state_allocates_ability(self):
        from amrita_core.components.process import LOAD_STATE

        opt = DatabackendOptions(skip_memory_fetch=True)
        slot = BackendSlots(LegacyBackend(), LegacyBackend())
        ab = AbilityState(config=AmritaConfig(), slot=slot)
        ab.ability = None
        await LOAD_STATE.func(
            opt=opt,
            ability=ab,
            meta=SessionMetadata(session_id="alloc"),
            mem=MemoryContext(),
            rt_payload=WorkingState(),
            ip=_simple_ip(),
        )
        assert isinstance(ab.ability, AbilityContext)

    def test_append_response_value_error(self):
        from amrita_core.components.process import APPEND_RESPONSE

        wok = WorkingState(context_wrap=MagicMock())
        resp = RespState(response=None)
        with pytest.raises(ValueError, match="Response is None"):
            APPEND_RESPONSE.func(rt_payload=wok, resp=resp)

    def test_append_response_runtime_error(self):
        from amrita_core.components.process import APPEND_RESPONSE

        wok = WorkingState(context_wrap=None)
        usage = UniResponseUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        resp = RespState(
            response=UniResponse(content="ok", tool_calls=[], usage=usage),
        )
        with pytest.raises(RuntimeError, match="not set"):
            APPEND_RESPONSE.func(rt_payload=wok, resp=resp)

    def test_append_response_success(self):
        from amrita_core.components.process import APPEND_RESPONSE

        wrap = SendMessageWrap.validate_messages(
            [Message(role="system", content="sys"), Message(role="user", content="hi")]
        )
        wok = WorkingState(context_wrap=wrap)
        usage = UniResponseUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
        resp = RespState(
            response=UniResponse(content="ok", tool_calls=[], usage=usage),
        )
        APPEND_RESPONSE.func(rt_payload=wok, resp=resp)
        assert wok.context_wrap is not None
        assert wok.context_wrap.end_messages[-1].content == "ok"

    def test_apply_context_memory_none(self):
        from amrita_core.components.process import APPLY_CONTEXT

        mem = MemoryContext(memory=None)
        wok = WorkingState(context_wrap=MagicMock())
        with pytest.raises(RuntimeError, match="Memory is not set"):
            APPLY_CONTEXT.func(mem=mem, rt_payload=wok)

    def test_apply_context_wrap_none(self):
        from amrita_core.components.process import APPLY_CONTEXT

        mem = MemoryContext(memory=MemoryModel())
        wok = WorkingState(context_wrap=None)
        with pytest.raises(RuntimeError, match="Context wrap is not set"):
            APPLY_CONTEXT.func(mem=mem, rt_payload=wok)

    def test_apply_context_success(self):
        from amrita_core.components.process import APPLY_CONTEXT

        msgs = [
            Message(role="system", content="sys"),
            Message(role="assistant", content="hi"),
            Message(role="user", content="q"),
        ]
        wrap = SendMessageWrap.validate_messages(msgs)
        mem = MemoryContext(memory=MemoryModel(messages=[]))
        wok = WorkingState(context_wrap=wrap)
        APPLY_CONTEXT.func(mem=mem, rt_payload=wok)
        assert len(mem.memory.messages) > 0  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_commit_memory_skip(self):
        from amrita_core.components.process import COMMIT_MEMORY

        opt = DatabackendOptions(skip_memory_commit=True)
        slot = BackendSlots(LegacyBackend(), LegacyBackend())
        ab = AbilityState(config=AmritaConfig(), slot=slot)
        await COMMIT_MEMORY.func(
            opt=opt,
            ability=ab,
            meta=SessionMetadata(session_id="no-commit"),
            mem=MemoryContext(memory=MemoryModel()),
        )
