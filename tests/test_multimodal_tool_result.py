# pyright: reportArgumentType=false, reportIndexIssue=false, reportReturnType=false, reportIncompatibleMethodOverride=false, reportAttributeAccessIssue=false
"""Multimodal tool results: types, tool declarations, capability flags, gateway degradation.

The cases build malformed payloads on purpose (dicts with missing fields, a non-list
content, fake adapters), where type checking only fights the test intent, so the
relevant diagnostics are disabled for the whole file.
"""

from __future__ import annotations

import asyncio
import typing
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from amrita_sense.hook.matcher import Matcher

from amrita_core import libchat
from amrita_core.adapters.anthropic import AnthropicAdapter
from amrita_core.base.adapter import AdapterManager, FeatureFlag, ModelAdapter
from amrita_core.exceptions import UnsupportedContentError
from amrita_core.hook.event import FallbackContext
from amrita_core.libchat import (
    _prepare_payload,
    agentic_call_completion,
    call_completion,
)
from amrita_core.tools.manager import _is_content_list, simple_tool
from amrita_core.types import (
    File,
    FileContent,
    ImageContent,
    ImageUrl,
    Message,
    ModelPreset,
    TextContent,
    ToolCall,
    ToolResult,
    UniResponse,
)
from amrita_core.types.tool import content_text


def _image(url: str = "https://example.com/a.png") -> ImageContent:
    return ImageContent(image_url=ImageUrl(url=url))


def _file(name: str = "report.pdf") -> FileContent:
    return FileContent(
        file=File(filename=name, file_data="AAA", type="application/pdf")
    )


@pytest.fixture(autouse=True)
def _reset_degrade_warnings():
    """``_DEGRADE_WARNED`` is process-wide; stale state would leak between cases."""
    libchat._DEGRADE_WARNED.clear()
    yield
    libchat._DEGRADE_WARNED.clear()


class TestToolResultContent:
    """ToolResult content accepts plain text and a list of content blocks."""

    def test_str_content(self):
        result = ToolResult(role="tool", name="f", tool_call_id="1", content="done")
        assert result.text == "done"

    def test_block_content_is_coerced(self):
        result = ToolResult(
            role="tool",
            name="f",
            tool_call_id="1",
            content=[
                {"type": "text", "text": "see"},
                {"type": "image_url", "image_url": {"url": "https://e/x.png"}},
            ],
        )
        assert isinstance(result.content, list)
        assert isinstance(result.content[0], TextContent)
        assert isinstance(result.content[1], ImageContent)

    def test_text_view_marks_non_text_blocks(self):
        result = ToolResult(
            role="tool",
            name="f",
            tool_call_id="1",
            content=[TextContent(text="see"), _image()],
        )
        assert result.text == "see<image>"

    def test_roundtrip_keeps_block_payload(self):
        result = ToolResult(
            role="tool",
            name="f",
            tool_call_id="1",
            content=[TextContent(text="see"), _image()],
        )
        restored = ToolResult.model_validate(result.model_dump())
        assert restored.model_dump() == result.model_dump()
        assert restored.text == result.text

    def test_unknown_content_type_rejected(self):
        with pytest.raises(ValueError, match="Unknown content type"):
            ToolResult(
                role="tool",
                name="f",
                tool_call_id="1",
                content=[{"type": "not-registered"}],
            )

    def test_missing_type_rejected(self):
        with pytest.raises(ValueError, match="missing 'type'"):
            ToolResult(role="tool", name="f", tool_call_id="1", content=[{"text": "x"}])

    def test_content_text_helper_handles_none_and_str(self):
        assert content_text(None) == ""
        assert content_text("plain") == "plain"


class TestSimpleToolPassThrough:
    """simple_tool must not JSON-encode a content-block list."""

    def test_content_list_is_not_serialized(self):
        @simple_tool
        async def multimodal(q: str) -> str:
            """Return an image.

            Args:
                q (str): query
            """
            return [TextContent(text="see"), _image()]

        result = asyncio.run(multimodal({"q": "x"}))
        assert _is_content_list(result)
        assert isinstance(result[0], TextContent)

    def test_plain_list_still_json(self):
        @simple_tool
        async def listing(q: str) -> list:
            """Return a list.

            Args:
                q (str): query
            """
            return [1, 2, 3]

        result = asyncio.run(listing({"q": "x"}))
        assert result == "[\n    1,\n    2,\n    3\n]"


