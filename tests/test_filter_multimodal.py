"""`filter_multimodal`: the public capability filter for caller-built payloads."""

from __future__ import annotations

from amrita_core.base.adapter import FeatureFlag, ModelAdapter
from amrita_core.libchat import filter_multimodal
from amrita_core.types import (
    ImageContent,
    ImageUrl,
    Message,
    TextContent,
    ToolResult,
)


def _image(url: str = "https://example.com/a.png") -> ImageContent:
    return ImageContent(image_url=ImageUrl(url=url))


class _Full(ModelAdapter):
    __no_register__ = True
    __abstract__ = True
    features = FeatureFlag(input_multimodal=True, tool_result_multimodal=True)


class _TextOnly(ModelAdapter):
    __no_register__ = True
    __abstract__ = True
    features = FeatureFlag(input_multimodal=True, tool_result_multimodal=False)


class _Closed(ModelAdapter):
    __no_register__ = True
    __abstract__ = True
    features = FeatureFlag()


def _context() -> list:
    return [
        Message(role="user", content=[TextContent(text="look"), _image()]),
        Message(role="assistant", content=None),
        ToolResult(
            role="tool",
            name="shot",
            tool_call_id="1",
            content=[TextContent(text="see"), _image()],
        ),
    ]


class TestFilterMultimodal:
    def test_supporting_adapter_gets_the_original_list(self):
        context = _context()
        assert filter_multimodal(context, _Full) is context

    def test_tool_result_is_filtered_by_its_own_flag(self):
        context = _context()
        filtered = filter_multimodal(context, _TextOnly)
        # User-message multimodal is still supported, so the object is reused.
        assert filtered[0] is context[0]
        result = filtered[2]
        assert result is not context[2]
        assert [block.type for block in result.content] == ["text", "text"]
        assert result.content[1].text == "[Image Unsupported]"

    def test_closed_adapter_filters_every_message(self):
        context = _context()
        filtered = filter_multimodal(context, _Closed)
        assert filtered[0] is not context[0]
        assert filtered[0].content[1].text == "[Image Unsupported]"
        assert filtered[2] is not context[2]

    def test_history_is_never_mutated(self):
        context = _context()
        filter_multimodal(context, _Closed)
        assert isinstance(context[0].content[1], ImageContent)
        assert isinstance(context[2].content[1], ImageContent)

    def test_text_only_message_passes_through(self):
        message = Message(role="user", content="plain")
        assert filter_multimodal([message], _Closed)[0] is message
