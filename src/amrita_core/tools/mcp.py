from __future__ import annotations

import asyncio
import contextlib
import json
import random
from collections.abc import Awaitable, Callable, Iterable
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from typing import Any, cast, overload

import aiologic
from amrita_sense.logging import logger
from fastmcp import Client
from fastmcp.client.client import CallToolResult
from mcp_types import (
    AudioContent as MCPAudioContent,
)
from mcp_types import (
    BlobResourceContents,
    EmbeddedResource,
    ResourceLink,
    TextResourceContents,
)
from mcp_types import (
    ImageContent as MCPImageContent,
)
from mcp_types import (
    TextContent as MCPTextContent,
)
from typing_extensions import Self

from amrita_core.types import (
    Content,
    File,
    FileContent,
    ImageContent,
    ImageUrl,
    TextContent,
)
from amrita_core.types.tool import TOOL_RESULT_CONTENT
from amrita_core.utils import _did_you_mean_hint

from ._parser import resolve_transport
from .manager import MultiToolsManager, ToolsManager
from .models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    MCPToolSchema,
    ToolData,
    ToolFunctionSchema,
    cast_mcp_properties_to_amrita,
)

MCP_SERVER_SCRIPT_TYPE = (
    str | Path  # Supports: file paths, http(s)://, sse://, stream+http(s)://, stdio://
)


#: MCP reports only a MIME type; a file block also needs a filename.
_EXT_BY_MIME: dict[str, str] = {
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/ogg": "ogg",
    "audio/mp4": "m4a",
    "audio/webm": "webm",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    "application/pdf": "pdf",
}


def _extension_for(mime_type: str) -> str:
    """Pick a file extension for a MIME type, falling back to its subtype."""
    lowered = (mime_type or "").lower()
    if lowered in _EXT_BY_MIME:
        return _EXT_BY_MIME[lowered]
    subtype = lowered.partition("/")[2]
    return subtype or "bin"


def _data_uri(data: str, mime_type: str) -> str:
    """Wrap MCP's raw base64 payload as the inline URL the framework stores."""
    return f"data:{mime_type or 'application/octet-stream'};base64,{data}"


def _convert_block(block: object) -> Content | None:
    """Convert one MCP content block into a framework ``Content`` block.

    MCP returns media as bare base64 plus a MIME type; the framework's
    ``image_url`` block wants an inline data URI, and a non-image binary has to
    become a ``file`` block (which requires a filename). Unknown block types
    return ``None`` instead of raising: a server that adds a new content kind
    should not break every call, and the text parts still reach the model.
    """
    if isinstance(block, MCPTextContent):
        return TextContent(text=block.text)
    if isinstance(block, MCPImageContent):
        return ImageContent(
            image_url=ImageUrl(url=_data_uri(block.data, block.mime_type))
        )
    if isinstance(block, MCPAudioContent):
        return FileContent(
            file=File(
                filename=f"audio.{_extension_for(block.mime_type)}",
                file_data=block.data,
                type=block.mime_type,
            )
        )
    if isinstance(block, EmbeddedResource):
        resource = block.resource
        if isinstance(resource, TextResourceContents):
            return TextContent(text=resource.text)
        if isinstance(resource, BlobResourceContents):
            mime_type = getattr(resource, "mime_type", None) or (
                "application/octet-stream"
            )
            return FileContent(
                file=File(
                    filename=f"resource.{_extension_for(mime_type)}",
                    file_data=resource.blob,
                    type=mime_type,
                )
            )
        return None
    if isinstance(block, ResourceLink):
        name = getattr(block, "name", "") or ""
        uri = getattr(block, "uri", "") or ""
        return TextContent(text=f"<resource:{name}> {uri}".strip())
    return None


def _content_blocks_to_result(blocks: Iterable[object]) -> TOOL_RESULT_CONTENT:
    """Collapse a tool result into text when it is text-only, else keep blocks.

    The string return keeps every existing caller working (and is what the
    plain-text view reads anyway); the block list is only used when the server
    actually sent media, which is what makes ``tool_result_multimodal`` matter.
    """
    converted = [
        item for item in (_convert_block(block) for block in blocks) if item is not None
    ]
    if all(isinstance(item, TextContent) for item in converted):
        return "".join(f"{cast(TextContent, item).text}\n\n" for item in converted)
    return cast(TOOL_RESULT_CONTENT, converted)


