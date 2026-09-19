"""MCP transport URL parser — resolves EXTRA+PROTOCOL:// and shorthands to fastmcp transports."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable
from typing import Any

from fastmcp.client.transports import (
    SSETransport,
    StdioTransport,
    StreamableHttpTransport,
)

#  Transport factories


def _httpx_module() -> Any:
    """Return the ``httpx`` flavour fastmcp's HTTP transports are built on.

    fastmcp 3.x drives its transports with ``httpx``; fastmcp 4.x moved to
    ``httpx2`` and hands the ``auth`` object straight to the new client, so a
    mismatched flavour is only rejected once the connection is opened.
    """
    transports_module = sys.modules.get(SSETransport.__module__)
    httpx2 = (
        getattr(transports_module, "httpx2", None)
        if transports_module is not None
        else None
    )
    if httpx2 is not None:
        return httpx2

    import httpx

    return httpx


def _make_sse_transport(
    url: str, username: str | None, password: str | None
) -> SSETransport:
    if username and password:
        return SSETransport(url=url, auth=_httpx_module().BasicAuth(username, password))
    if username:
        return SSETransport(url=url, auth=username)
    return SSETransport(url=url)


def _make_streamable_transport(
    url: str, username: str | None, password: str | None
) -> StreamableHttpTransport:
    return StreamableHttpTransport(url=url)


# Registry: extra -> factory(url, username, password)
TRANSPORT_REGISTRY: dict[
    str, Callable[[str, str | None, str | None], SSETransport | StreamableHttpTransport]
] = {
    "sse": _make_sse_transport,
    "streamable": _make_streamable_transport,
}

# Shorthand: scheme -> (extra, protocol), e.g. sse://host -> sse+http://host
SHORTHAND_SCHEMES: dict[str, tuple[str, str]] = {
    "sse": ("sse", "http"),
}

ResolvedTransport = str | SSETransport | StreamableHttpTransport | StdioTransport

#  Compiled regexes

_EXTRA_PROTO_RE = re.compile(
    r"^(?P<extra>[a-z][a-z0-9-]*)\+(?P<protocol>[a-z][a-z0-9.+-]*)://"
    r"((?P<user>[^:@]+)(:(?P<password>[^@]+))?@)?"
    r"(?P<host>[^:/]+)(:(?P<port>\d+))?"
    r"(?P<path>/.*)?$",
    re.IGNORECASE,
)

_SHORTHAND_RE = re.compile(
    r"^(?P<shorthand>[a-z][a-z0-9-]*)://"
    r"((?P<user>[^:@]+)(:(?P<password>[^@]+))?@)?"
    r"(?P<host>[^:/]+)(:(?P<port>\d+))?"
    r"(?P<path>/.*)?$",
    re.IGNORECASE,
)


def resolve_transport(server_script: str) -> ResolvedTransport:
    """Resolve a URL-based transport string into the appropriate fastmcp transport.

    **extra+protocol** (general)::

        EXTRA+PROTOCOL://[user:pwd@]host[:port]/path

    **Shorthand** (backward compat)::

        SHORTHAND://[user:pwd@]host[:port]/path

    **Stdio**::

        stdio://["cmd","arg1",...]

    All other inputs (``http://``, ``https://``, file paths) pass through to fastmcp.
    """
    script = server_script.strip()

    #  stdio://[...]
    if script.startswith("stdio://"):
        payload = script[len("stdio://") :]
        if not payload:
            raise ValueError(
                'stdio:// URL must contain a JSON list, e.g. stdio://["uvx","mcp-server-git"]'
            )
        cmd_list: list[str] = json.loads(payload)
        if not cmd_list or not isinstance(cmd_list, list):
            raise ValueError(
                f"stdio:// payload must be a non-empty JSON list, got: {payload!r}"
            )
        command, *args = cmd_list
        return StdioTransport(command=command, args=args)

    #  Shorthand: sse://... -> sse+http://...
    if m := _SHORTHAND_RE.match(script):
        shorthand = m.group("shorthand")
        if shorthand in SHORTHAND_SCHEMES and "+" not in script.split("://")[0]:
            extra, proto = SHORTHAND_SCHEMES[shorthand]
            script = f"{extra}+{proto}://" + m.group(0)[len(shorthand) + 3 :]

    #  extra+protocol
    if m := _EXTRA_PROTO_RE.match(script):
        extra = m.group("extra")
        if extra not in TRANSPORT_REGISTRY:
            return script
        # Build canonical URL: protocol://[user:pwd@]host[:port]/path
        user = m.group("user") or ""
        pwd = m.group("password") or ""
        auth_prefix = f"{user}:{pwd}@" if user else ""
        port = m.group("port") or ""
        port_part = f":{port}" if port else ""
        path = m.group("path") or ""
        real_url = (
            f"{m.group('protocol')}://{auth_prefix}{m.group('host')}{port_part}{path}"
        )
        return TRANSPORT_REGISTRY[extra](real_url, m.group("user"), m.group("password"))

    #  Pass-through
    return script
