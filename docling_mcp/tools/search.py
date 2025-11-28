import logging
from typing import Optional

from fastmcp import Context
from fastmcp.exceptions import ToolError

from core.rag_service import search_knowledge_base_structured

logger = logging.getLogger(__name__)


async def query_knowledge_base(
    query: str, limit: int = 5, source_filter: Optional[str] = None, ctx: Context = None
) -> str:
    """
    Search the knowledge base using semantic similarity.

    Use this tool when the user asks questions about the documentation or knowledge base.

    Args:
        query: The search query to find relevant information
        limit: Maximum number of results to return (default: 5)
        source_filter: Optional filter to search only in specific documentation sources.
                      Examples: "langfuse-docs", "docling", "langfuse-docs/deployment".
                      If provided, only documents whose source path contains this string will be searched.
        ctx: MCP Context object (injected by FastMCP)

    Returns:
        A formatted string containing the search results with source citations
    """
    try:
        if ctx:
            ctx.info(f"Searching knowledge base for: '{query}'")

        results = await search_knowledge_base_structured(query, limit, source_filter)

        if not results or not results.get("results"):
            filter_msg = f" in '{source_filter}'" if source_filter else ""
            return (
                f"No relevant information found in the knowledge base{filter_msg} for your query."
            )

        response_parts = []
        for row in results["results"]:
            title = row.get("title", "Unknown")
            content = row.get("content", "")
            response_parts.append(f"[Source: {title}]\n{content}\n")

        return "\n---\n".join(response_parts)

    except Exception as e:
        logger.error(f"Error in query_knowledge_base: {e}", exc_info=True)
        raise ToolError(f"Failed to query knowledge base: {str(e)}")


async def ask_knowledge_base(question: str, limit: int = 5, ctx: Context = None) -> str:
    """
    Ask the knowledge base a question and get an answer.

    This tool performs semantic search and returns relevant information from the knowledge base.
    Use this when the user asks a direct question that needs to be answered using the knowledge base.

    Args:
        question: The question to ask the knowledge base.
        limit: Maximum number of results to return (default: 5).
        ctx: MCP Context object (injected by FastMCP)

    Returns:
        Relevant information from the knowledge base formatted as a response.
    """
    try:
        if ctx:
            ctx.info(f"Asking knowledge base: '{question}'")

        # Search for relevant context
        search_results = await search_knowledge_base_structured(question, limit=limit)

        if not search_results or not search_results.get("results"):
            return "I couldn't find any relevant information in the knowledge base to answer your question."

        # Format results as context for the LLM client to use
        response_parts = [
            f"Found {len(search_results['results'])} relevant results for your question:\n"
        ]

        for i, row in enumerate(search_results["results"], 1):
            title = row.get("title", "Unknown")
            source = row.get("source", "Unknown")
            content = row.get("content", "")
            similarity = row.get("similarity", 0)

            response_parts.append(
                f"--- Result {i} (relevance: {similarity:.2%}) ---\n"
                f"Source: {title} ({source})\n"
                f"Content:\n{content}\n"
            )

        return "\n".join(response_parts)

    except Exception as e:
        logger.error(f"Error in ask_knowledge_base: {e}", exc_info=True)
        raise ToolError(f"Failed to search knowledge base: {str(e)}")