class TestFeatureFlag:
    """Capability flags and the legacy-field translation."""

    def test_defaults_are_closed(self):
        flag = FeatureFlag()
        assert flag.agentic_call is False
        assert flag.input_multimodal is False
        assert flag.tool_result_multimodal is False

    def test_frozen(self):
        with pytest.raises((FrozenInstanceError, AttributeError)):
            FeatureFlag().agentic_call = True  # type: ignore[misc]

    def test_legacy_supports_agentic_call_is_translated(self):
        class Legacy(ModelAdapter):
            __no_register__ = True
            __abstract__ = True
            supports_agentic_call = True

        assert Legacy.features.agentic_call is True
        assert Legacy.supports_agentic_call is True

    def test_explicit_features_wins(self):
        class Explicit(ModelAdapter):
            __no_register__ = True
            __abstract__ = True
            features = FeatureFlag(tool_result_multimodal=True)
            supports_agentic_call = True

        assert Explicit.features.tool_result_multimodal is True
        # The legacy field stays in sync so readers never see a stale value.
        assert Explicit.supports_agentic_call is False


class TestGatewayDegrade:
    """The gateway shapes the payload per target protocol without mutating history."""

    @staticmethod
    def _preset(protocol: str) -> ModelPreset:
        preset = ModelPreset()
        preset.protocol = protocol
        return preset

    def test_supported_adapter_payload_untouched(self):
        messages = [
            Message(role="user", content=[TextContent(text="hi"), _image()]),
            ToolResult(
                role="tool",
                name="f",
                tool_call_id="1",
                content=[TextContent(text="see"), _image()],
            ),
        ]
        payload = _prepare_payload(messages, self._preset("anthropic"))
        assert payload[0] is messages[0]
        assert payload[1] is messages[1]

    def test_unsupported_tool_result_raises_before_sending(self):
        result = ToolResult(
            role="tool",
            name="f",
            tool_call_id="1",
            content=[TextContent(text="see"), _image()],
        )
        messages = [
            Message(role="user", content="hi"),
            Message(role="assistant", content=None),
            result,
        ]
        with pytest.raises(UnsupportedContentError) as excinfo:
            _prepare_payload(messages, self._preset("openai"))
        exc = excinfo.value
        assert exc.protocol == "openai"
        assert exc.scope == "tool_result"
        assert exc.tool_call_ids == ("1",)
        assert "image" in exc.kinds
        # Raising must not rewrite the stored history; the image stays.
        assert any(isinstance(b, ImageContent) for b in result.content)

    def test_text_only_history_passes_through(self):
        messages = [Message(role="user", content="hi")]
        payload = _prepare_payload(messages, self._preset("openai"))
        assert payload[0] is messages[0]


class TestBlockLabel:
    """The text view and the degrade note share one set of labels."""

    def test_image_type_maps_to_readable_label(self):
        assert content_text([_image()]) == "<image>"

    def test_file_keeps_its_name(self):
        assert content_text([_file("a.pdf")]) == "<file:a.pdf>"

    def test_file_without_name_has_no_colon(self):
        block = FileContent(file=File(file_id="file-123"))
        assert content_text([block]) == "<file:file-123>"

    def test_mixed_blocks_keep_order(self):
        result = ToolResult(
            role="tool",
            name="f",
            tool_call_id="1",
            content=[TextContent(text="a"), _image(), TextContent(text="b")],
        )
        assert result.text == "a<image>b"


