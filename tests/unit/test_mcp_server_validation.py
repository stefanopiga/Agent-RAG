"""
Unit tests for MCP Server validation logic (docling_mcp/server.py)

Tests:
- Pre-flight validation (empty query, invalid input)
- Error handling with ToolError
- Input validation for all tools
"""

from unittest.mock import patch

import pytest
from fastmcp.exceptions import ToolError

# Import tools and get the underlying functions via .fn attribute
from docling_mcp.server import (
    ask_knowledge_base,
    get_knowledge_base_document,
    get_knowledge_base_overview,
    list_knowledge_base_documents,
    query_knowledge_base,
)

# Get underlying functions from FunctionTool objects
query_knowledge_base_fn = query_knowledge_base.fn
ask_knowledge_base_fn = ask_knowledge_base.fn
list_knowledge_base_documents_fn = list_knowledge_base_documents.fn
get_knowledge_base_document_fn = get_knowledge_base_document.fn
get_knowledge_base_overview_fn = get_knowledge_base_overview.fn


class TestQueryKnowledgeBaseValidation:
    """Test validation logic in query_knowledge_base."""

    @pytest.mark.asyncio
    async def test_empty_query_returns_no_results(self):
        """Test that empty query returns no results message."""
        with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
            with patch("docling_mcp.server.search_with_embedding") as mock_search:
                mock_embed.return_value = ([0.1] * 1536, 100.0)
                mock_search.return_value = ([], 50.0)

                result = await query_knowledge_base_fn("")

                assert "No relevant information found" in result

    @pytest.mark.asyncio
    async def test_valid_query_returns_results(self):
        """Test that valid query returns formatted results."""
        with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
            with patch("docling_mcp.server.search_with_embedding") as mock_search:
                mock_embed.return_value = ([0.1] * 1536, 100.0)
                mock_search.return_value = (
                    [
                        {
                            "title": "Test Doc",
                            "content": "Test content",
                            "source": "test",
                            "similarity": 0.9,
                        }
                    ],
                    50.0,
                )

                result = await query_knowledge_base_fn("test query", limit=5)

                assert "[Source: Test Doc]" in result
                assert "Test content" in result
                mock_embed.assert_called_once_with("test query")
                mock_search.assert_called_once_with([0.1] * 1536, 5, None)

    @pytest.mark.asyncio
    async def test_source_filter_passed_to_search(self):
        """Test that source_filter is passed correctly."""
        with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
            with patch("docling_mcp.server.search_with_embedding") as mock_search:
                mock_embed.return_value = ([0.1] * 1536, 100.0)
                mock_search.return_value = ([], 50.0)

                await query_knowledge_base_fn("test", limit=5, source_filter="langfuse-docs")

                mock_search.assert_called_once_with([0.1] * 1536, 5, "langfuse-docs")

    @pytest.mark.asyncio
    async def test_error_raises_tool_error(self):
        """Test that search errors raise ToolError."""
        with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
            mock_embed.side_effect = RuntimeError("Database error")

            with pytest.raises(ToolError) as exc_info:
                await query_knowledge_base_fn("test query")

            assert "Failed to query knowledge base" in str(exc_info.value)


class TestAskKnowledgeBaseValidation:
    """Test validation logic in ask_knowledge_base."""

    @pytest.mark.asyncio
    async def test_empty_question_returns_no_info(self):
        """Test that empty question returns no info message when no results found."""
        with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
            with patch("docling_mcp.server.search_with_embedding") as mock_search:
                mock_embed.return_value = ([0.1] * 1536, 100.0)
                mock_search.return_value = ([], 50.0)

                result = await ask_knowledge_base_fn("")

                assert "couldn't find any relevant information" in result

    @pytest.mark.asyncio
    async def test_valid_question_returns_context(self):
        """Test that valid question returns formatted context."""
        with patch("docling_mcp.server.generate_query_embedding") as mock_embed:
            with patch("docling_mcp.server.search_with_embedding") as mock_search:
                mock_embed.return_value = ([0.1] * 1536, 100.0)
                mock_search.return_value = (
                    [
                        {
                            "title": "Test Doc",
                            "content": "Answer content",
                            "source": "test",
                            "similarity": 0.85,
                        }
                    ],
                    50.0,
                )

                result = await ask_knowledge_base_fn("What is test?", limit=3)

                assert "Found 1 relevant results" in result
                assert "Test Doc" in result
                assert "Answer content" in result
                assert "85" in result  # similarity percentage
                mock_embed.assert_called_once_with("What is test?")
                mock_search.assert_called_once_with([0.1] * 1536, 3)


