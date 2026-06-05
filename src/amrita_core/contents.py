from __future__ import annotations

import base64
from abc import ABC
from io import BytesIO
from pathlib import Path
from typing import Any, TypedDict

import aiofiles
import aiohttp
import filetype
from filetype.types.base import Type

from amrita_core.base.adapter import MessageContent


def get_image_format(file: Path | bytes):
    kind: Type | None = filetype.guess(file)
    if kind is None:
        return
    assert isinstance(kind.mime, str)
    if kind and kind.mime.startswith("image/"):
        assert isinstance(kind.extension, str)
        return kind.extension.lower()  # return 'png', 'jpeg' or 'gif' etc.


class RawMessageContent(MessageContent, ABC):
    """Raw message content implementation abstract class"""

    def __init__(self, raw_data: Any):
        super().__init__("raw")
        self.raw_data = raw_data

    def get_content(self):
        return self.raw_data

    def __str__(self) -> str:
        return str(self.raw_data)


class StringMessageContent(MessageContent):
    """String type message content implementation"""

    def __init__(self, text: str):
        super().__init__("string")
        self.text = text

    def get_content(self) -> str:
        return self.text


# TODO: When Python 3.10 EOL, refactor to use TypedDict + Generic
#       e.g. class MessageMetadataPayload(TypedDict, Generic[T, T_E]):
class MessageMetadataPayload(TypedDict):
    type: str
    extra_type: str | None

class MessageMetadataPayloadError(MessageMetadataPayload):
    error: str
    type: str  # TODO: Literal["error"] after Python 3.10 EOL


class MessageMetadataPayloadSystem(MessageMetadataPayload):
    type: str  # TODO: Literal["system"] after Python 3.10 EOL
    message: str


class MessageMetadata(TypedDict):
    content: str
    metadata: MessageMetadataPayload


class MessageWithMetadata(MessageContent):
    """Message with additional metadata"""

    def __init__(self, content: str, metadata: MessageMetadataPayload):
        """Constructor of MessageWith Metadata

        Args:
            content (str): Message content
            metadata (dict[str, Any]): Metadata, normally has "type", "extra_type"(optional), "content" fields, but can be customized
        """
        super().__init__("metadata")
        self.content = content
        self.metadata = metadata

    def get_content(self) -> str:
        return self.content

    def get_metadata(self) -> MessageMetadataPayload:
        return self.metadata

    def get_full_content(self) -> MessageMetadata:
        return MessageMetadata(content=self.content, metadata=self.metadata)


class ImageMessage(MessageContent):
    """Image message"""

    def __init__(self, image: str | BytesIO | bytes):
        """Construct a new ImageMessage object.

        Args:
            image (str | BytesIO | bytes): The image to be responded with, str: URL, BytesIO: file object, bytes: Base64 encoded image
        """
        super().__init__("image")
        self.image: str | BytesIO | bytes = image

    async def get_image(self, headers: dict[str, Any] | None = None) -> BytesIO | bytes:
        if isinstance(self.image, str):
            self.image = await self.curl_image(headers)
        return self.image

    async def curl_image(self, extra_headers: dict | None = None) -> bytes:
        if isinstance(self.image, str):
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36"
            }
            headers.update(extra_headers or {})
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(self.image) as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to download image from {self.image}")
                    bt = await response.read()
                    obj = base64.b64encode(bt)
                    return obj
        raise ValueError("Image must be a URL to use this method")

    def get_content(self) -> str:
        if isinstance(self.image, str):
            return f"![]({self.image})"
        elif isinstance(self.image, BytesIO):
            self.image = self.image.getvalue()
        image_type = get_image_format(self.image)
        if not image_type:
            return "[Unsupported image format]"
        base64_data = base64.b64encode(self.image).decode("utf-8")
        return f"![](data:image/{image_type};base64,{base64_data})"

    async def save_to(self, path: Path, headers: dict | None = None):
        async with aiofiles.open(path, "wb") as f:
            if isinstance(self.image, BytesIO):
                await f.write(self.image.read())
            elif isinstance(self.image, bytes):
                await f.write(self.image)
            else:
                await f.write(await self.curl_image(headers))


__all__ = [
    "ImageMessage",
    "MessageMetadata",
    "MessageWithMetadata",
    "RawMessageContent",
    "StringMessageContent",
    "get_image_format",
]