class TestDegradeWarning:
    """Degrade warnings are deduplicated per (protocol, kind), not per turn."""

    def test_warns_once_per_key(self):
        preset = ModelPreset()
        preset.protocol = "test-off"
        payload = [Message(role="user", content=[_image()])]
        with patch.object(libchat.logger, "warning") as warn:
            _prepare_payload(payload, preset)
            _prepare_payload(payload, preset)
        assert warn.call_count == 1
        assert "declares no input_multimodal" in warn.call_args.args[0]

    def test_tool_result_raises_while_input_only_warns(self):
        preset = ModelPreset()
        preset.protocol = "test-off"
        tool = ToolResult(role="tool", name="f", tool_call_id="1", content=[_image()])
        with pytest.raises(UnsupportedContentError):
            _prepare_payload([tool], preset)
        with patch.object(libchat.logger, "warning") as warn:
            _prepare_payload([Message(role="user", content=[_image()])], preset)
        assert "declares no input_multimodal" in warn.call_args.args[0]

    def test_supported_adapter_never_warns(self):
        preset = ModelPreset()
        preset.protocol = "anthropic"
        payload = [Message(role="user", content=[_image()])]
        with patch.object(libchat.logger, "warning") as warn:
            _prepare_payload(payload, preset)
        warn.assert_not_called()


class TestDegradedNoteUsesBlockLabel:
    """The degrade note and ``content_text`` must read as the same block."""

    def test_image_note_is_not_the_raw_type(self):
        preset = ModelPreset()
        preset.protocol = "test-off"
        payload = _prepare_payload([Message(role="user", content=[_image()])], preset)
        text = payload[0].content[0].text
        assert "<image omitted" in text
        assert "image_url" not in text

    def test_file_note_keeps_the_filename(self):
        preset = ModelPreset()
        preset.protocol = "test-off"
        payload = _prepare_payload(
            [Message(role="user", content=[_file("a.pdf")])], preset
        )
        assert "<file:a.pdf omitted" in payload[0].content[0].text


class _RecordingAdapter(ModelAdapter):
    """Record the payload the gateway actually sent, for end-to-end assertions."""

    __no_register__ = True
    __abstract__ = True
    calls: typing.ClassVar[list] = []

    def __init__(self, preset=None, config=None):
        self.preset = preset
        self.config = config

    async def call_api(self, messages, **kwargs):
        type(self).calls.append(list(messages))
        yield "ok"
        yield UniResponse(content="ok", tool_calls=None, usage=None)

    async def agentic_call_api(
        self,
        messages,
        tools=None,
        tool_choice=None,
        **kwargs,
    ):
        type(self).calls.append(list(messages))
        yield "ok"
        yield UniResponse(content="ok", tool_calls=[], usage=None)


def _install_adapter(protocol: str, flag: FeatureFlag) -> type[_RecordingAdapter]:
    """Register an adapter with the given flags; return its class so calls can be read."""

    class _Adapter(_RecordingAdapter):
        __override__ = True
        features = flag

        @staticmethod
        def get_adapter_protocol() -> str:
            return protocol

    _Adapter.calls = []
    AdapterManager().register_adapter(_Adapter)
    return _Adapter


async def _reflect(preset, call_func, config):
    """Hand the payload to the adapter, not to the ``_call_with_reflection`` shell."""
    adapter_cls = AdapterManager().safe_get_adapter(preset.protocol)
    assert adapter_cls is not None
    return await call_func(adapter_cls(preset, config))


def _preset(protocol: str, name: str = "p") -> ModelPreset:
    preset = ModelPreset(model="m", name=name, api_key="k", protocol=protocol)
    return preset


class TestGatewayEndToEnd:
    """The degraded payload really reached the adapter."""

    @pytest.mark.asyncio
    async def test_call_completion_sends_degraded_payload(self):
        adapter = _install_adapter(
            "test-e2e-off", FeatureFlag(agentic_call=True, input_multimodal=False)
        )
        message = Message(role="user", content=[TextContent(text="hi"), _image()])
        with patch("amrita_core.libchat._call_with_reflection", side_effect=_reflect):
            async for _ in call_completion([message], _preset("test-e2e-off")):
                pass

        sent = adapter.calls[0][0]
        assert all(block["type"] == "text" for block in sent["content"])
        # The object is not mutated in place; the image stays in history.
        assert any(isinstance(b, ImageContent) for b in message.content)

    @pytest.mark.asyncio
    async def test_call_completion_keeps_payload_when_supported(self):
        adapter = _install_adapter(
            "test-e2e-on",
            FeatureFlag(agentic_call=True, input_multimodal=True),
        )
        with patch("amrita_core.libchat._call_with_reflection", side_effect=_reflect):
            async for _ in call_completion(
                [Message(role="user", content=[_image()])], _preset("test-e2e-on")
            ):
                pass

        sent = adapter.calls[0][0]
        assert sent["content"][0]["type"] == "image_url"


