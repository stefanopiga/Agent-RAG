"""
MCP Server
==========
Exposes the RAG agent capabilities as a Model Context Protocol (MCP) server.
Compatible with Cursor, Claude Desktop, and other MCP clients.

Architecture:
- Standalone server with direct service integration (no HTTP proxy)
- Uses core/rag_service.py directly for RAG operations
- LangFuse integration for observability tracing (graceful degradation if unavailable)
- Cost tracking via langfuse.openai wrapper in embedder (automatic token/cost calculation)
- Prometheus metrics for performance monitoring (/metrics endpoint)
- Health check endpoint (/health) for service status monitoring
"""

import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Dict, Optional, Set, TypeVar

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from core.rag_service import (
    generate_query_embedding,
    search_with_embedding,
)
from docling_mcp.lifespan import lifespan
from docling_mcp.metrics import (
    record_db_search_time,
    record_embedding_time,
    record_request_end,
    record_request_start,
)
from utils.db_utils import get_document, list_documents

F = TypeVar("F", bound=Callable[..., Any])


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import LangFuse observe decorator with graceful fallback
try:
    from langfuse import get_client as get_langfuse_client
    from langfuse import observe

    _langfuse_available = True
except ImportError:
    _langfuse_available = False
    get_langfuse_client = None

    # Create no-op decorator as fallback
    def observe(name=None, **kwargs):  # type: ignore[misc]
        def decorator(func: F) -> F:
            return func

        return decorator

    logger.info("LangFuse SDK not installed, tracing disabled")


@asynccontextmanager
async def langfuse_span(
    name: str, span_type: str = "span", metadata: dict = None
) -> AsyncGenerator[Any, None]:
    """
    Create a nested LangFuse span for cost tracking and timing breakdown.

    Args:
        name: Name of the span (e.g., "embedding-generation", "vector-search")
        span_type: Type of span ("span" for general, "generation" for LLM calls)
        metadata: Optional metadata to attach to the span

    Yields:
        A dict with 'span' (LangFuse span or None) and 'start_time' for timing.

    Note:
        - Gracefully degrades to no-op if LangFuse unavailable
        - Always records timing in span metadata (duration_ms)
        - Also records to Prometheus metrics for embedding and db_search spans
    """
    start_time = time.time()
    span = None
    span_context = {"span": None, "start_time": start_time}

    if _langfuse_available and get_langfuse_client is not None:
        try:
            client = get_langfuse_client()
            if client is not None:
                # LangFuse client has span method but mypy doesn't recognize it
                # Use getattr to avoid mypy error
                span_method = getattr(client, "span", None)
                if span_method is not None:
                    span = span_method(name=name, metadata=metadata or {})
                    span_context["span"] = span
        except Exception as e:
            logger.debug(f"LangFuse span creation failed (graceful degradation): {e}")

    try:
        yield span_context
    finally:
        # Calculate duration
        duration_seconds = time.time() - start_time
        duration_ms = duration_seconds * 1000

        # Update span metadata with timing
        if span is not None:
            try:
                span.update(metadata={**(metadata or {}), "duration_ms": duration_ms})
                span.end()
            except Exception as e:
                logger.debug(f"Failed to update span timing: {e}")

        # Record to Prometheus metrics based on span type
        try:
            if name == "embedding-generation":
                record_embedding_time(duration_seconds)
            elif name == "vector-search":
                record_db_search_time(duration_seconds)
        except Exception:
            pass  # Graceful degradation for metrics


def _update_langfuse_metadata(metadata: dict) -> None:
    """
    Update LangFuse span metadata with graceful degradation.

    Args:
        metadata: Dictionary of metadata to add to the current span.
    """
    if not _langfuse_available:
        return
    try:
        from langfuse import get_client

        get_client().update_current_span(metadata=metadata)
    except Exception:
        pass  # Graceful degradation - don't fail if LangFuse unavailable


# Initialize FastMCP server
mcp = FastMCP("Docling RAG Agent", lifespan=lifespan)

# Import and register tools using decorator
# Tools are defined in their respective modules with @mcp.tool() applied during import


