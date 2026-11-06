"""A tool-calling assistant turn may also carry visible text; keep it."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from amrita_core.adapters.openai import OpenAIAdapter
from amrita_core.adapters.openai_responses import OpenAIResponsesAdapter
from amrita_core.config import AmritaConfig
from amrita_core.types import ModelPreset

TEXT = "STATUS: looking that up now"


def _preset(protocol: str, base_url: str = "https://api.example.com") -> ModelPreset:
    return ModelPreset(
        model="m", name="p", api_key="k", protocol=protocol, base_url=base_url
    )


def _messages() -> list:
    return [
        {"role": "user", "content": "what time is it"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "get_time", "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "name": "get_time",
            "content": "12:00",
        },
    ]


class TestOpenAIChatToolCallContent:
    @pytest.mark.asyncio
    async def test_text_next_to_tool_calls_survives(self):
        adapter = OpenAIAdapter(_preset("openai"), AmritaConfig())
        completion = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=TEXT,
                        tool_calls=[
                            SimpleNamespace(
                                id="call_1",
                                type="function",
                                function=SimpleNamespace(
                                    name="get_time", arguments="{}"
                                ),
                            )
                        ],
                        reasoning_content=None,
                    ),
                    finish_reason="tool_calls",
                )
            ],
            model="m",
            _request_id="r",
            usage=None,
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=AsyncMock(return_value=completion))
            )
        )
        with patch(
            "amrita_core.adapters.openai.openai.AsyncOpenAI", return_value=client
        ):
            result = await adapter.call_tools(_messages(), [])

        assert result.content == TEXT
        assert result.tool_calls
        assert result.tool_calls[0].id == "call_1"


class TestAnthropicToolCallContent:
    @pytest.mark.asyncio
    async def test_text_block_next_to_tool_use_survives(self):
        from anthropic.types import TextBlock, ToolUseBlock

        adapter = __import__(
            "amrita_core.adapters.anthropic", fromlist=["AnthropicAdapter"]
        ).AnthropicAdapter(_preset("anthropic"), AmritaConfig())
        response = SimpleNamespace(
            content=[
                TextBlock(type="text", text=TEXT),
                ToolUseBlock(type="tool_use", id="tool_1", name="get_time", input={}),
            ],
            stop_sequence=None,
            stop_reason="tool_use",
            model="m",
            _request_id="r",
            usage=None,
        )
        client = SimpleNamespace(
            messages=SimpleNamespace(create=AsyncMock(return_value=response))
        )
        with patch(
            "amrita_core.adapters.anthropic.anthropic.AsyncAnthropic",
            return_value=client,
        ):
            result = await adapter.call_tools(_messages(), [])

        assert result.content == TEXT
        assert result.tool_calls
        assert result.tool_calls[0].id == "tool_1"


class TestResponsesToolCallContent:
    @pytest.mark.asyncio
    async def test_output_text_next_to_function_call_survives(self):
        adapter = OpenAIResponsesAdapter(_preset("openai-responses"), AmritaConfig())
        response = SimpleNamespace(
            output=[
                SimpleNamespace(
                    type="message",
                    content=[SimpleNamespace(type="output_text", text=TEXT)],
                ),
                SimpleNamespace(
                    type="function_call",
                    call_id="call_1",
                    name="get_time",
                    arguments="{}",
                ),
            ],
            usage=None,
            model="m",
            id="r",
            status="completed",
        )
        client = SimpleNamespace(
            responses=SimpleNamespace(create=AsyncMock(return_value=response))
        )
        with patch(
            "amrita_core.adapters.openai_responses.openai.AsyncOpenAI",
            return_value=client,
        ):
            result = await adapter.call_tools(_messages(), [])

        assert result.content == TEXT
        assert result.tool_calls
        assert result.tool_calls[0].id == "call_1"