class TestAgenticFallbackRenegotiates:
    """A fallback that swaps the preset must renegotiate the payload for the new protocol."""

    @pytest.mark.asyncio
    async def test_fallback_refuses_untransportable_tool_result(self):
        multi = _install_adapter(
            "test-agentic-multi",
            FeatureFlag(
                agentic_call=True, input_multimodal=True, tool_result_multimodal=True
            ),
        )
        text = _install_adapter(
            "test-agentic-text",
            FeatureFlag(
                agentic_call=True, input_multimodal=True, tool_result_multimodal=False
            ),
        )

        matcher = Matcher("PRESET_FALLBACK", priority=1)

        async def switch(ev: FallbackContext):
            ev.preset = _preset("test-agentic-text", "weak")

        matcher.handle()(switch)
        try:
            messages = [
                Message(role="user", content="hi"),
                Message(
                    role="assistant",
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="1",
                            function={"name": "shot", "arguments": "{}"},  # type: ignore[arg-type]
                        )
                    ],
                ),
                ToolResult(
                    role="tool",
                    name="shot",
                    tool_call_id="1",
                    content=[TextContent(text="see"), _image()],
                ),
            ]
            attempts = {"n": 0}

            async def flaky(preset, call_func, config):
                attempts["n"] += 1
                if attempts["n"] == 1:
                    raise RuntimeError("boom")
                return await _reflect(preset, call_func, config)

            with patch("amrita_core.libchat._call_with_reflection", side_effect=flaky):
                with pytest.raises(UnsupportedContentError) as excinfo:
                    async for _ in agentic_call_completion(
                        messages, preset=_preset("test-agentic-multi", "strong")
                    ):
                        pass
        finally:
            matcher._dead_at = datetime.now() - timedelta(minutes=1)

        # The first protocol failed before sending, so nothing was recorded.
        assert multi.calls == []
        # A capability gap is not retried; the weaker protocol sends nothing.
        assert text.calls == []
        assert excinfo.value.protocol == "test-agentic-text"
        # The stored history stays unchanged.
        assert isinstance(messages[2].content[1], ImageContent)


class TestAnthropicToolResultBlocks:
    """Anthropic ``tool_result`` carries blocks natively; images must not be flattened away."""

    def _messages(self, content: list) -> list[dict]:
        return [
            {"role": "user", "content": "screenshot please"},
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "shot", "arguments": "{}"},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_1", "content": content},
        ]

    def test_image_block_survives_into_tool_result(self):
        converted = AnthropicAdapter._convert_messages(
            self._messages(
                [
                    {"type": "text", "text": "captured"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/a.png"},
                    },
                ]
            )
        )
        tool_msg = converted[-1]
        assert tool_msg["role"] == "user"
        block = tool_msg["content"][0]
        assert block["type"] == "tool_result"
        assert block["tool_use_id"] == "call_1"
        assert block["content"] == [
            {"type": "text", "text": "captured"},
            {
                "type": "image",
                "source": {"type": "url", "url": "https://example.com/a.png"},
            },
        ]

    def test_inline_image_becomes_base64_source(self):
        converted = AnthropicAdapter._convert_messages(
            self._messages(
                [
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64,AAAA"},
                    }
                ]
            )
        )
        source = converted[-1]["content"][0]["content"][0]["source"]
        assert source == {"type": "base64", "media_type": "image/png", "data": "AAAA"}

    def test_plain_text_tool_result_stays_string(self):
        converted = AnthropicAdapter._convert_messages(self._messages("all good"))
        assert converted[-1]["content"][0]["content"] == "all good"


