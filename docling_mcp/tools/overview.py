import logging
from typing import Set

from fastmcp import Context
from fastmcp.exceptions import ToolError

from utils.db_utils import list_documents

logger = logging.getLogger(__name__)


async def get_knowledge_base_overview(ctx: Context = None) -> str:
    """
    Get a high-level overview of the knowledge base.

    Use this at the start of a session to discover what documents are available
    and get summary statistics about the knowledge base.
    Avoid repeated calls within the same session.

    Args:
        ctx: MCP Context object (injected by FastMCP)

    Returns:
        A formatted overview with statistics and document list.
    """
    try:
        if ctx:
            ctx.info("Getting knowledge base overview")

        # Fetch documents to calculate overview stats
        docs = await list_documents(limit=10000)

        total_documents = len(docs)
        total_chunks = sum(doc.get("chunk_count", 0) for doc in docs)

        # Collect unique sources
        sources: Set[str] = set()
        for doc in docs:
            source = doc.get("source", "")
            if source:
                # Get top-level source (e.g., "langfuse-docs" from "langfuse-docs/deployment/guide.md")
                top_source = source.split("/")[0] if "/" in source else source
                sources.add(top_source)

        # Format overview response
        result_parts = [
            "📊 Knowledge Base Overview",
            "=" * 50,
            f"Total Documents: {total_documents}",
            f"Total Chunks: {total_chunks}",
            f"Unique Sources: {len(sources)}",
        ]

        if sources:
            result_parts.append(f"\nSources ({len(sources)}):")
            for source in sorted(sources)[:10]:
                result_parts.append(f"  - {source}")
            if len(sources) > 10:
                result_parts.append(f"  ... and {len(sources) - 10} more")

        if docs:
            result_parts.append(f"\nDocuments ({len(docs)}):")
            for doc in docs[:20]:
                title = doc.get("title", "Unknown")
                source = doc.get("source", "Unknown")
                chunks = doc.get("chunk_count", 0)
                result_parts.append(f"  - [{source}] {title} ({chunks} chunks)")
            if len(docs) > 20:
                result_parts.append(f"  ... and {len(docs) - 20} more")

        return "\n".join(result_parts)

    except Exception as e:
        logger.error(f"Error in get_knowledge_base_overview: {e}", exc_info=True)
        raise ToolError(f"Failed to get overview: {str(e)}")
