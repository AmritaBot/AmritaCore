"""Tests for the run-scoped usage ledger and its libchat gateway recording."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from amrita_core.libchat import call_completion, tools_caller
from amrita_core.types import (
    Message,
    UniResponse,
    UniResponseUsage,
)
from amrita_core.types.response import RequestMetadata
from amrita_core.usage import (
    SessionUsageProxy,
    UsageEntry,
    UsageLedger,
    UsageRegistry,
    UsageSnapshot,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Every test starts from an empty registry and cleans up after itself."""
    UsageRegistry._ledgers.clear()
    yield
    UsageRegistry._ledgers.clear()


@pytest.fixture
def preset():
    from amrita_core.types import ModelPreset

    preset = ModelPreset(model="gpt-3.5", name="usage-test", api_key="k")
    preset.config = MagicMock()
    preset.config.cot_model = False
    preset.config.stream = False
    preset.thinking_config = None
    return preset


@pytest.fixture
def config():
    from amrita_core.config import AmritaConfig

    return AmritaConfig()


def _mk_usage(
    prompt: int = 10, completion: int = 5, total: int = 15
) -> UniResponseUsage:
    return UniResponseUsage(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=total,
    )


class TestUsageLedger:
    def test_total_is_derived_sum(self):
        ledger = UsageLedger()
        ledger.add(UsageEntry(prompt_tokens=10, completion_tokens=2, total_tokens=12))
        ledger.add(UsageEntry(prompt_tokens=20, completion_tokens=3, total_tokens=23))
        total = ledger.total()
        assert total.prompt_tokens == 30
        assert total.completion_tokens == 5
        assert total.total_tokens == 35

    def test_prompt_since_filters_by_ts(self):
        ledger = UsageLedger()
        ledger.add(UsageEntry(prompt_tokens=10, total_tokens=10, ts=100.0))
        ledger.add(UsageEntry(prompt_tokens=20, total_tokens=20, ts=200.0))
        assert ledger.prompt_since(150.0) == 20
        assert ledger.prompt_since(0.0) == 30

    def test_entries_returns_copy(self):
        ledger = UsageLedger()
        ledger.add(UsageEntry(prompt_tokens=1, total_tokens=1))
        entries = ledger.entries()
        entries.clear()
        assert len(ledger.entries()) == 1


class TestUsageRegistry:
    def test_register_reuses_ledger_for_same_stream(self):
        p1 = UsageRegistry.register("s1")
        p2 = UsageRegistry.register("s1")
        p1.record(_mk_usage(5))
        assert p2.extra_total.prompt_tokens == 5

    def test_unregister_pops_registry(self):
        UsageRegistry.register("s1")
        assert "s1" in UsageRegistry._ledgers
        UsageRegistry.unregister("s1")
        assert "s1" not in UsageRegistry._ledgers

    def test_unregister_is_idempotent(self):
        UsageRegistry.unregister("never-registered")

    def test_proxy_after_unregister_returns_zero(self):
        proxy = UsageRegistry.register("s1")
        proxy.record(_mk_usage(5))
        UsageRegistry.unregister("s1")
        assert proxy.extra_total.prompt_tokens == 0
        assert proxy.prompt_since(0.0) == 0
        assert proxy.snapshot() is None


class TestSessionUsageProxy:
    def test_record_skips_none_usage(self):
        proxy = UsageRegistry.register("s1")
        proxy.record(None)
        assert proxy.extra_total.total_tokens == 0

    def test_record_stores_metadata(self):
        proxy = UsageRegistry.register("s1")
        proxy.record(_mk_usage(7, 3, 10), model="deepseek-chat", request_id="req-1")
        entries = UsageRegistry._ledgers["s1"].entries()
        assert entries[0].model == "deepseek-chat"
        assert entries[0].request_id == "req-1"

    def test_stateless_proxy_survives_copy(self):
        proxy = UsageRegistry.register("s1")
        copied = SessionUsageProxy(proxy.stream_id)
        proxy.record(_mk_usage(4))
        # No reference held: the copy still reads the same registry ledger.
        assert copied.extra_total.prompt_tokens == 4


class TestUsageSnapshot:
    def test_from_ledger_summarizes(self):
        ledger = UsageLedger()
        ledger.add(UsageEntry(prompt_tokens=10, completion_tokens=2, total_tokens=12))
        snap = UsageSnapshot.from_ledger("s1", ledger)
        assert snap.stream_id == "s1"
        assert snap.prompt_tokens == 10
        assert len(snap.entries) == 1

    def test_proxy_snapshot_roundtrip(self):
        proxy = UsageRegistry.register("s1")
        proxy.record(_mk_usage(6, 4, 10))
        snap = proxy.snapshot()
        assert snap is not None
        assert snap.total_tokens == 10