class TestListKnowledgeBaseDocumentsValidation:
    """Test validation logic in list_knowledge_base_documents."""

    @pytest.mark.asyncio
    async def test_empty_list_returns_message(self):
        """Test that empty document list returns appropriate message."""
        with patch("docling_mcp.server.list_documents") as mock_list:
            mock_list.return_value = []

            result = await list_knowledge_base_documents_fn()

            assert "No documents found" in result

    @pytest.mark.asyncio
    async def test_documents_formatted_correctly(self):
        """Test that documents are formatted correctly."""
        with patch("docling_mcp.server.list_documents") as mock_list:
            mock_list.return_value = [
                {
                    "id": "123",
                    "title": "Doc 1",
                    "source": "source-1",
                    "chunk_count": 10,
                    "updated_at": "2025-01-01",
                }
            ]

            result = await list_knowledge_base_documents_fn(limit=50)

            assert "Found 1 documents" in result
            assert "[source-1] Doc 1" in result
            assert "10 chunks" in result
            mock_list.assert_called_once_with(50, 0)


class TestGetKnowledgeBaseDocumentValidation:
    """Test validation logic in get_knowledge_base_document."""

    @pytest.mark.asyncio
    async def test_empty_id_raises_tool_error(self):
        """Test that empty document ID raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            await get_knowledge_base_document_fn("")

        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_whitespace_id_raises_tool_error(self):
        """Test that whitespace-only ID raises ToolError."""
        with pytest.raises(ToolError) as exc_info:
            await get_knowledge_base_document_fn("   ")

        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_not_found_raises_tool_error(self):
        """Test that non-existent document raises ToolError."""
        with patch("docling_mcp.server.get_document") as mock_get:
            mock_get.return_value = None

            with pytest.raises(ToolError) as exc_info:
                await get_knowledge_base_document_fn("nonexistent-id")

            assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_valid_document_returned(self):
        """Test that valid document is returned correctly."""
        with patch("docling_mcp.server.get_document") as mock_get:
            mock_get.return_value = {
                "id": "123",
                "title": "Test Doc",
                "source": "test-source",
                "content": "Test content",
                "metadata": {"key": "value"},
                "created_at": "2025-01-01",
                "updated_at": "2025-01-02",
            }

            result = await get_knowledge_base_document_fn("123")

            assert "Document ID: 123" in result
            assert "Title: Test Doc" in result
            assert "Test content" in result


class TestGetKnowledgeBaseOverviewValidation:
    """Test validation logic in get_knowledge_base_overview."""

    @pytest.mark.asyncio
    async def test_empty_overview(self):
        """Test overview when no documents exist."""
        with patch("docling_mcp.server.list_documents") as mock_list:
            mock_list.return_value = []

            result = await get_knowledge_base_overview_fn()

            assert "Total Documents: 0" in result
            assert "Total Chunks: 0" in result

    @pytest.mark.asyncio
    async def test_overview_with_documents(self):
        """Test overview with documents."""
        with patch("docling_mcp.server.list_documents") as mock_list:
            mock_list.return_value = [
                {"title": "Doc 1", "source": "source-a/path", "chunk_count": 10},
                {"title": "Doc 2", "source": "source-b/path", "chunk_count": 5},
            ]

            result = await get_knowledge_base_overview_fn()

            assert "Total Documents: 2" in result
            assert "Total Chunks: 15" in result
            assert "Unique Sources: 2" in result