class TestAnthropicFileBlock:
    """A ``file`` block cannot be sent, but it must not vanish silently."""

    def test_file_block_leaves_a_note(self):
        blocks = AnthropicAdapter._convert_content_to_blocks(
            [{"type": "file", "file": {"filename": "a.pdf"}}]
        )
        assert blocks == [
            {
                "type": "text",
                "text": "<file:a.pdf omitted: this adapter cannot carry file blocks>",
            }
        ]

    def test_file_block_without_name_still_notes(self):
        blocks = AnthropicAdapter._convert_content_to_blocks(
            [{"type": "file", "file": {"file_id": "file-1"}}]
        )
        assert blocks[0]["type"] == "text"
        assert "file-1" in blocks[0]["text"]


class TestBuiltinAdapterDeclarations:
    """Built-in adapters flags are the only basis for gateway degradation."""

    def test_openai_declares_no_tool_result_multimodal(self):
        from amrita_core.adapters.openai import OpenAIAdapter

        assert OpenAIAdapter.features.agentic_call is True
        assert OpenAIAdapter.features.input_multimodal is True
        assert OpenAIAdapter.features.tool_result_multimodal is False

    def test_anthropic_declares_tool_result_multimodal(self):
        assert AnthropicAdapter.features.agentic_call is True
        assert AnthropicAdapter.features.input_multimodal is True
        assert AnthropicAdapter.features.tool_result_multimodal is True

    def test_legacy_flag_follows_the_declaration(self):
        from amrita_core.adapters.openai import OpenAIAdapter

        assert OpenAIAdapter.supports_agentic_call is True


class TestLegacyFlagKeepsInheritedFeatures:
    """The legacy field covers streaming only; it must not clear other inherited flags."""

    def test_child_disabling_agentic_call_keeps_multimodal(self):
        from amrita_core.adapters.openai import OpenAIAdapter

        class Child(OpenAIAdapter):
            __no_register__ = True
            __abstract__ = True
            supports_agentic_call = False

        assert Child.features.agentic_call is False
        # A subclass that only turns streaming off keeps the multimodal declarations.
        assert Child.features.input_multimodal is True

    def test_child_without_the_legacy_field_shares_the_parent_flag(self):
        from amrita_core.adapters.openai import OpenAIAdapter

        class Child(OpenAIAdapter):
            __no_register__ = True
            __abstract__ = True

        assert Child.features is OpenAIAdapter.features


class TestContentTextToleratesRawPayloads:
    """``StepToolReturnEvent.result`` skips validation; the text view must not raise."""

    def test_dict_blocks(self):
        assert content_text([{"type": "text", "text": "hi"}]) == "hi"

    def test_dict_image_block_uses_the_shared_label(self):
        assert (
            content_text([{"type": "image_url", "image_url": {"url": "https://e/a"}}])
            == "<image>"
        )

    def test_dict_file_block_keeps_the_name(self):
        assert content_text([{"type": "file", "file": {"filename": "a.pdf"}}]) == (
            "<file:a.pdf>"
        )

    def test_bare_strings(self):
        assert content_text(["a", "b"]) == "ab"

    def test_event_result_round_trips_into_text(self):
        from amrita_core.builtins.agent.events import StepToolReturnEvent

        ev = StepToolReturnEvent(
            step_index=0,
            phase=None,
            tool_name="t",
            tool_id="i",
            result=[{"type": "text", "text": "ok"}],
        )
        assert content_text(ev.result) == "ok"


class TestAnthropicSystemBlocks:
    """``system`` accepts text only, but flattening must not silently drop non-text blocks."""

    def test_system_image_leaves_a_note(self):
        converted = AnthropicAdapter._convert_messages(
            [
                {
                    "role": "system",
                    "content": [
                        {"type": "text", "text": "be nice"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "https://e/a.png"},
                        },
                    ],
                },
                {"role": "user", "content": "hi"},
            ]
        )
        assert converted[0]["role"] == "system"
        # system is flattened to text; this asserts that text.
        text = typing.cast(str, converted[0]["content"])
        assert "be nice" in text
        assert "<image omitted" in text
        assert "image_url" not in text

    def test_plain_system_text_is_untouched(self):
        converted = AnthropicAdapter._convert_messages(
            [
                {"role": "system", "content": "be nice"},
                {"role": "user", "content": "hi"},
            ]
        )
        assert converted[0]["content"] == "be nice"