@mcp.tool()
@observe(name="query_knowledge_base")
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

    Cost Tracking:
        Embedding generation cost is automatically tracked via langfuse.openai wrapper.
        Cost breakdown visible in LangFuse trace under "embedding-generation" span.

    Performance Metrics:
        - Request duration tracked in Prometheus (mcp_request_duration_seconds)
        - Embedding time tracked (rag_embedding_time_seconds)
        - DB search time tracked (rag_db_search_time_seconds)
    """
    tool_name = "query_knowledge_base"
    request_start = record_request_start(tool_name)
    status = "success"

    try:
        _update_langfuse_metadata(
            {
                "tool_name": tool_name,
                "query": query,
                "limit": limit,
                "source_filter": source_filter,
                "source": "mcp",
            }
        )

        if ctx:
            await ctx.info(f"Searching knowledge base for: '{query}'")

        # Create separate LangFuse spans for embedding and DB search (AC #2)
        # This provides granular timing breakdown in LangFuse dashboard

        # Span 1: Embedding generation
        async with langfuse_span(
            name="embedding-generation",
            span_type="span",
            metadata={"query_length": len(query), "model": "text-embedding-3-small"},
        ) as embed_span:
            query_embedding, embedding_ms = await generate_query_embedding(query)
            if embed_span.get("span"):
                try:
                    embed_span["span"].update(
                        metadata={
                            "embedding_time_ms": embedding_ms,
                            "embedding_dim": len(query_embedding),
                        }
                    )
                except Exception:
                    pass

        # Span 2: Vector database search
        async with langfuse_span(
            name="vector-search",
            span_type="span",
            metadata={"limit": limit, "source_filter": source_filter},
        ) as search_span:
            results_list, db_ms = await search_with_embedding(query_embedding, limit, source_filter)
            if search_span.get("span"):
                try:
                    search_span["span"].update(
                        metadata={"db_search_time_ms": db_ms, "results_count": len(results_list)}
                    )
                except Exception:
                    pass

        # Build results dict for compatibility
        results = {
            "results": results_list,
            "timing": {"embedding_ms": embedding_ms, "db_ms": db_ms},
        }

        if not results_list:
            filter_msg = f" in '{source_filter}'" if source_filter else ""
            return (
                f"No relevant information found in the knowledge base{filter_msg} for your query."
            )

        response_parts = []
        for row in results["results"]:
            row_dict: Dict[str, Any] = row  # type: ignore[assignment]
            title = row_dict.get("title", "Unknown")
            content = row_dict.get("content", "")
            response_parts.append(f"[Source: {title}]\n{content}\n")

        return "\n---\n".join(response_parts)

    except Exception as e:
        status = "error"
        logger.error(f"Error in query_knowledge_base: {e}", exc_info=True)
        raise ToolError(f"Failed to query knowledge base: {str(e)}")
    finally:
        record_request_end(tool_name, request_start, status)


@mcp.tool()
@observe(name="ask_knowledge_base")
async def ask_knowledge_base(question: str, limit: int = 5, ctx: Context = None) -> str:
    """
    Ask the knowledge base a question and get an answer.

    This tool performs semantic search and returns relevant information from the knowledge base.
    Use this when the user asks a direct question that needs to be answered using the knowledge base.

    Args:
        question: The question to ask the knowledge base.
        limit: Maximum number of results to return (default: 5).

    Cost Tracking:
        Embedding generation cost is automatically tracked via langfuse.openai wrapper.
        Cost breakdown visible in LangFuse trace under "embedding-generation" span.

    Performance Metrics:
        - Request duration tracked in Prometheus (mcp_request_duration_seconds)
        - Embedding time tracked (rag_embedding_time_seconds)
        - DB search time tracked (rag_db_search_time_seconds)
    """
    tool_name = "ask_knowledge_base"
    request_start = record_request_start(tool_name)
    status = "success"

    try:
        _update_langfuse_metadata(
            {"tool_name": tool_name, "question": question, "limit": limit, "source": "mcp"}
        )

        if ctx:
            await ctx.info(f"Asking knowledge base: '{question}'")

        # Create separate LangFuse spans for embedding and DB search (AC #2)
        # This provides granular timing breakdown in LangFuse dashboard

        # Span 1: Embedding generation
        async with langfuse_span(
            name="embedding-generation",
            span_type="span",
            metadata={"question_length": len(question), "model": "text-embedding-3-small"},
        ) as embed_span:
            query_embedding, embedding_ms = await generate_query_embedding(question)
            if embed_span.get("span"):
                try:
                    embed_span["span"].update(
                        metadata={
                            "embedding_time_ms": embedding_ms,
                            "embedding_dim": len(query_embedding),
                        }
                    )
                except Exception:
                    pass

        # Span 2: Vector database search
        async with langfuse_span(
            name="vector-search", span_type="span", metadata={"limit": limit}
        ) as search_span:
            results_list, db_ms = await search_with_embedding(query_embedding, limit)
            if search_span.get("span"):
                try:
                    search_span["span"].update(
                        metadata={"db_search_time_ms": db_ms, "results_count": len(results_list)}
                    )
                except Exception:
                    pass

        if not results_list:
            return "I couldn't find any relevant information in the knowledge base to answer your question."

        response_parts = [f"Found {len(results_list)} relevant results for your question:\n"]

        for i, row in enumerate(results_list, 1):
            row_dict: Dict[str, Any] = row  # type: ignore[assignment]
            title = row_dict.get("title", "Unknown")
            source = row_dict.get("source", "Unknown")
            content = row_dict.get("content", "")
            similarity = row_dict.get("similarity", 0)

            response_parts.append(
                f"--- Result {i} (relevance: {similarity:.2%}) ---\n"
                f"Source: {title} ({source})\n"
                f"Content:\n{content}\n"
            )

        return "\n".join(response_parts)

    except Exception as e:
        status = "error"
        logger.error(f"Error in ask_knowledge_base: {e}", exc_info=True)
        raise ToolError(f"Failed to search knowledge base: {str(e)}")
    finally:
        record_request_end(tool_name, request_start, status)


@mcp.tool()
@observe(name="list_knowledge_base_documents")
async def list_knowledge_base_documents(
    limit: int = 50, offset: int = 0, ctx: Context = None
) -> str:
    """
    List all documents currently available in the RAG knowledge base.
    Returns a formatted list with titles, sources, and chunk counts.

    Args:
        limit: Maximum number of documents to return (default: 50)
        offset: Offset for pagination (default: 0)

    Performance Metrics:
        Request duration tracked in Prometheus (mcp_request_duration_seconds)
    """
    tool_name = "list_knowledge_base_documents"
    request_start = record_request_start(tool_name)
    status = "success"

    try:
        _update_langfuse_metadata(
            {"tool_name": tool_name, "limit": limit, "offset": offset, "source": "mcp"}
        )

        if ctx:
            await ctx.info(f"Listing documents (limit={limit}, offset={offset})")

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
        status = "error"
        logger.error(f"Error in list_knowledge_base_documents: {e}", exc_info=True)
        raise ToolError(f"Failed to list documents: {str(e)}")
    finally:
        record_request_end(tool_name, request_start, status)


@mcp.tool()
@observe(name="get_knowledge_base_document")
async def get_knowledge_base_document(document_id: str, ctx: Context = None) -> str:
    """
    Get a specific document from the knowledge base by its ID.

    Use this when you need to retrieve the full content of a specific document.
    You can get document IDs from list_knowledge_base_documents or search results.

    Args:
        document_id: The UUID of the document to retrieve.

    Performance Metrics:
        Request duration tracked in Prometheus (mcp_request_duration_seconds)
    """
    tool_name = "get_knowledge_base_document"
    request_start = record_request_start(tool_name)
    status = "success"

    try:
        _update_langfuse_metadata(
            {"tool_name": tool_name, "document_id": document_id, "source": "mcp"}
        )

        if not document_id or not document_id.strip():
            raise ToolError("Document ID cannot be empty.")

        if ctx:
            await ctx.info(f"Getting document details for ID: {document_id}")

        doc = await get_document(document_id)

        if not doc:
            raise ToolError(f"Document with ID {document_id} not found")

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
        status = "error"
        raise
    except Exception as e:
        status = "error"
        logger.error(f"Error in get_knowledge_base_document: {e}", exc_info=True)
        raise ToolError(f"Failed to get document: {str(e)}")
    finally:
        record_request_end(tool_name, request_start, status)


@mcp.tool()
@observe(name="get_knowledge_base_overview")
async def get_knowledge_base_overview(ctx: Context = None) -> str:
    """
    Get a high-level overview of the knowledge base.

    Use this at the start of a session to discover what documents are available
    and get summary statistics about the knowledge base.
    Avoid repeated calls within the same session.

    Performance Metrics:
        Request duration tracked in Prometheus (mcp_request_duration_seconds)
    """
    tool_name = "get_knowledge_base_overview"
    request_start = record_request_start(tool_name)
    status = "success"

    try:
        _update_langfuse_metadata({"tool_name": tool_name, "source": "mcp"})

        if ctx:
            await ctx.info("Getting knowledge base overview")

        docs = await list_documents(limit=10000)

        total_documents = len(docs)
        total_chunks = sum(doc.get("chunk_count", 0) for doc in docs)

        sources: Set[str] = set()
        for doc in docs:
            source = doc.get("source", "")
            if source:
                top_source = source.split("/")[0] if "/" in source else source
                sources.add(top_source)

        result_parts = [
            "Knowledge Base Overview",
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
        status = "error"
        logger.error(f"Error in get_knowledge_base_overview: {e}", exc_info=True)
        raise ToolError(f"Failed to get overview: {str(e)}")
    finally:
        record_request_end(tool_name, request_start, status)


if __name__ == "__main__":
    mcp.run()
