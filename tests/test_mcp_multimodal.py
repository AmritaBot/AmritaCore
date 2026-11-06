"""MCP content blocks: media from a server becomes a framework content block."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp_types import (
    AudioContent,
    BlobResourceContents,
    EmbeddedResource,
    ImageContent,
    ResourceLink,
    TextContent,
    TextResourceContents,
)

from amrita_core.tools.mcp import (
    MCPClient,
    _content_blocks_to_result,
    _convert_block,
)


class TestConvertBlock:
    def test_image_becomes_inline_data_uri(self):
        block = _convert_block(ImageContent(data="AAA", mime_type="image/png"))
        assert block is not None
        assert block.type == "image_url"
        assert block.image_url.url == "data:image/png;base64,AAA"

    def test_audio_becomes_a_file_block_with_an_extension(self):
        block = _convert_block(AudioContent(data="BBB", mime_type="audio/mpeg"))
        assert block is not None
        assert block.type == "file"
        assert block.file.filename == "audio.mp3"
        assert block.file.file_data == "BBB"
        assert block.file.type == "audio/mpeg"

    def test_unknown_audio_type_falls_back_to_the_subtype(self):
        block = _convert_block(AudioContent(data="C", mime_type="audio/flac"))
        assert block.file.filename == "audio.flac"

    def test_text_resource_becomes_text(self):
        block = _convert_block(
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(uri="file:///a.txt", text="hello"),
            )
        )
        assert block.type == "text"
        assert block.text == "hello"

    def test_blob_resource_becomes_a_file_block(self):
        block = _convert_block(
            EmbeddedResource(
                type="resource",
                resource=BlobResourceContents(
                    uri="file:///a.bin", blob="ZZZ", mime_type="application/pdf"
                ),
            )
        )
        assert block.type == "file"
        assert block.file.filename == "resource.pdf"
        assert block.file.file_data == "ZZZ"

    def test_resource_link_is_described_in_text(self):
        block = _convert_block(
            ResourceLink(
                type="resource_link",
                name="report",
                uri="https://example.com/r",
            )
        )
        assert block.type == "text"
        assert "report" in block.text
        assert "https://example.com/r" in block.text

    def test_unknown_block_is_dropped(self):
        assert _convert_block(object()) is None


class TestBlocksToResult:
    def test_text_only_stays_a_string(self):
        result = _content_blocks_to_result(
            [TextContent(text="a"), TextContent(text="b")]
        )
        assert result == "a\n\nb\n\n"

    def test_media_keeps_the_block_list(self):
        result = _content_blocks_to_result(
            [TextContent(text="see"), ImageContent(data="AAA", mime_type="image/png")]
        )
        assert isinstance(result, list)
        assert [block.type for block in result] == ["text", "image_url"]

    def test_unknown_blocks_do_not_lose_the_text(self):
        result = _content_blocks_to_result([object(), TextContent(text="kept")])
        assert result == "kept\n\n"


class TestSimpleCallReturnsBlocks:
    @pytest.mark.asyncio
    async def test_media_survives_simple_call(self):
        client = MCPClient(server_script="test_script")
        mock_client = AsyncMock()
        mock_client.__aexit__.return_value = None
        mock_result = MagicMock()
        mock_result.content = [
            TextContent(text="screenshot"),
            ImageContent(data="AAA", mime_type="image/png"),
        ]
        mock_client.call_tool.return_value = mock_result

        with (
            patch.object(client, "_connect"),
            patch.object(client, "close"),
        ):
            client.mcp_client = mock_client
            result = await client.simple_call("shot", {})

        assert isinstance(result, list)
        assert result[1].image_url.url == "data:image/png;base64,AAA"
