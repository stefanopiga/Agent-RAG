"""
Docling MCP Server Module
=========================
MCP server with direct service integration for RAG capabilities.
"""

from docling_mcp.server import (
    ask_knowledge_base,
    get_knowledge_base_document,
    get_knowledge_base_overview,
    list_knowledge_base_documents,
    mcp,
    query_knowledge_base,
)

__all__ = [
    "mcp",
    "query_knowledge_base",
    "ask_knowledge_base",
    "list_knowledge_base_documents",
    "get_knowledge_base_document",
    "get_knowledge_base_overview",
]
