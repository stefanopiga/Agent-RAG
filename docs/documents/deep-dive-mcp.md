# Deep-Dive: MCP Server

**Target:** `mcp_server.py`
**Generated:** 2025-11-26
**Scope:** `mcp_server.py`, `core/rag_service.py`

## Executive Summary

The MCP Server (`mcp_server.py`) exposes the RAG agent's capabilities via the **Model Context Protocol (MCP)**, allowing external tools like Cursor and Claude Desktop to interact with the knowledge base. It is built using `FastMCP` and follows a **Service-Oriented Architecture** by delegating core logic to `core.rag_service`. This design ensures that the MCP server is a lightweight interface layer, while business logic remains centralized and reusable.

## File Inventory

### 1. `mcp_server.py`
- **Purpose:** MCP Server entry point. Defines tools, resources, and prompts.
- **Key Components:**
    - `FastMCP` instance: "Docling RAG Agent".
    - `server_lifespan`: Async context manager for resource lifecycle (DB pool, Embedder).
    - `query_knowledge_base` (Tool): Semantic search tool.
    - `list_knowledge_base_documents` (Resource): Lists available docs.
- **Dependencies:** `fastmcp`, `core.rag_service`, `utils.db_utils`.

### 2. `core/rag_service.py`
- **Purpose:** Pure business logic for RAG operations. Decoupled from any UI (Streamlit) or Interface (MCP).
- **Key Components:**
    - `search_knowledge_base`: Main search function.
    - `initialize_global_embedder`: Background task for model loading.
    - `_global_embedder`: Singleton instance for performance.
- **Dependencies:** `ingestion.embedder`, `utils.db_utils`.

## Data Flow Analysis

1.  **Request:** MCP Client (e.g., Cursor) sends `call_tool("query_knowledge_base", { "query": "..." })`.
2.  **Interface Layer (`mcp_server.py`):**
    -   Receives request.
    -   Logs query.
    -   Calls `core.rag_service.search_knowledge_base()`.
3.  **Service Layer (`core/rag_service.py`):**
    -   Acquires `_global_embedder` (waits if initializing).
    -   Generates query embedding (cached if repeated).
    -   Executes SQL vector search via `utils.db_utils`.
    -   Formats results with source citations.
4.  **Response:** Returns formatted string to MCP Client.

## Integration Points

-   **MCP Protocol:** Implements standard MCP tools and resources.
-   **Database:** Shares the same PostgreSQL database as the Ingestion Pipeline and Streamlit App.
-   **Embeddings:** Uses the same `ingestion.embedder` logic as the ingestion pipeline, ensuring vector compatibility.

## Key Implementation Details & Patterns

-   **Global Embedder Pattern:** To solve the "cold start" problem of loading heavy ML models (300-500ms overhead per call), `rag_service.py` maintains a global singleton `_global_embedder`.
-   **Background Initialization:** The embedder loading is offloaded to a background task in `server_lifespan` to prevent blocking the MCP server startup handshake.
-   **Service Layer Decoupling:** The refactoring (mentioned in `walkthrough.md`) successfully moved logic out of `app.py` into `core/rag_service.py`, making `mcp_server.py` extremely thin (~150 LOC).

## Risks & Recommendations

-   **Shared Database:** The MCP server accesses the same DB as the ingestion pipeline. If ingestion is running (wiping DB), queries might fail or return empty results.
    *   *Recommendation:* Implement read-replicas or better locking strategies if high concurrency is expected.
-   **Memory Footprint:** The global embedder keeps the model in memory. Running Streamlit + MCP + Ingestion simultaneously might strain memory on smaller machines.
    *   *Recommendation:* Consider a shared "Embedding Service" (microservice) if memory becomes a bottleneck.
