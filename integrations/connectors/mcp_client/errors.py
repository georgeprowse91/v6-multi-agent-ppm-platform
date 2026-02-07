"""Error types for MCP client."""

from __future__ import annotations

from typing import Any


class MCPClientError(Exception):
    """Base error for MCP client."""


class MCPTransportError(MCPClientError):
    """Raised when transport fails."""


class MCPAuthenticationError(MCPClientError):
    """Raised when auth fails."""


class MCPResponseError(MCPClientError):
    """Raised for invalid or unexpected responses."""


class MCPToolNotFoundError(MCPClientError):
    """Raised when a tool is missing from configuration or server."""


class MCPServerError(MCPClientError):
    """Raised when server returns JSON-RPC error."""

    def __init__(self, message: str, code: int | None = None, data: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data
