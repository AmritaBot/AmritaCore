import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amrita_core.tools.mcp import (
    ClientManager,
    MCPClient,
    MultiClientManager,
)


class TestMCPClient:
    @pytest.fixture
    def mcp_client(self):
        return MCPClient(server_script="test_script")

    def test_initialization(self, mcp_client: MCPClient):
        assert mcp_client.mcp_client is None
        assert mcp_client.server_script == "test_script"
        assert mcp_client.tools == []
        assert mcp_client.openai_tools == []

    @pytest.mark.asyncio
    async def test_aenter_and_aexit(self, mcp_client: MCPClient):
        with patch.object(mcp_client, "_connect") as mock_connect:
            result = await mcp_client.__aenter__()
            assert result == mcp_client
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    @patch("amrita_core.tools.mcp.Client")
    async def test_connect(self, mock_client_class):
        # Create a mock client instance
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance

        client = MCPClient(server_script="test_script")

        # Mock the list_tools return value
        mock_client_instance.list_tools.return_value = []

        # Connect manually
        await client._connect(update_tools=True)

        # Verify that the connection was successful
        assert client.mcp_client is not None

    @pytest.mark.asyncio
    async def test_simple_call(self, mcp_client):
        # Test simple call
        with (
            patch.object(mcp_client, "_connect"),
            patch.object(mcp_client, "close") as mock_close,
        ):
            # Mock mcp_client instance
            mock_client = AsyncMock()
            # Do NOT suppress exceptions propagating out of `async with`.
            mock_client.__aexit__.return_value = None
            mock_result = MagicMock()
            mock_result.content = []
            mock_client.call_tool.return_value = mock_result

            mcp_client.mcp_client = mock_client

            await mcp_client.simple_call("test_tool", {"param": "value"})

            # Verify that the tool was called correctly
            mock_client.call_tool.assert_called_once_with(
                "test_tool", {"param": "value"}
            )
            # The connection is deferred to a TTL task, not torn down now.
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_simple_call_with_exception(self, mcp_client):
        """Test simple_call when exception occurs"""
        with (
            patch.object(mcp_client, "_connect"),
            patch.object(mcp_client, "close"),
        ):
            mock_client = AsyncMock()
            # Do NOT suppress exceptions propagating out of `async with`.
            mock_client.__aexit__.return_value = None
            mock_client.call_tool.side_effect = Exception("Test error")
            mcp_client.mcp_client = mock_client

            result = await mcp_client.simple_call("test_tool", {"param": "value"})

            # Should return JSON error response
            error_data = json.loads(result)
            assert error_data["success"] is False
            assert "Test error" in error_data["error"]

    @pytest.mark.asyncio
    async def test_simple_call_concurrent(self, mcp_client):
        """Concurrent simple_calls share one connection without premature close.

        Regression test: previously the `finally` block called `_close()` on
        every call, so the first caller to finish tore down the connection
        while siblings were still mid-call.
        """
        with (
            patch.object(mcp_client, "_connect"),
            patch.object(mcp_client, "close") as mock_close,
        ):
            mock_client = AsyncMock()
            # Do NOT suppress exceptions propagating out of `async with`.
            mock_client.__aexit__.return_value = None
            mock_result = MagicMock()
            mock_result.content = []
            mcp_client.mcp_client = mock_client

            # Barrier: force BOTH calls to be in flight on the shared
            # connection before either one returns, otherwise the refcount can
            # never exceed one and the race is not actually exercised.
            started_count = 0
            both_started = asyncio.Event()
            release = asyncio.Event()

            async def delayed_call(tool_name, data):
                nonlocal started_count
                started_count += 1
                if started_count == 2:
                    both_started.set()
                await release.wait()
                return mock_result

            mock_client.call_tool.side_effect = delayed_call

            results_task = asyncio.gather(
                asyncio.create_task(
                    mcp_client.simple_call("tool_a", {"x": 1})
                ),
                asyncio.create_task(
                    mcp_client.simple_call("tool_b", {"y": 2})
                ),
            )
            # Wait until both coroutines reached call_tool (i.e. _active_calls
            # is 2), then let them finish.
            await both_started.wait()
            release.set()
            results = await results_task

            assert results == ["", ""]
            # Both calls used the SAME shared connection.
            assert mock_client.call_tool.await_count == 2
            # No immediate teardown while a sibling was in flight: the TTL
            # waiter is scheduled once, after the last active call exits.
            assert mock_close.call_count == 1
            assert mcp_client._active_calls == 0

    @pytest.mark.asyncio
    async def test_simple_call_ttl_minus_one_keeps_resident(self, mcp_client):
        """With connection_ttl == -1 the connection stays resident after a call."""
        mcp_client._close_ttl = -1
        with (
            patch.object(mcp_client, "_connect"),
            patch.object(mcp_client, "close") as mock_close,
            patch.object(mcp_client, "close_no_wait") as mock_close_no_wait,
        ):
            mock_client = AsyncMock()
            # Do NOT suppress exceptions propagating out of `async with`.
            mock_client.__aexit__.return_value = None
            mock_result = MagicMock()
            mock_result.content = []
            mock_client.call_tool.return_value = mock_result
            mcp_client.mcp_client = mock_client

            await mcp_client.simple_call("test_tool", {"param": "value"})

            # Resident pool: neither TTL close nor immediate close is triggered.
            mock_close.assert_not_called()
            mock_close_no_wait.assert_not_called()
            assert mcp_client.mcp_client is mock_client

    @pytest.mark.asyncio
    async def test_close_noop_while_calls_in_flight(self, mcp_client):
        """_close must not tear down a connection with active calls."""
        mock_client = AsyncMock()
        mcp_client.mcp_client = mock_client
        mcp_client._active_calls = 2

        await mcp_client._close()

        # Connection survives: it is still referenced by in-flight calls.
        assert mcp_client.mcp_client is mock_client
        mock_client.__aexit__.assert_not_called()

    @pytest.mark.asyncio
    async def test_connect_already_connected_suppress(self, mcp_client):
        """Test _connect when already connected"""
        mcp_client.mcp_client = AsyncMock()

        await mcp_client._connect()


