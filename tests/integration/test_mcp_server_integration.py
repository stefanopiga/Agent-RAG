"""
Integration tests for MCP Server (docling_mcp/)

Tests:
- End-to-end flow with direct service integration
- Error propagation from core services to MCP tools
- Tool registration and server initialization
"""

from unittest.mock import patch

import pytest

# Import tools and get the underlying functions via .fn attribute
from docling_mcp.server import (
    ask_knowledge_base,
    get_knowledge_base_document,
    get_knowledge_base_overview,
    list_knowledge_base_documents,
    mcp,
    query_knowledge_base,
)

# Get underlying functions from FunctionTool objects
query_knowledge_base_fn = query_knowledge_base.fn
ask_knowledge_base_fn = ask_knowledge_base.fn
list_knowledge_base_documents_fn = list_knowledge_base_documents.fn
get_knowledge_base_document_fn = get_knowledge_base_document.fn
get_knowledge_base_overview_fn = get_knowledge_base_overview.fn


class TestMCPServerIntegration:
    """Integration tests for MCP server tools."""

    @pytest.mark.asyncio
    async def test_query_knowledge_base_full_flow(self):
        """Test complete flow of query_knowledge_base with successful response."""
        with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
            with patch("docling_mcp.server.search_with_embedding") as mock_search:
                mock_embed.return_value = ([0.1] * 1536, 100.0)
                mock_search.return_value = (
                    [
                        {
                            "title": "Document 1",
                            "content": "Content from document 1",
                            "source": "source-1",
                            "similarity": 0.95,
                        },
                        {
                            "title": "Document 2",
                            "content": "Content from document 2",
                            "source": "source-2",
                            "similarity": 0.85,
                        },
                    ],
                    50.0,
                )

                result = await query_knowledge_base_fn(
                    query="test query", limit=5, source_filter="test-source"
                )

                assert "[Source: Document 1]" in result
                assert "[Source: Document 2]" in result
                assert "Content from document 1" in result
                assert "Content from document 2" in result
                assert "---" in result  # Separator between results

                mock_embed.assert_called_once_with("test query")
                mock_search.assert_called_once_with([0.1] * 1536, 5, "test-source")

    @pytest.mark.asyncio
    async def test_query_knowledge_base_no_results(self):
        """Test query_knowledge_base when no results are found."""
        with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
            with patch("docling_mcp.server.search_with_embedding") as mock_search:
                mock_embed.return_value = ([0.1] * 1536, 100.0)
                mock_search.return_value = ([], 50.0)

                result = await query_knowledge_base_fn("test query")

                assert "No relevant information found" in result
                assert "knowledge base" in result

    @pytest.mark.asyncio
    async def test_ask_knowledge_base_full_flow(self):
        """Test complete flow of ask_knowledge_base."""
        with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
            with patch("docling_mcp.server.search_with_embedding") as mock_search:
                mock_embed.return_value = ([0.1] * 1536, 100.0)
                mock_search.return_value = (
                    [
                        {
                            "title": "Answer Doc",
                            "content": "This is the answer content",
                            "source": "docs/answer.md",
                            "similarity": 0.92,
                        }
                    ],
                    50.0,
                )

                result = await ask_knowledge_base_fn("What is the answer?", limit=3)

                assert "Found 1 relevant results" in result
                assert "Answer Doc" in result
                assert "This is the answer content" in result
                assert "92" in result  # similarity percentage

                mock_embed.assert_called_once_with("What is the answer?")
                mock_search.assert_called_once_with([0.1] * 1536, 3)

    @pytest.mark.asyncio
    async def test_list_knowledge_base_documents_full_flow(self):
        """Test complete flow of list_knowledge_base_documents."""
        with patch("docling_mcp.server.list_documents") as mock_list:
            mock_list.return_value = [
                {
                    "id": "doc-1",
                    "title": "Doc 1",
                    "source": "source-1",
                    "chunk_count": 10,
                    "updated_at": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "doc-2",
                    "title": "Doc 2",
                    "source": "source-2",
                    "chunk_count": 5,
                    "updated_at": "2025-01-02T00:00:00Z",
                },
            ]

            result = await list_knowledge_base_documents_fn()

            assert "Found 2 documents:" in result
            assert "[source-1] Doc 1" in result
            assert "[source-2] Doc 2" in result
            assert "10 chunks" in result
            assert "5 chunks" in result

            mock_list.assert_called_once_with(50, 0)

    @pytest.mark.asyncio
    async def test_list_knowledge_base_documents_empty(self):
        """Test list_knowledge_base_documents when no documents exist."""
        with patch("docling_mcp.server.list_documents") as mock_list:
            mock_list.return_value = []

            result = await list_knowledge_base_documents_fn()

            assert "No documents found" in result

    @pytest.mark.asyncio
    async def test_get_knowledge_base_document_full_flow(self):
        """Test complete flow of get_knowledge_base_document."""
        with patch("docling_mcp.server.get_document") as mock_get:
            mock_get.return_value = {
                "id": "doc-123",
                "title": "Full Document",
                "source": "docs/full.md",
                "content": "Full document content here",
                "metadata": {"author": "test"},
                "created_at": "2025-01-01",
                "updated_at": "2025-01-02",
            }

            result = await get_knowledge_base_document_fn("doc-123")

            assert "Document ID: doc-123" in result
            assert "Title: Full Document" in result
            assert "Source: docs/full.md" in result
            assert "Full document content here" in result

            mock_get.assert_called_once_with("doc-123")

    @pytest.mark.asyncio
    async def test_get_knowledge_base_overview_full_flow(self):
        """Test complete flow of get_knowledge_base_overview."""
        with patch("docling_mcp.server.list_documents") as mock_list:
            mock_list.return_value = [
                {"title": "Doc 1", "source": "langfuse-docs/guide.md", "chunk_count": 10},
                {"title": "Doc 2", "source": "langfuse-docs/api.md", "chunk_count": 8},
                {"title": "Doc 3", "source": "docling/readme.md", "chunk_count": 5},
            ]

            result = await get_knowledge_base_overview_fn()

            assert "Total Documents: 3" in result
            assert "Total Chunks: 23" in result
            assert "Unique Sources: 2" in result  # langfuse-docs, docling
            assert "langfuse-docs" in result
            assert "docling" in result


class TestMCPServerToolRegistration:
    """Test that tools are properly registered with FastMCP."""

    @pytest.mark.asyncio
    async def test_all_tools_registered(self):
        """Test that all expected tools are registered."""
        tools = await mcp.get_tools()
        tool_names = list(tools.keys())

        expected_tools = [
            "query_knowledge_base",
            "list_knowledge_base_documents",
            "get_knowledge_base_document",
            "get_knowledge_base_overview",
            "ask_knowledge_base",
        ]

        for tool in expected_tools:
            assert tool in tool_names, f"Tool '{tool}' not found in registered tools"
