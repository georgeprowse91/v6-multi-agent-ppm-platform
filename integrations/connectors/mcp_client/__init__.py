"""MCP client package for connector integrations."""

from .auth import AuthConfig
from .client import MCPClient
from .errors import (
    MCPAuthenticationError,
    MCPClientError,
    MCPResponseError,
    MCPServerError,
    MCPToolNotFoundError,
    MCPTransportError,
)
from .models import MCPToolSchema

__all__ = [
    "AuthConfig",
    "MCPClient",
    "MCPAuthenticationError",
    "MCPClientError",
    "MCPResponseError",
    "MCPServerError",
    "MCPToolNotFoundError",
    "MCPTransportError",
    "MCPToolSchema",
]
