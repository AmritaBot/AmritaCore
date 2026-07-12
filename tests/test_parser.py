"""Tests for MCP transport URL parser (_parser.py)."""

from __future__ import annotations

import httpx
import pytest
from fastmcp.client.transports import (
    SSETransport,
    StdioTransport,
    StreamableHttpTransport,
)

from amrita_core.tools._parser import (
    TRANSPORT_REGISTRY,
    SHORTHAND_SCHEMES,
    resolve_transport,
)


class TestExtraProtocol:
    """Tests for the EXTRA+PROTOCOL://... pattern."""

    def test_sse_plus_http_basic(self):
        t = resolve_transport("sse+http://127.0.0.1:9178/sse")
        assert isinstance(t, SSETransport)

    def test_sse_plus_https(self):
        t = resolve_transport("sse+https://example.com/sse")
        assert isinstance(t, SSETransport)

    def test_sse_plus_http_no_port(self):
        t = resolve_transport("sse+http://localhost/mcp/sse")
        assert isinstance(t, SSETransport)

    def test_sse_plus_http_no_path(self):
        t = resolve_transport("sse+http://127.0.0.1:8080")
        assert isinstance(t, SSETransport)

    def test_sse_plus_http_with_basic_auth(self):
        t = resolve_transport("sse+http://admin:secret@host:8080/sse")
        assert isinstance(t, SSETransport)
        assert isinstance(t.auth, httpx.BasicAuth)

    def test_sse_plus_http_with_user_only(self):
        t = resolve_transport("sse+http://token@host/sse")
        assert isinstance(t, SSETransport)

    def test_streamable_plus_http(self):
        t = resolve_transport("streamable+http://example.com/mcp")
        assert isinstance(t, StreamableHttpTransport)

    def test_streamable_plus_https(self):
        t = resolve_transport("streamable+https://example.com/mcp")
        assert isinstance(t, StreamableHttpTransport)


class TestShorthand:
    """Tests for shorthand schemes (e.g. sse:// → sse+http://)."""

    def test_sse_shorthand_basic(self):
        t = resolve_transport("sse://127.0.0.1:9178/sse")
        assert isinstance(t, SSETransport)

    def test_sse_shorthand_with_auth(self):
        t = resolve_transport("sse://user:pwd@host/sse")
        assert isinstance(t, SSETransport)
        assert isinstance(t.auth, httpx.BasicAuth)

    def test_sse_shorthand_no_port(self):
        t = resolve_transport("sse://example.com/sse")
        assert isinstance(t, SSETransport)

    def test_sse_shorthand_no_path(self):
        t = resolve_transport("sse://localhost:8080")
        assert isinstance(t, SSETransport)


class TestStdio:
    """Tests for the stdio:// transport."""

    def test_stdio_single_command(self):
        t = resolve_transport('stdio://["python","server.py"]')
        assert isinstance(t, StdioTransport)
        assert t.command == "python"
        assert t.args == ["server.py"]

    def test_stdio_with_args(self):
        t = resolve_transport(
            'stdio://["uvx","mcp-server-git","--verbose","--port","8080"]'
        )
        assert isinstance(t, StdioTransport)
        assert t.command == "uvx"
        assert t.args == ["mcp-server-git", "--verbose", "--port", "8080"]

    def test_stdio_npx(self):
        t = resolve_transport(
            'stdio://["npx","-y","@modelcontextprotocol/server-everything"]'
        )
        assert isinstance(t, StdioTransport)
        assert t.command == "npx"
        assert t.args == ["-y", "@modelcontextprotocol/server-everything"]

    def test_stdio_empty_payload_raises(self):
        with pytest.raises(ValueError, match="must contain a JSON list"):
            resolve_transport("stdio://")

    def test_stdio_non_list_payload_raises(self):
        with pytest.raises(ValueError, match="must be a non-empty JSON list"):
            resolve_transport('stdio://{"not":"a list"}')

    def test_stdio_empty_list_raises(self):
        with pytest.raises(ValueError, match="must be a non-empty JSON list"):
            resolve_transport("stdio://[]")


class TestPassThrough:
    """Tests for inputs that should pass through unchanged."""

    def test_http_passthrough(self):
        t = resolve_transport("http://example.com/mcp")
        assert t == "http://example.com/mcp"

    def test_https_passthrough(self):
        t = resolve_transport("https://example.com/mcp")
        assert t == "https://example.com/mcp"

    def test_file_path_passthrough(self):
        t = resolve_transport("/home/user/my_script.py")
        assert t == "/home/user/my_script.py"

    def test_relative_path_passthrough(self):
        t = resolve_transport("script.py")
        assert t == "script.py"

    def test_unknown_extra_passthrough(self):
        t = resolve_transport("unknown+http://host/path")
        assert t == "unknown+http://host/path"


class TestEdgeCases:
    """Edge case tests."""

    def test_whitespace_stripping(self):
        t = resolve_transport("  sse+http://127.0.0.1:9178/sse  ")
        assert isinstance(t, SSETransport)

    def test_sse_plus_http_ipv4(self):
        t = resolve_transport("sse+http://192.168.1.1:3000/sse")
        assert isinstance(t, SSETransport)

    def test_host_with_dashes(self):
        t = resolve_transport("sse+http://my-mcp-server.local/sse")
        assert isinstance(t, SSETransport)

    def test_streamable_with_auth_is_passthrough(self):
        """streamable doesn't attach auth, but shouldn't crash."""
        t = resolve_transport("streamable+http://user:pwd@host/mcp")
        # StreamableHttpTransport is returned, auth is simply ignored
        assert isinstance(t, StreamableHttpTransport)


class TestRegistryIntegrity:
    """Verify registry / shorthand structures are consistent."""

    def test_sse_in_registry(self):
        assert "sse" in TRANSPORT_REGISTRY

    def test_streamable_in_registry(self):
        assert "streamable" in TRANSPORT_REGISTRY

    def test_sse_in_shorthands(self):
        assert "sse" in SHORTHAND_SCHEMES
        assert SHORTHAND_SCHEMES["sse"] == ("sse", "http")

    def test_all_shorthands_refer_to_valid_registry_entries(self):
        for extra, _proto in SHORTHAND_SCHEMES.values():
            assert extra in TRANSPORT_REGISTRY
