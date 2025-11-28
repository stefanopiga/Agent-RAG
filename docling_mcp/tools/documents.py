import json
import logging

from fastmcp import Context
from fastmcp.exceptions import ToolError

from utils.db_utils import get_document, list_documents

logger = logging.getLogger(__name__)


async def list_knowledge_base_documents(
    limit: int = 50, offset: int = 0, ctx: Context = None
) -> str:
    """
    List all documents currently available in the RAG knowledge base.
    Returns a formatted list with titles, sources, and chunk counts.

    Args:
        limit: Maximum number of documents to return (default: 50)
        offset: Offset for pagination (default: 0)
        ctx: MCP Context object (injected by FastMCP)

    Returns:
        A formatted list of documents with metadata
    """
    try:
        if ctx:
            ctx.info(f"Listing documents (limit={limit}, offset={offset})")

        docs = await list_documents(limit, offset)

        if not docs:
            return "No documents found in the knowledge base."

        result = [f"Found {len(docs)} documents:"]
        for doc in docs:
            result.append(
                f"- [{doc.get('source', 'Unknown')}] {doc.get('title', 'Unknown')} "
                f"({doc.get('chunk_count', 0)} chunks, updated: {doc.get('updated_at', 'Unknown')})"
            )

        return "\n".join(result)

    except Exception as e:
        logger.error(f"Error in list_knowledge_base_documents: {e}", exc_info=True)
        raise ToolError(f"Failed to list documents: {str(e)}")


async def get_knowledge_base_document(document_id: str, ctx: Context = None) -> str:
    """
    Get a specific document from the knowledge base by its ID.

    Use this when you need to retrieve the full content of a specific document.
    You can get document IDs from list_knowledge_base_documents or search results.

    Args:
        document_id: The UUID of the document to retrieve.
        ctx: MCP Context object (injected by FastMCP)

    Returns:
        The full document content with metadata, or an error message if not found.
    """
    try:
        if not document_id or not document_id.strip():
            raise ToolError("Document ID cannot be empty.")

        if ctx:
            ctx.info(f"Getting document details for ID: {document_id}")

        doc = await get_document(document_id)

        if not doc:
            raise ToolError(f"Document with ID {document_id} not found")

        # Format document response
        result_parts = [
            f"Document ID: {doc.get('id', document_id)}",
            f"Title: {doc.get('title', 'Unknown')}",
            f"Source: {doc.get('source', 'Unknown')}",
            f"Created: {doc.get('created_at', 'Unknown')}",
            f"Updated: {doc.get('updated_at', 'Unknown')}",
        ]

        metadata = doc.get("metadata", {})
        if metadata:
            result_parts.append(f"\nMetadata: {json.dumps(metadata, indent=2)}")

        content = doc.get("content", "")
        if content:
            result_parts.append(f"\n---\nContent:\n{content}")

        return "\n".join(result_parts)

    except ToolError:
        raise
    except Exception as e:
        logger.error(f"Error in get_knowledge_base_document: {e}", exc_info=True)
        raise ToolError(f"Failed to get document: {str(e)}")
