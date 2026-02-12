from __future__ import annotations

import base64
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Iterable
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, TypedDict

import aiofiles
import aiohttp
import filetype
from filetype.types.base import Type

from amrita_core.config import AmritaConfig, get_config

from .logging import logger
from .tools.models import ToolChoice, ToolFunctionSchema
from .types import ModelPreset, ToolCall, UniResponse


def get_image_format(file: Path | bytes):
    kind: Type | None = filetype.guess(file)
    if kind is None:
        return
    assert isinstance(kind.mime, str)
    if kind and kind.mime.startswith("image/"):
        assert isinstance(kind.extension, str)
        return kind.extension.lower()  # return 'png', 'jpeg' or 'gif' etc.


class MessageContent(ABC):
    """Abstract base class for different types of message content

    This allows for various types of content to be yielded by the chat manager,
    not just strings. Subclasses should implement their own representation.
    """

    def __str__(self) -> str:
        return self.get_content()

    def __init__(self, content_type: str):
        self.type = content_type

    @abstractmethod
    def get_content(self):
        """Return the actual content of the message"""
        raise NotImplementedError("Subclasses must implement get_content method")


class RawMessageContent(MessageContent, ABC):
    """Raw message content implementation abstract class"""

    def __init__(self, raw_data: Any):
        super().__init__("raw")
        self.raw_data = raw_data

    def get_content(self):
        return self.raw_data


class StringMessageContent(MessageContent):
    """String type message content implementation"""

    def __init__(self, text: str):
        super().__init__("string")
        self.text = text

    def get_content(self) -> str:
        return self.text


class MessageMetadata(TypedDict):
    content: str
    metadata: dict[str, Any]


class MessageWithMetadata(MessageContent):
    """Message with additional metadata"""

    def __init__(self, content: str, metadata: dict[str, Any]):
        super().__init__("metadata")
        self.content = content
        self.metadata = metadata

    def get_content(self) -> Any:
        return self.content

    def get_metadata(self) -> dict:
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
        return f"![](data:image/{image_type};base64,{self.image.decode('utf-8')})"

    async def save_to(self, path: Path, headers: dict | None = None):
        async with aiofiles.open(path, "wb") as f:
            if isinstance(self.image, BytesIO):
                await f.write(self.image.read())
            elif isinstance(self.image, bytes):
                await f.write(self.image)
            else:
                await f.write(await self.curl_image(headers))


COMPLETION_RETURNING = MessageContent | str | UniResponse[str, None]


@dataclass
class ModelAdapter:
    """Base class for model adapter"""

    preset: ModelPreset
    config: AmritaConfig = field(default_factory=get_config)
    __override__: bool = False  # Whether to allow overriding existing adapters

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        if not getattr(cls, "__abstract__", False):
            AdapterManager().register_adapter(cls)

    @abstractmethod
    async def call_api(
        self, messages: Iterable
    ) -> AsyncGenerator[COMPLETION_RETURNING, None]:
        yield ""

    async def call_tools(
        self,
        messages: Iterable,
        tools: list[ToolFunctionSchema],
        tool_choice: ToolChoice | None = None,
    ) -> UniResponse[None, list[ToolCall] | None]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_adapter_protocol() -> str | tuple[str, ...]: ...

    @property
    def protocol(self):
        """Get model protocol adapter"""
        return self.get_adapter_protocol()


class AdapterManager:
    __instance = None
    _adapter_class: dict[str, type[ModelAdapter]]

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance._adapter_class = {}
        return cls.__instance

    def get_adapters(self) -> dict[str, type[ModelAdapter]]:
        """Get all registered adapters"""
        return self._adapter_class

    def safe_get_adapter(self, protocol: str) -> type[ModelAdapter] | None:
        """Get adapter"""
        return self._adapter_class.get(protocol)

    def get_adapter(self, protocol: str) -> type[ModelAdapter]:
        """Get adapter"""
        if protocol not in self._adapter_class:
            raise ValueError(f"No adapter found for protocol {protocol}")
        return self._adapter_class[protocol]

    def register_adapter(self, adapter: type[ModelAdapter]):
        """Register adapter"""
        protocol = adapter.get_adapter_protocol()
        override = adapter.__override__ if hasattr(adapter, "__override__") else False
        if isinstance(protocol, str):
            if protocol in self._adapter_class:
                if not override:
                    raise ValueError(
                        f"Model protocol adapter {protocol} is already registered"
                    )
                logger.warning(
                    f"Model protocol adapter {protocol} has been registered by {self._adapter_class[protocol].__name__}, overriding existing adapter"
                )

            self._adapter_class[protocol] = adapter
        elif isinstance(protocol, tuple):
            for p in protocol:
                if not isinstance(p, str):
                    raise TypeError(
                        "Model protocol adapter must be a string or tuple of strings"
                    )
                if p in self._adapter_class:
                    if not override:
                        raise ValueError(
                            f"Model protocol adapter {p} is already registered"
                        )
                    logger.warning(
                        f"Model protocol adapter {p} has been registered by {self._adapter_class[p].__name__}, overriding existing adapter"
                    )
                self._adapter_class[p] = adapter
