"""Models for MCP client responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MCPToolSchema:
    """Represents a tool schema from an MCP server."""

    name: str
    description: str | None
    input_schema: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MCPToolSchema":
        return cls(
            name=payload.get("name", ""),
            description=payload.get("description"),
            input_schema=payload.get("inputSchema", {}) or {},
        )


@dataclass(frozen=True)
class MCPResource:
    """Represents a resource descriptor from an MCP server."""

    uri: str
    name: str | None
    description: str | None
    mime_type: str | None
    annotations: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MCPResource":
        return cls(
            uri=payload.get("uri", ""),
            name=payload.get("name"),
            description=payload.get("description"),
            mime_type=payload.get("mimeType"),
            annotations=payload.get("annotations", {}) or {},
        )


@dataclass(frozen=True)
class MCPPrompt:
    """Represents a prompt descriptor from an MCP server."""

    name: str
    description: str | None
    arguments: list[dict[str, Any]]
    annotations: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MCPPrompt":
        return cls(
            name=payload.get("name", ""),
            description=payload.get("description"),
            arguments=payload.get("arguments", []) or [],
            annotations=payload.get("annotations", {}) or {},
        )


@dataclass(frozen=True)
class JsonRpcError:
    code: int
    message: str
    data: Any | None = None


@dataclass(frozen=True)
class JsonRpcResponse:
    id: str | int | None
    result: Any | None
    error: JsonRpcError | None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JsonRpcResponse":
        error_payload = payload.get("error")
        error = None
        if error_payload:
            error = JsonRpcError(
                code=error_payload.get("code", 0),
                message=error_payload.get("message", "Unknown error"),
                data=error_payload.get("data"),
            )
        return cls(
            id=payload.get("id"),
            result=payload.get("result"),
            error=error,
        )