class MCPClient:
    """Reusable MCP Client"""

    mcp_client: Client | None = None
    server_script: MCP_SERVER_SCRIPT_TYPE
    _close_waiter: asyncio.Future | None = None
    _close_ttl: int
    _connect_lock: aiologic.Lock
    _active_calls: int = 0  # In-flight simple_call counter

    def __init__(
        self,
        server_script: MCP_SERVER_SCRIPT_TYPE,
        connection_ttl: int = 60,  # When the connection is not used for a long time, it will be closed
        # headers: dict | None = None,
    ):
        """Constructor

        Args:
            server_script (MCP_SERVER_SCRIPT_TYPE): Server script
            connection_ttl (int, optional): TTL for connection when planned to close. Defaults to 60. Set to -1 to disable
        """
        self.mcp_client = None
        self.server_script: MCP_SERVER_SCRIPT_TYPE = server_script
        self.tools: list[MCPToolSchema] = []
        self.openai_tools: list[ToolFunctionSchema] = []
        if connection_ttl < -1:
            raise ValueError("connection_ttl must be greater than or equals to -1")
        self._close_ttl = connection_ttl
        self._connect_lock = aiologic.Lock()
        self._active_calls = 0

    async def __aenter__(self) -> Self:
        self._close_waiter = None
        if not self.mcp_client:
            await self._connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._close_ttl == -1:
            return await self.close_no_wait()
        self.close()

    async def bound_to(self, tm: ClientManager):
        try:
            tm.register_only(client=self)
            await tm._load_this(self)
        except Exception:
            with contextlib.suppress(Exception):
                await tm.unregister_client(self.server_script)
            raise

    async def simple_call(
        self, tool_name: str, data: dict[str, Any]
    ) -> TOOL_RESULT_CONTENT:
        """Call MCP tool

        The underlying fastmcp ``Client`` is a reentrant context manager with
        reference counting, so ``async with`` lets concurrent calls (e.g. the
        agent's parallel tool runner) share one connection safely. The
        connection is not torn down on every call: a TTL task reclaims it only
        after the last active call exits, forming a lightweight resident
        connection pool.

        Args:
            tool_name (str): tool name
            data (dict[str, Any]): tool parameters
        """
        self._active_calls += 1
        try:
            # Always cancel pending close-waiter first to prevent the TTL task from closing the connection while call_tool is in progress.
            await self._clean_waiter()
            if self.mcp_client is None:
                await self._connect()
            assert self.mcp_client is not None
            async with self.mcp_client:
                response: CallToolResult = await self.mcp_client.call_tool(
                    tool_name, data
                )
                return _content_blocks_to_result(response.content)
        except Exception as e:
            logger.opt(exception=e).error(
                f"Failed to call tool:{tool_name}, because {e}."
            )
            return json.dumps({"success": False, "error": str(e)})
        finally:
            self._active_calls -= 1
            if self._active_calls <= 0:
                self._active_calls = 0
                if self._close_ttl != -1:
                    # Defer the close: the TTL task reclaims the connection only after the last concurrent call has exited.
                    self.close()

    async def _connect(self, update_tools: bool = False):
        """Connect to MCP Server (idempotent, safe for concurrent calls)
        Args:
            update_tools (bool, optional): whether to update the tool list. Defaults to False.
                When True, tools are always refreshed from the server, even if already connected.
        """
        # Cancel any pending close-waiter outside the lock to avoid deadlock: _clean_waiter cancels the waiter task whose _close() also needs _connect_lock.
        await self._clean_waiter()
        async with self._connect_lock:
            if self.mcp_client is not None:
                if update_tools:
                    await self._refresh_tools()
                return

            server_script: MCP_SERVER_SCRIPT_TYPE = self.server_script
            transport = resolve_transport(str(server_script))
            self.mcp_client = Client(transport)
            await self.mcp_client.__aenter__()
            logger.info(
                f"Successfully connected to MCP Server@{str(server_script)[:10]}..."
            )
            if update_tools or not self.tools:
                await self._refresh_tools()

    async def _refresh_tools(self) -> None:
        """Refresh the cached tool list from the connected MCP server."""
        assert self.mcp_client is not None, "Cannot refresh tools: not connected"
        self.tools = [
            MCPToolSchema.model_validate(i.model_dump(by_alias=True))
            for i in await self.mcp_client.list_tools()
        ]
        logger.info(f"Available tools: {[tool.name for tool in self.tools]}")
        self._cast_tool_to_amrita()

    async def _clean_waiter(self):
        if self._close_waiter is not None:
            with contextlib.suppress(asyncio.CancelledError):
                self._close_waiter.cancel()
                await asyncio.sleep(0)
            self._close_waiter = None

    def close(self) -> asyncio.Future[None]:
        """Create a TTL-Task to wait for connection's close.

        Returns:
            asyncio.Task[None]: Waiting task.
        """
        if self._close_waiter is not None and not self._close_waiter.done():
            return self._close_waiter
        if self._close_ttl == -1:
            raise RuntimeError("TTL is not set. Please use `close_no_wait` instead.")

        async def waiter() -> None:

            with contextlib.suppress(asyncio.CancelledError):
                await asyncio.sleep(self._close_ttl)
                await self._close()

        self._close_waiter = asyncio.create_task(waiter())
        return self._close_waiter

    async def close_no_wait(self):
        await self._clean_waiter()
        await self._close()

    async def _close(self) -> None:
        """Close connection (no-op while calls are still in flight)."""
        async with self._connect_lock:
            if self.mcp_client and self._active_calls <= 0:
                # Swap out the client reference BEFORE calling __aexit__ to fix a race condition:
                client = self.mcp_client
                self.mcp_client = None
                try:
                    await client.__aexit__(None, None, None)
                finally:
                    # Always run waiter-task cleanup, even if __aexit__ fails.
                    await self._clean_waiter()

    def _format_tools_for_openai(self):
        """Convert MCP tool format to OpenAI tool format"""
        openai_tools: list[ToolFunctionSchema] = [
            ToolFunctionSchema(
                strict=True,
                type="function",
                function=FunctionDefinitionSchema(
                    name=tool.name,
                    description=tool.description or f"Running tool named: {tool.name}",
                    parameters=FunctionParametersSchema(
                        type="object",
                        required=tool.inputSchema.required or [],
                        properties=cast_mcp_properties_to_amrita(
                            property=tool.inputSchema.properties or {}
                        ),
                    ),
                ),
            )
            for tool in self.tools
        ]
        return openai_tools

    def _cast_tool_to_amrita(self) -> None:
        self.openai_tools = self._format_tools_for_openai()

    def get_tools(self) -> list[ToolFunctionSchema]:
        """Get MCP tool list"""
        return self.openai_tools

    def get_original_tools(self) -> list[MCPToolSchema]:
        """Get original MCP tool list"""
        return self.tools


