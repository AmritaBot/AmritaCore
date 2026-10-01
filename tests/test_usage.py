"""Tests for the run-scoped billing ledger and its libchat gateway recording."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from amrita_core.builtins.backends import LegacyBackend
from amrita_core.libchat import call_completion, tools_caller
from amrita_core.types import (
    BillingRecord,
    Message,
    RateConfig,
    UniResponse,
    UniResponseUsage,
)
from amrita_core.types.response import RequestMetadata
from amrita_core.usage import SessionUsageProxy


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


class TestBillingRecord:
    def test_rate_survives_json_roundtrip(self):
        rate = RateConfig(
            per=1000, input=Decimal("0.00014"), output=Decimal("0.00028")
        )
        record = BillingRecord(model="m", preset_name="p", rate=rate, total_tokens=10)
        restored = BillingRecord.model_validate(record.model_dump(mode="json"))
        assert restored.rate is not None
        assert restored.rate.input == Decimal("0.00014")

    def test_defaults_are_empty(self):
        record = BillingRecord()
        assert record.rate is None
        assert record.preset_name is None
        assert record.total_tokens == 0


class TestLegacyBillingBackend:
    @pytest.mark.asyncio
    async def test_commit_and_load(self):
        backend = LegacyBackend()
        await backend.commit_billing("s1", [BillingRecord(model="m", total_tokens=7)])
        records = await backend.load_billing("s1")
        assert len(records) == 1
        assert records[0].model == "m"

    @pytest.mark.asyncio
    async def test_commit_is_append_only(self):
        backend = LegacyBackend()
        await backend.commit_billing("s1", [BillingRecord(total_tokens=1)])
        await backend.commit_billing("s1", [BillingRecord(total_tokens=2)])
        assert len(await backend.load_billing("s1")) == 2

    @pytest.mark.asyncio
    async def test_empty_commit_is_noop(self):
        backend = LegacyBackend()
        await backend.commit_billing("s1", [])
        assert await backend.load_billing("s1") == []

    @pytest.mark.asyncio
    async def test_sessions_are_isolated(self):
        backend = LegacyBackend()
        await backend.commit_billing("s1", [BillingRecord(total_tokens=1)])
        assert await backend.load_billing("s2") == []

    @pytest.mark.asyncio
    async def test_load_returns_copy(self):
        backend = LegacyBackend()
        await backend.commit_billing("s1", [BillingRecord(total_tokens=1)])
        loaded = await backend.load_billing("s1")
        loaded.clear()
        assert len(await backend.load_billing("s1")) == 1


class TestSessionUsageProxy:
    def test_record_skips_none_usage(self):
        proxy = SessionUsageProxy("s1", "r1")
        proxy.record(None)
        assert proxy.extra_total.total_tokens == 0

    def test_record_captures_metadata(self):
        proxy = SessionUsageProxy("s1", "r1")
        rate = RateConfig(input=Decimal("1"))
        proxy.record(
            _mk_usage(7, 3, 10),
            model="deepseek-chat",
            preset_name="fast",
            rate=rate,
            request_id="req-1",
        )
        record = proxy.records[0]
        assert record.model == "deepseek-chat"
        assert record.preset_name == "fast"
        assert record.rate is rate
        assert record.request_id == "req-1"
        assert record.session_id == "s1"
        assert record.stream_id == "r1"

    def test_extra_total_sums_records(self):
        proxy = SessionUsageProxy("s1", "r1")
        proxy.record(_mk_usage(10, 2, 12))
        proxy.record(_mk_usage(20, 3, 23))
        total = proxy.extra_total
        assert total.prompt_tokens == 30
        assert total.completion_tokens == 5
        assert total.total_tokens == 35

    def test_prompt_since_filters_by_ts(self):
        proxy = SessionUsageProxy("s1", "r1")
        proxy.record(_mk_usage(prompt=10))
        proxy._records[0].ts = 100.0
        proxy.record(_mk_usage(prompt=20))
        proxy._records[1].ts = 200.0
        assert proxy.prompt_since(150.0) == 20
        assert proxy.prompt_since(0.0) == 30

    def test_records_returns_copy(self):
        proxy = SessionUsageProxy("s1", "r1")
        proxy.record(_mk_usage())
        records = proxy.records
        records.clear()
        assert len(proxy.records) == 1

    def test_flush_into_appends(self):
        proxy = SessionUsageProxy("s1", "r1")
        proxy.record(_mk_usage(prompt=5))
        target: list[BillingRecord] = []
        proxy.flush_into(target)
        assert len(target) == 1
        assert target[0].prompt_tokens == 5

    def test_flush_into_is_idempotent(self):
        proxy = SessionUsageProxy("s1", "r1")
        proxy.record(_mk_usage(prompt=5))
        target: list[BillingRecord] = []
        proxy.flush_into(target)
        proxy.flush_into(target)
        assert len(target) == 1

    def test_flush_into_only_appends_new_records(self):
        proxy = SessionUsageProxy("s1", "r1")
        target: list[BillingRecord] = []
        proxy.record(_mk_usage(prompt=5))
        proxy.flush_into(target)
        proxy.record(_mk_usage(prompt=7))
        proxy.flush_into(target)
        assert [r.prompt_tokens for r in target] == [5, 7]

    @pytest.mark.asyncio
    async def test_commit_forwards_to_backend(self):
        backend = LegacyBackend()
        proxy = SessionUsageProxy("s1", "r1", backend=backend)
        proxy.record(_mk_usage(prompt=9))
        await proxy.commit()
        records = await backend.load_billing("s1")
        assert len(records) == 1
        assert records[0].prompt_tokens == 9

    @pytest.mark.asyncio
    async def test_commit_without_backend_is_noop(self):
        proxy = SessionUsageProxy("s1", "r1")
        proxy.record(_mk_usage())
        await proxy.commit()


class TestLibchatGatewayRecording:
    @pytest.mark.asyncio
    async def test_call_completion_records_usage(self, preset, config):
        proxy = SessionUsageProxy("s1", "r1")

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
        records = proxy.records
        assert len(records) == 1
        assert records[0].prompt_tokens == 11
        assert records[0].model == "m1"
        assert records[0].preset_name == "usage-test"

    @pytest.mark.asyncio
    async def test_call_completion_captures_rate_snapshot(self, preset, config):
        preset.rate = RateConfig(input=Decimal("0.001"), output=Decimal("0.002"))
        proxy = SessionUsageProxy("s1", "r1")

        async def fake_response():
            yield UniResponse(content="hi", tool_calls=None, usage=_mk_usage(11, 6, 17))

        with patch(
            "amrita_core.libchat._call_with_reflection",
            return_value=lambda: fake_response(),
        ):
            async for _ in call_completion(
                [Message(role="user", content="x")],
                preset=preset,
                config=config,
                usage=proxy,
            ):
                pass
        assert proxy.records[0].rate is preset.rate

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

    @pytest.mark.asyncio
    async def test_call_completion_usage_none_response_not_recorded(
        self, preset, config
    ):
        proxy = SessionUsageProxy("s1", "r1")

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
        assert proxy.records == []

    @pytest.mark.asyncio
    async def test_tools_caller_records_usage(self, preset, config):
        proxy = SessionUsageProxy("s1", "r1")

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
        records = proxy.records
        assert len(records) == 1
        assert records[0].completion_tokens == 15

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


class TestGatewayLedgerSeparation:
    @pytest.mark.asyncio
    async def test_tools_and_completion_accumulate_independently(self, preset, config):
        """The final completion (no usage param) stays on the UniResponse,
        while process calls accumulate on the proxy."""
        proxy = SessionUsageProxy("s1", "r1")

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
            async for _ in call_completion(
                [Message(role="user", content="x")],
                preset=preset,
                config=config,
                usage=proxy,
            ):
                pass

        assert len(proxy.records) == 2
        assert proxy.extra_total.total_tokens == 450
