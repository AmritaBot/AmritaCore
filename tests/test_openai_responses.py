"""OpenAI Responses adapter: payload shape, stateless request, streaming assembly."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from amrita_core.adapters.openai_responses import (
    OpenAIResponsesAdapter,
    _content_parts,
    _to_input_items,
    _to_tool_choice,
    _to_tools,
)
from amrita_core.config import AmritaConfig
from amrita_core.tools.models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    ToolFunctionSchema,
)
from amrita_core.types import ModelPreset, UniResponse


def _preset(stream: bool = False) -> ModelPreset:
    preset = ModelPreset(
        model="gpt-5", name="p", api_key="k", protocol="openai-responses"
    )
    preset.config.stream = stream
    return preset


def _adapter(stream: bool = False) -> OpenAIResponsesAdapter:
    return OpenAIResponsesAdapter(_preset(stream), AmritaConfig())


def _tool() -> ToolFunctionSchema:
    return ToolFunctionSchema(
        function=FunctionDefinitionSchema(
            name="shot",
            description="take a screenshot",
            parameters=FunctionParametersSchema(
                type="object", properties={}, required=[]
            ),
        ),
        strict=True,
    )


def _tool_messages() -> list[dict]:
    return [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "screenshot please"},
        {
            "role": "assistant",
            "content": "taking it",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "shot", "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "name": "shot",
            "content": [
                {"type": "text", "text": "see"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA"}},
            ],
        },
    ]


class TestConversion:
    def test_assistant_tool_calls_become_separate_items(self):
        items = _to_input_items(_tool_messages())
        assert items[0] == {
            "type": "message",
            "role": "system",
            "content": [{"type": "input_text", "text": "be brief"}],
        }
        assistant = items[2]
        assert assistant["type"] == "message"
        assert assistant["content"] == [{"type": "output_text", "text": "taking it"}]
        call = items[3]
        assert call == {
            "type": "function_call",
            "call_id": "call_1",
            "name": "shot",
            "arguments": "{}",
        }

    def test_tool_result_carries_image_parts(self):
        items = _to_input_items(_tool_messages())
        output = items[4]
        assert output["type"] == "function_call_output"
        assert output["call_id"] == "call_1"
        assert output["output"] == [
            {"type": "input_text", "text": "see"},
            {"type": "input_image", "image_url": "data:image/png;base64,AA"},
        ]

    def test_plain_text_tool_result_stays_a_string(self):
        items = _to_input_items(
            [{"role": "tool", "tool_call_id": "c", "content": "done"}]
        )
        assert items[0]["output"] == "done"

    def test_file_block_becomes_input_file(self):
        parts = _content_parts(
            [
                {
                    "type": "file",
                    "file": {
                        "filename": "a.pdf",
                        "file_data": "AAA",
                        "type": "application/pdf",
                    },
                }
            ]
        )
        assert parts == [
            {
                "type": "input_file",
                "file_data": "AAA",
                "filename": "a.pdf",
            }
        ]

    def test_image_in_assistant_history_is_noted(self):
        parts = _content_parts(
            [{"type": "image_url", "image_url": {"url": "https://e/x.png"}}],
            assistant=True,
        )
        assert parts[0]["type"] == "output_text"
        assert "omitted" in parts[0]["text"]

    def test_tools_are_flattened(self):
        converted = _to_tools([_tool()])
        assert converted == [
            {
                "type": "function",
                "name": "shot",
                "description": "take a screenshot",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
                "strict": True,
            }
        ]

    def test_tool_choice_shapes(self):
        assert _to_tool_choice(None) == "auto"
        assert _to_tool_choice("required") == "required"
        assert _to_tool_choice(_tool()) == {"type": "function", "name": "shot"}


class _FakeStream:
    def __init__(self, events):
        self._events = list(events)
        self.response = SimpleNamespace(headers={})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._events:
            raise StopAsyncIteration
        return self._events.pop(0)


def _stream_events() -> list:
    return [
        SimpleNamespace(
            type="response.output_item.added",
            item=SimpleNamespace(
                type="function_call",
                id="item_1",
                call_id="call_1",
                name="shot",
                arguments="",
            ),
        ),
        SimpleNamespace(
            type="response.function_call_arguments.delta",
            item_id="item_1",
            delta='{"a"',
        ),
        SimpleNamespace(
            type="response.function_call_arguments.delta", item_id="item_1", delta=":1}"
        ),
        SimpleNamespace(type="response.output_text.delta", delta="Hel"),
        SimpleNamespace(type="response.output_text.delta", delta="lo"),
        SimpleNamespace(
            type="response.completed",
            response=SimpleNamespace(
                id="resp_1",
                model="gpt-5",
                status="completed",
                output=[],
                usage=SimpleNamespace(
                    input_tokens=10,
                    output_tokens=5,
                    total_tokens=15,
                    input_tokens_details=SimpleNamespace(cached_tokens=3),
                ),
            ),
        ),
    ]


class TestRequests:
    @pytest.mark.asyncio
    async def test_stateless_request_shape(self):
        adapter = _adapter(stream=False)
        fake_client = SimpleNamespace(
            responses=SimpleNamespace(
                create=AsyncMock(
                    return_value=SimpleNamespace(
                        output=[
                            SimpleNamespace(
                                type="function_call",
                                call_id="call_1",
                                name="shot",
                                arguments="{}",
                            )
                        ],
                        usage=None,
                        model="gpt-5",
                        id="resp_1",
                        status="completed",
                    )
                )
            )
        )
        with patch(
            "amrita_core.adapters.openai_responses.openai.AsyncOpenAI",
            return_value=fake_client,
        ):
            await adapter.call_tools(_tool_messages(), [_tool()], "auto")

        kwargs = fake_client.responses.create.call_args.kwargs
        assert kwargs["store"] is False
        assert "previous_response_id" not in kwargs
        assert kwargs["input"][-1]["type"] == "function_call_output"
        assert kwargs["tools"][0]["name"] == "shot"
        assert kwargs["tool_choice"] == "auto"

    @pytest.mark.asyncio
    async def test_streaming_assembles_text_and_tool_calls(self):
        adapter = _adapter(stream=True)
        fake_client = SimpleNamespace(
            responses=SimpleNamespace(
                create=AsyncMock(return_value=_FakeStream(_stream_events()))
            )
        )
        chunks = []
        with patch(
            "amrita_core.adapters.openai_responses.openai.AsyncOpenAI",
            return_value=fake_client,
        ):
            async for chunk in adapter.agentic_call_api(
                _tool_messages(), tools=[_tool()]
            ):
                chunks.append(chunk)

        text = "".join(c for c in chunks if isinstance(c, str))
        final = chunks[-1]
        assert text == "Hello"
        assert isinstance(final, UniResponse)
        assert final.content == "Hello"
        assert final.tool_calls is not None
        assert final.tool_calls[0].id == "call_1"
        assert final.tool_calls[0].function.arguments == '{"a":1}'
        assert final.usage is not None
        assert final.usage.cache_hit == 3
        assert final.metadata.original_request_id == "resp_1"
        assert final.metadata.stop_reason == "tool_use"

    @pytest.mark.asyncio
    async def test_adapter_declares_tool_result_multimodal(self):
        from amrita_core.adapters.openai_responses import OpenAIResponsesAdapter

        assert OpenAIResponsesAdapter.features.tool_result_multimodal is True
        assert OpenAIResponsesAdapter.features.input_multimodal is True
        assert OpenAIResponsesAdapter.features.agentic_call is True


class TestReasoningRoundTrip:
    """Providers reject a tool turn whose reasoning items are not replayed."""

    def _signature(self) -> str:
        from amrita_core.adapters.openai_responses import _reasoning_signature

        signature = _reasoning_signature(
            [
                {
                    "id": "rs_1",
                    "encrypted_content": "enc-1",
                    "text": "thinking about it",
                }
            ]
        )
        assert signature is not None
        return signature

    def test_reasoning_item_is_replayed_before_the_message(self):
        items = _to_input_items(
            [
                {
                    "role": "assistant",
                    "content": "done",
                    "reasoning_signature": self._signature(),
                }
            ]
        )
        assert items[0] == {
            "type": "reasoning",
            "id": "rs_1",
            "summary": [],
            "content": [{"type": "reasoning_text", "text": "thinking about it"}],
            "encrypted_content": "enc-1",
        }
        assert items[1]["role"] == "assistant"

    def test_anthropic_signature_is_ignored(self):
        items = _to_input_items(
            [
                {
                    "role": "assistant",
                    "content": "done",
                    "reasoning_signature": "not-json-signature",
                }
            ]
        )
        assert all(item["type"] != "reasoning" for item in items)

    def test_disabled_thinking_maps_to_effort_none(self):
        from amrita_core.types import ThinkingConfig

        adapter = _adapter()
        adapter.preset.thinking_config = ThinkingConfig(thinking_type="disabled")
        kwargs = adapter._request_kwargs([], None, None, False)
        assert kwargs["reasoning"] == {"effort": "none"}

    def test_parse_output_collects_reasoning_items(self):
        from amrita_core.adapters.openai_responses import _parse_output

        text, reasoning, _calls, items = _parse_output(
            [
                SimpleNamespace(
                    type="reasoning",
                    id="rs_1",
                    encrypted_content="enc-1",
                    summary=[],
                    content=[SimpleNamespace(type="reasoning_text", text="hm")],
                ),
                SimpleNamespace(
                    type="message",
                    content=[SimpleNamespace(type="output_text", text="hi")],
                ),
            ]
        )
        assert text == "hi"
        assert reasoning == "hm"
        assert items == [{"id": "rs_1", "encrypted_content": "enc-1", "text": "hm"}]