class TestMultiClientManager:
    @pytest.fixture
    def manager(self):
        # Create a new instance to avoid state pollution
        manager = MultiClientManager()
        manager.clients = []
        manager.script_to_clients = {}
        manager.name_to_clients = {}
        manager.tools_remapping = {}
        manager.reversed_remappings = {}
        return manager

    def test_initialization(self):
        manager = MultiClientManager()
        assert manager.clients == []
        assert manager.script_to_clients == {}
        assert manager.name_to_clients == {}
        assert manager.tools_remapping == {}
        assert manager.reversed_remappings == {}
        assert hasattr(manager, "tools_manager")
        assert manager._is_initialized is False

    def test_get_client_by_script(self):
        manager = MultiClientManager()
        client = manager.get_client_by_script("test_script")
        assert isinstance(client, MCPClient)
        assert client.server_script == "test_script"

    @pytest.mark.asyncio
    async def test_register_only_with_server_script(self):
        manager = MultiClientManager()
        result = manager.register_only(server_script="test_script")
        assert result == manager
        assert len(manager.clients) == 1
        assert isinstance(manager.clients[0], MCPClient)

    @pytest.mark.asyncio
    async def test_register_only_with_client(self):
        manager = MultiClientManager()
        client = MCPClient(server_script="test_script")
        result = manager.register_only(client=client)
        assert result == manager
        assert len(manager.clients) == 1
        assert manager.clients[0] == client

    def test_register_only_without_args(self):
        """Test register_only without required arguments"""
        manager = MultiClientManager()
        with pytest.raises(
            ValueError, match="Please provide MCP Server script or MCP Client"
        ):
            manager.register_only()  # type: ignore

    @pytest.mark.asyncio
    async def test_initialize_this(self):
        manager = MultiClientManager()
        with patch.object(manager, "_load_this") as mock_load:
            result = await manager.initialize_this("test_script")
            assert result == manager
            mock_load.assert_called_once()

    def test_tools_wrapper(self):
        manager = MultiClientManager()
        # Test tools wrapper
        wrapper = manager._tools_wrapper("test_tool")
        assert callable(wrapper)

    @pytest.mark.asyncio
    async def test_get_client_by_tool_name_not_found(self, manager):
        """Test get_client_by_tool_name when tool doesn't exist"""
        with pytest.raises(RuntimeError, match=r"Tool not found: 'nonexistent_tool'"):
            await manager.get_client_by_tool_name("nonexistent_tool")


class TestClientManager:
    def test_singleton_behavior(self):
        # Reset ClientManager state to ensure test accuracy
        ClientManager._instance = None
        ClientManager._initialized = False

        manager1 = ClientManager()
        manager2 = ClientManager()
        assert manager1 is manager2

    def test_inheritance_from_multi_client_manager(self):
        # Reset ClientManager state
        ClientManager._instance = None
        ClientManager._initialized = False

        manager = ClientManager()
        assert isinstance(manager, MultiClientManager)
