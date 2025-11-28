# Analysis: Monolith Refactoring Opportunities

**Generated:** 2025-11-26
**Context:** Transitioning from Monolith to Modular Architecture

## 1. Current Architecture (Monolith)

The current `docling-rag-agent` is a **Modular Monolith**. While code is organized into folders (`core`, `ingestion`, `utils`), the components are tightly coupled by direct Python imports and shared runtime resources (memory, database connections).

### Coupling Analysis

| Component | Coupled With | Type of Coupling | Risk |
|-----------|--------------|------------------|------|
| **Streamlit App** (`app.py`) | `core.agent`, `utils.db_utils` | Direct Import, Shared Runtime | UI crashes if DB fails; Memory contention with Agent. |
| **MCP Server** (`mcp_server.py`) | `core.rag_service`, `utils.db_utils` | Direct Import, Shared Runtime | Server startup blocked by heavy model loading; Shared DB pool. |
| **Ingestion** (`ingestion/`) | `utils.db_utils`, `utils.models` | Shared Code, Shared DB | Ingestion load affects Query latency; Schema changes break all apps. |
| **Embeddings** | `core`, `ingestion` | Shared Logic (`embedder.py`) | Model changes require redeploying ALL services. |

### Critical Pain Points
1.  **Memory Contention:** Running Streamlit + MCP + Ingestion on one machine loads the embedding model multiple times (or strains shared memory).
2.  **Deployment Rigidity:** Cannot scale "Ingestion" separately from "Query" traffic.
3.  **Startup Latency:** MCP server takes ~40s to start because it loads ML models, causing timeouts.

## 2. Proposed Architecture (Service-Oriented)

To address the "Monolith Structure to Change" request, we propose splitting the system into **3 Distinct Services**.

### Service A: RAG API Service (The "Brain")
*   **Responsibility:** Semantic search, embedding generation, LLM interaction.
*   **Interface:** REST API (FastAPI) or gRPC.
*   **Components:** `core/rag_service.py`, `ingestion/embedder.py`.
*   **Scaling:** Scale based on query load (GPU/CPU heavy).

### Service B: Ingestion Worker (The "Muscle")
*   **Responsibility:** File scanning, Docling conversion, Chunking, Writing to DB.
*   **Interface:** Async Worker (triggered by file events or API call).
*   **Components:** `ingestion/ingest.py`, `ingestion/chunker.py`.
*   **Scaling:** Scale based on document volume (Memory/CPU heavy).

### Service C: Interface Layer (The "Face")
*   **Responsibility:** User interaction, formatting, protocol handling.
*   **Components:**
    *   **Streamlit UI:** Consumes RAG API. Lightweight.
    *   **MCP Server:** Consumes RAG API. Lightweight, fast startup.
*   **Scaling:** Scale based on concurrent users (Network I/O bound).

## 3. Refactoring Roadmap

### Phase 1: Decoupling (Current Status: ✅ Partial)
-   [x] Separate `rag_service.py` from `app.py` (Done).
-   [x] Separate `db_utils.py` for shared access (Done).
-   [ ] **Action:** Abstract `embedder.py` behind an interface so it can be swapped for an API call later.

### Phase 2: API Extraction (High Priority)
1.  Create `api/main.py` using FastAPI.
2.  Expose `POST /search` endpoint wrapping `rag_service.search_knowledge_base`.
3.  Expose `POST /ingest` endpoint wrapping `ingest.ingest_documents`.

### Phase 3: Client Refactoring
1.  Update `app.py` to call `http://rag-api/search` instead of `import core.agent`.
2.  Update `mcp_server.py` to call `http://rag-api/search`.
3.  *Result:* MCP server startup becomes instant (<1s).

### Phase 4: Containerization
1.  `Dockerfile.api` (RAG Service)
2.  `Dockerfile.ui` (Streamlit)
3.  `Dockerfile.mcp` (MCP Server)
4.  `docker-compose.yml` orchestrating them with a shared PostgreSQL container.

## 4. Immediate "Quick Wins"

If a full microservices rewrite is too much, implement these **Modular Monolith** improvements:

1.  **Lazy Loading:** Ensure `import ingestion.embedder` only happens inside functions, not at module level (already partially done in `rag_service`).
2.  **Async Workers:** Move ingestion to a background thread/process even within the monolith, communicating via a queue (e.g., `asyncio.Queue` or Redis).
3.  **Config Separation:** Use distinct `.env` sections or files for `INGESTION_` vs `APP_` config to clarify dependencies.