class TestLibchatGatewayRecording:
    @pytest.mark.asyncio
    async def test_call_completion_records_usage(self, preset, config):
        proxy = UsageRegistry.register("s1")

        async def fake_response():
            yield "hello"
            yield UniResponse(
                content="hi",
                tool_calls=None,
                usage=_mk_usage(11, 6, 17),
                metadata=RequestMetadata(model="m1", original_request_id="req-1"),
            )

        with patch(
            "amrita_core.libchat._call_with_reflection",
            return_value=lambda: fake_response(),
        ):
            collected = [
                c
                async for c in call_completion(
                    [Message(role="user", content="x")],
                    preset=preset,
                    config=config,
                    usage=proxy,
                )
            ]
        assert isinstance(collected[-1], UniResponse)
        entries = UsageRegistry._ledgers["s1"].entries()
        assert len(entries) == 1
        assert entries[0].prompt_tokens == 11
        assert entries[0].model == "m1"

    @pytest.mark.asyncio
    async def test_call_completion_no_usage_param_is_noop(self, preset, config):
        async def fake_response():
            yield UniResponse(content="hi", tool_calls=None, usage=_mk_usage(11, 6, 17))

        with patch(
            "amrita_core.libchat._call_with_reflection",
            return_value=lambda: fake_response(),
        ):
            collected = [
                c
                async for c in call_completion(
                    [Message(role="user", content="x")],
                    preset=preset,
                    config=config,
                    usage=None,
                )
            ]
        assert isinstance(collected[-1], UniResponse)
        assert UsageRegistry._ledgers == {}

    @pytest.mark.asyncio
    async def test_call_completion_usage_none_response_not_recorded(
        self, preset, config
    ):
        proxy = UsageRegistry.register("s1")

        async def fake_response():
            yield UniResponse(content="hi", tool_calls=None, usage=None)

        with patch(
            "amrita_core.libchat._call_with_reflection",
            return_value=lambda: fake_response(),
        ):
            collected = [
                c
                async for c in call_completion(
                    [Message(role="user", content="x")],
                    preset=preset,
                    config=config,
                    usage=proxy,
                )
            ]
        assert isinstance(collected[-1], UniResponse)
        assert UsageRegistry._ledgers["s1"].entries() == []

    @pytest.mark.asyncio
    async def test_tools_caller_records_usage(self, preset, config):
        proxy = UsageRegistry.register("s1")

        async def fake_tools(preset_arg, call_func, config_arg):
            return UniResponse(
                role="assistant",
                content=None,
                tool_calls=None,
                usage=_mk_usage(30, 15, 45),
                metadata=RequestMetadata(model="m2", original_request_id="req-2"),
            )

        with patch("amrita_core.libchat._call_with_reflection", side_effect=fake_tools):
            resp = await tools_caller(
                [Message(role="user", content="x")],
                tools=[],
                preset=preset,
                config=config,
                usage=proxy,
            )
        assert resp.usage is not None
        entries = UsageRegistry._ledgers["s1"].entries()
        assert len(entries) == 1
        assert entries[0].completion_tokens == 15

    @pytest.mark.asyncio
    async def test_tools_caller_no_usage_param_is_noop(self, preset, config):
        async def fake_tools(preset_arg, call_func, config_arg):
            return UniResponse(
                role="assistant",
                content=None,
                tool_calls=None,
                usage=_mk_usage(30, 15, 45),
            )

        with patch("amrita_core.libchat._call_with_reflection", side_effect=fake_tools):
            await tools_caller(
                [Message(role="user", content="x")],
                tools=[],
                preset=preset,
                config=config,
            )
        assert UsageRegistry._ledgers == {}


class TestGatewayDoubleLedgerSeparation:
    @pytest.mark.asyncio
    async def test_tools_and_completion_accumulate_independently(self, preset, config):
        """Final completion (no usage param) and process calls (with proxy)
        land in different ledgers: the final response usage stays on the
        UniResponse, the process usage accumulates on the proxy."""
        proxy = UsageRegistry.register("s1")

        async def fake_tools(preset_arg, call_func, config_arg):
            return UniResponse(
                role="assistant",
                content=None,
                tool_calls=None,
                usage=_mk_usage(100, 50, 150),
            )

        async def fake_response():
            yield UniResponse(
                content="final", tool_calls=None, usage=_mk_usage(200, 100, 300)
            )

        with patch("amrita_core.libchat._call_with_reflection", side_effect=fake_tools):
            await tools_caller(
                [Message(role="user", content="x")],
                tools=[],
                preset=preset,
                config=config,
                usage=proxy,
            )
        with patch(
            "amrita_core.libchat._call_with_reflection",
            return_value=lambda: fake_response(),
        ):
            collected = [
                c
                async for c in call_completion(
                    [Message(role="user", content="x")],
                    preset=preset,
                    config=config,
                    usage=None,
                )
            ]
        final = collected[-1]
        assert isinstance(final, UniResponse)
        # Final completion usage stays on the response, not the process ledger.
        assert final.usage is not None
        assert final.usage.total_tokens == 300
        assert proxy.extra_total.total_tokens == 150
