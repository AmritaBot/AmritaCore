import json
import random
from asyncio import Lock
from collections.abc import Awaitable, Callable, Iterable
from contextlib import nullcontext
from copy import deepcopy
from typing import Any, overload

from fastmcp import Client
from fastmcp.client.client import CallToolResult
from fastmcp.client.transports import ClientTransportT
from mcp.types import TextContent
from typing_extensions import Self
from zipp import Path

from amrita_core.logging import logger

from .manager import MultiToolsManager, ToolsManager
from .models import (
    FunctionDefinitionSchema,
    FunctionParametersSchema,
    MCPToolSchema,
    ToolData,
    ToolFunctionSchema,
    cast_mcp_properties_to_openai,
)

MCP_SERVER_SCRIPT_TYPE = ClientTransportT


class NOT_GIVEN:
    pass


class MCPClient:
    """Reusable MCP Client"""

    mcp_client: Client | None = None
    server_script: MCP_SERVER_SCRIPT_TYPE

    def __init__(
        self,
        server_script: MCP_SERVER_SCRIPT_TYPE,
        # headers: dict | None = None,
    ):
        self.mcp_client = None
        self.server_script: MCP_SERVER_SCRIPT_TYPE = server_script
        self.tools: list[MCPToolSchema] = []
        self.openai_tools: list[ToolFunctionSchema] = []

    async def __aenter__(self) -> Self:
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close()

    async def simple_call(self, tool_name: str, data: dict[str, Any]) -> str:
        """Call MCP tool
        Args:
            tool_name (str): tool name
            data (dict[str, Any]): tool parameters
        """

        try:
            if self.mcp_client is None:
                await self._connect()
            assert self.mcp_client is not None
            response: CallToolResult = await self.mcp_client.call_tool(tool_name, data)
            ct: list[TextContent] = [
                i for i in response.content if isinstance(i, TextContent)
            ]
            return "".join([f"{i.text}\n\n" for i in ct])
        except Exception as e:
            logger.opt(exception=e, colors=True).error(
                f"Failed to call tool:{tool_name}, because {e}."
            )
            return json.dumps({"success": False, "error": str(e)})
        finally:
            await self._close()

    async def _connect(self, update_tools: bool = False):
        """Connect to MCP Server
        Args:
            update_tools (bool, optional): whether to update the tool list. Defaults to False.
        """
        if self.mcp_client is not None:
            raise RuntimeError("MCP Server is already connected!")

        server_script = self.server_script
        self.mcp_client = Client(server_script)
        await self.mcp_client.__aenter__()
        logger.info(f"Successfully connected to MCP Server@{server_script}")
        if not self.tools or update_tools:
            self.tools = [
                MCPToolSchema.model_validate(i.model_dump())
                for i in await self.mcp_client.list_tools()
            ]
            logger.info(f"Available tools: {[tool.name for tool in self.tools]}")
            self._cast_tool_to_openai()

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
                        required=tool.inputSchema.required,
                        properties=cast_mcp_properties_to_openai(
                            property=tool.inputSchema.properties
                        ),
                    ),
                ),
            )
            for tool in self.tools
        ]
        return openai_tools

    def _cast_tool_to_openai(self) -> None:
        self.openai_tools = self._format_tools_for_openai()

    def get_tools(self) -> list[ToolFunctionSchema]:
        """Get MCP tool list"""
        return self.openai_tools

    def get_original_tools(self) -> list[MCPToolSchema]:
        """Get original MCP tool list"""
        return self.tools

    async def _close(self):
        """Close connection"""
        if self.mcp_client:
            await self.mcp_client.__aexit__(None, None, None)
            self.mcp_client = None


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
    _lock: Lock
    _is_initialized = False  # Whether ToolsMapping is ready
    _initted = False

    def __init__(self, tools_manager: MultiToolsManager | None = None) -> None:
        if not self._initted:
            self._initted = True
            self.tools_manager = tools_manager or self.tools_manager
            self.clients = []
            self.name_to_clients = {}
            self.tools_remapping = {}
            self.reversed_remappings = {}
            self.script_to_clients = {}
            self._lock = Lock()

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
            raise RuntimeError(
                f"Tool not found: {tool_name}{f' (remapped from `{name}`)' if name != tool_name else ''}"
            )

    def _tools_wrapper(
        self, tool_name: str
    ) -> Callable[[dict[str, Any]], Awaitable[str]]:
        async def tools_runner(data: dict[str, Any]) -> str:
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
            tm = self.tools_manager
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
                        )
                    )

        except Exception as e:
            if fail_then_raise:
                raise
            logger.opt(exception=e, colors=True).error(
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

    async def reinitalize_all(self):
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
        tools_manager = self.tools_manager
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
