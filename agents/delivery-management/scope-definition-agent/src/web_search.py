"""Backward-compatible wrapper for shared web search utilities."""

from agents.common.web_search import (  # noqa: F401
    build_search_query,
    search_web,
    summarize_snippets,
)

__all__ = ["search_web", "summarize_snippets", "build_search_query"]
