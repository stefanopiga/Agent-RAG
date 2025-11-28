"""
PydanticAI Agent Definition
===========================
Defines the agent and its tools, wrapping the core RAG service.
"""

import logging

from pydantic_ai import Agent, RunContext

from client.api_client import RAGClient

logger = logging.getLogger(__name__)

# Initialize client
# In a real app, base_url might come from env vars
client = RAGClient()


async def search_knowledge_base(
    ctx: RunContext[None], query: str, limit: int = 5, source_filter: str | None = None
) -> str:
    """
    Search the knowledge base using semantic similarity.

    Args:
        query: The search query to find relevant information
        limit: Maximum number of results to return (default: 5)
        source_filter: Optional filter to search only in specific documentation sources.
                      Examples: "langfuse-docs", "docling", "langfuse-docs/deployment"
                      If provided, only documents whose source path contains this string will be searched.

    Returns:
        Formatted search results with source citations
    """
    try:
        # Call API
        response = await client.search(query, limit, source_filter)
        results = response.get("results", [])

        if not results:
            filter_msg = f" in '{source_filter}'" if source_filter else ""
            return (
                f"No relevant information found in the knowledge base{filter_msg} for your query."
            )

        # Format results for LLM consumption
        response_parts = []
        for row in results:
            # Handle both dictionary access (API) and object access (if we were local)
            # API returns dicts
            title = row.get("title", "Unknown")
            content = row.get("content", "")

            response_parts.append(f"[Source: {title}]\n{content}\n")

        return "\n---\n".join(response_parts)

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"Error searching knowledge base: {str(e)}"


# Create the PydanticAI agent with the RAG tool
agent = Agent(
    "openai:gpt-4o-mini",
    system_prompt="""You are a knowledgeable assistant equipped with access to organizational documentation and data resources.
Your primary function is to assist users in locating precise information from the available knowledge repository.
Maintain a cordial and professional communication style.

CRITICAL: You must query the knowledge base first when responding to questions requiring specific information.

IMPORTANT FILTERING CAPABILITY:
- When users specify a particular documentation source (e.g., "Docling docs", "Langfuse documentation"),
  use the source_filter parameter to search only within that documentation.
- Common source filters: "docling", "langfuse-docs", "langfuse-docs/deployment", etc.
- If the user asks about a specific product/project, apply the appropriate source_filter.
- Examples:
  * "How to deploy Docling?" → use source_filter="docling"
  * "Langfuse API documentation" → use source_filter="langfuse-docs"
  * "Deployment in Langfuse" → use source_filter="langfuse-docs/deployment"

When requested information is unavailable in the knowledge base, explicitly acknowledge this limitation and provide helpful general advice.
Deliver responses that are comprehensive yet focused.
Request additional details when user queries lack clarity or specificity.
Upon discovering pertinent information, present it in a synthesized format and include proper source attribution.""",
    tools=[search_knowledge_base],
)
