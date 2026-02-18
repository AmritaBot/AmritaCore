from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amrita_core.tools.mcp import (
    NOT_GIVEN,
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
            patch.object(mcp_client, "_close") as mock_close,
        ):
            # Mock mcp_client instance
            mock_client = AsyncMock()
            mock_result = MagicMock()
            mock_result.content = []
            mock_client.call_tool.return_value = mock_result

            mcp_client.mcp_client = mock_client

            await mcp_client.simple_call("test_tool", {"param": "value"})

            # Verify that the tool was called correctly
            mock_client.call_tool.assert_called_once_with(
                "test_tool", {"param": "value"}
            )
            mock_close.assert_called_once()


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


def test_not_given():
    # Test NOT_GIVEN class
    assert NOT_GIVEN is not None
    assert isinstance(NOT_GIVEN, type)