class MultiClientManager:
    clients: list[MCPClient]
    script_to_clients: dict[str, MCPClient]
    name_to_clients: dict[str, MCPClient]  # Map from FunctionName to MCPClient
    tools_remapping: dict[
        str, str
    ]  # Remap duplicate tools for SuggarChat (original_name->remapped_name)
    reversed_remappings: dict[
        str, str
    ]  # Reverse mapping (remapped_name->original_name)
    tools_manager: MultiToolsManager = ToolsManager()
    _lock: aiologic.Lock
    _is_initialized = False  # Whether ToolsMapping is ready

    def __init__(self, tools_manager: MultiToolsManager | None = None) -> None:
        super().__init__()
        self.tools_manager = tools_manager or self.tools_manager
        self.clients = []
        self.name_to_clients = {}
        self.tools_remapping = {}
        self.reversed_remappings = {}
        self.script_to_clients = {}
        self._lock = aiologic.Lock()

    def get_client_by_script(self, server_script: MCP_SERVER_SCRIPT_TYPE) -> MCPClient:
        """Get MCP Client (without operating stored MCP Server)
        Args:
            server_script (str, optional): MCP Server script path (or URI).
        """
        return MCPClient(server_script)

    async def get_client_by_tool_name(self, tool_name: str) -> MCPClient:
        """Get MCP Client by tool name
        Args:
            tool_name (str): tool name
        """
        async with self._lock:
            name = self.tools_remapping.get(tool_name) or tool_name
            if name in self.name_to_clients:
                return self.name_to_clients[name]
            hint = _did_you_mean_hint(tool_name, list(self.name_to_clients.keys()))
            raise RuntimeError(
                f"Tool not found: '{tool_name}'"
                f"{f' (remapped from `{name}`)' if name != tool_name else ''}."
                f"{hint}"
            )

    def _tools_wrapper(
        self, tool_name: str
    ) -> Callable[[dict[str, Any]], Awaitable[TOOL_RESULT_CONTENT]]:
        async def tools_runner(data: dict[str, Any]) -> TOOL_RESULT_CONTENT:
            client: MCPClient = await self.get_client_by_tool_name(tool_name)
            return await client.simple_call(tool_name, data)

        return tools_runner

    @overload
    def register_only(self, *, client: MCPClient) -> Self:
        """Register MCP Server only, without initialization"""
        ...

    @overload
    def register_only(self, *, server_script: MCP_SERVER_SCRIPT_TYPE) -> Self:
        """Register MCP Server only, without initialization"""
        ...

    def register_only(
        self,
        *,
        server_script: MCP_SERVER_SCRIPT_TYPE | None = None,
        client: MCPClient | None = None,
    ) -> Self:
        """Register MCP Server only, without initialization"""
        if client is not None:
            self.clients.append(client)
        elif server_script is not None:
            client = MCPClient(server_script)
            self.clients.append(client)
        else:
            raise ValueError("Please provide MCP Server script or MCP Client")
        return self

    async def update_tools(self, client: MCPClient):
        tools = client.get_tools()
        async with self._lock:
            for tool in tools:
                name = tool.function.name
                self.tools_manager.remove_tool(name)
                self.name_to_clients.pop(name, None)
                if remap := self.tools_remapping.pop(name, None):
                    self.reversed_remappings.pop(remap, None)
        await self._load_this(client)

    async def initialize_scripts_all(
        self, scripts: Iterable[MCP_SERVER_SCRIPT_TYPE]
    ) -> Self:
        for script in scripts:
            await self.initialize_this(script)
        return self

    async def initialize_this(
        self, server_script: MCP_SERVER_SCRIPT_TYPE, fail_then_raise: bool = False
    ) -> Self:
        """Register and initialize single MCP Server"""
        client: MCPClient = self.get_client_by_script(server_script)
        async with self._lock:
            try:
                await self._load_this(client)
            except Exception as e:
                logger.error(f"Failed to initialize MCP Server@{server_script}: {e}")
                if fail_then_raise:
                    raise
            else:
                self.clients.append(client)
        return self

    async def _load_this(self, client: MCPClient, fail_then_raise=True):
        try:
            tools_remapping_tmp = {}
            reversed_remappings_tmp = {}
            name_to_clients_tmp = {}
            tm: MultiToolsManager = self.tools_manager
            async with client as c:
                tools = deepcopy(c.get_tools())
                for tool in tools:
                    if (
                        tool.function.name in self.tools_remapping
                        or tool.function.name in self.name_to_clients
                    ):
                        logger.warning(
                            f"{client}@{client.server_script} has a tool named {tool.function.name}, which is already registered, the old tool will be replaced."
                        )
                    name_to_clients_tmp[tool.function.name] = client
                    origin_name = tool.function.name
                    if tm.has_tool(tool.function.name):
                        remapped_name = (
                            f"referred_{random.randint(1, 100)}_{tool.function.name}"
                        )
                        logger.warning(
                            f"Tool already exists: {tool.function.name}, it will be remapped to: {remapped_name}"
                        )
                        tools_remapping_tmp[origin_name] = remapped_name
                        reversed_remappings_tmp[remapped_name] = origin_name
                        tool.function.name = remapped_name

                    tm.register_tool(
                        ToolData(
                            data=tool,
                            func=self._tools_wrapper(origin_name),
                            # MCP tools carry no trustworthy read/write hint, so every remote call runs on its own.
                            concurrency_safe=False,
                        )
                    )

        except Exception as e:
            if fail_then_raise:
                raise
            logger.opt(exception=e).error(
                f"Failed to connect to MCP Server@{client.server_script}: {e}"
            )
        else:
            logger.info(f"Successfully loaded MCP Server@{client.server_script}")
            self.tools_remapping.update(tools_remapping_tmp)
            self.reversed_remappings.update(reversed_remappings_tmp)
            self.name_to_clients.update(name_to_clients_tmp)
            if isinstance(client.server_script, str | Path):
                server_script = str(client.server_script)
                self.script_to_clients[server_script] = client

    async def reinitialize_all(self):
        """Reinitialize all MCP Servers"""
        async with self._lock:
            for client in deepcopy(self.clients):
                await self.unregister_client(client.server_script, False)
                self.register_only(client=client)
                await self._load_this(client, fail_then_raise=False)

    async def initialize_all(self, lock: bool = True):
        """Connect to all MCP Servers"""
        async with self._lock if lock else nullcontext():
            for client in self.clients:
                await self._load_this(client, False)
            self._is_initialized = True

    async def unregister_client(self, script_name: str | Path, lock: bool = True):
        """Unregister an MCP Server"""
        tools_manager: MultiToolsManager = self.tools_manager
        async with self._lock if lock else nullcontext():
            script_name = str(script_name)
            if script_name in self.script_to_clients:
                client = self.script_to_clients.pop(script_name)
                for tool in client.openai_tools:
                    name = tool.function.name
                    tools_manager.remove_tool(name)
                    self.name_to_clients.pop(name, None)
                    if remap := self.tools_remapping.pop(name, None):
                        tools_manager.remove_tool(remap)
                        self.reversed_remappings.pop(remap, None)
                for idx, client in enumerate(self.clients):
                    if client.server_script == script_name:
                        self.clients.pop(idx)
                        break


class ClientManager(MultiClientManager):
    _instance = None
    _initialized = False

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self.__class__._initialized:
            super().__init__()
            self.__class__._initialized = True
