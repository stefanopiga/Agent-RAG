# Architecture - docling-rag-agent

## Executive Summary

**docling-rag-agent** è un sistema RAG (Retrieval Augmented Generation) production-ready che fornisce accesso conversazionale a knowledge base documentali tramite Streamlit UI e MCP Server. L'architettura è basata su **Service-Oriented Architecture (SOA)** con core business logic decoupled, LangFuse observability integrata, e MCP server standalone. Il sistema è progettato per prevenire conflitti tra agenti AI attraverso decisioni architetturali esplicite e pattern di implementazione rigorosi.

## Decision Summary

| Category                      | Decision                                             | Version                     | Verified   | Affects Epics  | Rationale                                                                          |
| ----------------------------- | ---------------------------------------------------- | --------------------------- | ---------- | -------------- | ---------------------------------------------------------------------------------- |
| **Observability Integration** | LangFuse decorator-based (`@observe()`)              | LangFuse Python SDK v3.0.0+ | 2025-11-26 | Epic 2, Epic 3 | Trace gerarchici automatici, cost tracking integrato, graceful degradation         |
| **Cost Tracking**             | LangFuse auto-tracking con `langfuse.openai` wrapper | OpenAI SDK 2.8.1+           | 2025-11-26 | Epic 2, Epic 3 | Zero codice aggiuntivo, pricing sempre aggiornato, breakdown automatico            |
| **MCP Server Architecture**   | Modulo `mcp/` con tools separati per dominio         | FastMCP 0.4.x+              | 2025-11-26 | Epic 2         | Standalone, direct service integration, pattern FastMCP nativi                     |
| **Error Handling**            | FastMCP `ToolError` Pattern                          | FastMCP 0.4.x+              | 2025-11-26 | Epic 2, Epic 4 | Messaggi informativi, logging strutturato, `mask_error_details=True` in produzione |
| **Logging Pattern**           | JSON Structured Logging                              | python-json-logger 4.0.0+   | 2025-11-26 | Epic 2, Epic 4 | Facile parsing, integrazione monitoring, ricerca efficiente                        |
| **API Response Format**       | Direct Pydantic Models                               | Pydantic 2.x                | 2025-11-26 | Epic 4         | Type-safe, semplice, già implementato                                              |
| **Testing Infrastructure**    | TDD Structure Rigorosa                               | pytest 8.x+                 | 2025-11-26 | Epic 5         | Coverage >70% enforcement, RAGAS evaluation, Playwright E2E                        |
| **Project Structure**         | Mapping epics → directories con convenzioni          | -                           | -          | Epic 6         | Organizzazione per responsabilità, zero file sparsi                                |
| **Date/Time Handling**        | ISO 8601 strings, UTC storage                        | datetime standard           | -          | All Epics      | Standard internazionale, parsing facile                                            |
| **Retry Pattern**             | Exponential backoff, max 3 tentativi                 | tenacity 9.1.2+             | 2025-11-26 | Epic 2, Epic 4 | Resilienza per transient errors                                                    |
| **Git Workflow**              | Git Flow semplificato + Conventional Commits         | -                           | -          | Epic 4         | Branch protection, commit standardization                                          |
| **CI/CD Pipeline**            | GitHub Actions: lint, type-check, test, secret scan  | GitHub Actions              | -          | Epic 4         | Quality gates automatici, security scanning                                        |
| **Secret Scanning**           | TruffleHog OSS su ogni PR                            | TruffleHog OSS              | -          | Epic 4         | Prevenzione leak secrets, fail build se rilevati                                   |
| **Code Review**               | CodeRabbit AI su ogni PR                             | CodeRabbit                  | -          | Epic 4         | Code quality, best practices, security                                             |
| **Versionamento**             | Semantic Versioning + CHANGELOG.md                   | SemVer                      | -          | Epic 4         | Standard industry, tracciabilità                                                   |

## Project Structure

```
docling-rag-agent/
├── docling_mcp/                      # Epic 2: MCP Server (standalone)
│   ├── __init__.py                   # Module exports
│   ├── server.py                     # FastMCP instance + tool definitions
│   ├── lifespan.py                   # Server lifecycle (DB init, embedder init)
│   ├── metrics.py                    # Prometheus metrics definitions (Story 2.3)
│   ├── health.py                     # Health check logic (Story 2.3)
│   ├── http_server.py                # FastAPI /metrics and /health endpoints (Story 2.3)
│   └── tools/                        # Tool modules (for reference/documentation)
│       ├── __init__.py
│       ├── search.py                 # query_knowledge_base, ask_knowledge_base
│       ├── documents.py              # list_knowledge_base_documents, get_knowledge_base_document
│       └── overview.py               # get_knowledge_base_overview
│   # Note: Directory named docling_mcp/ to avoid conflict with FastMCP's mcp package
│
├── core/                             # Epic 2: RAG Business Logic
│   ├── __init__.py
│   ├── agent.py                      # PydanticAI agent wrapper (Streamlit)
│   └── rag_service.py                # Pure RAG logic (decoupled)
│
├── ingestion/                        # Epic 1: Document Processing
│   ├── __init__.py
│   ├── ingest.py                     # DocumentIngestionPipeline
│   ├── chunker.py                    # HybridChunker, SimpleChunker
│   └── embedder.py                   # EmbeddingGenerator (OpenAI)
│
├── utils/                            # Shared Utilities
│   ├── __init__.py
│   ├── db_utils.py                   # AsyncPG connection pooling
│   ├── models.py                     # Pydantic data models
│   ├── providers.py                  # OpenAI provider config
│   ├── session_manager.py            # Epic 3: Session tracking and persistence
│   ├── langfuse_streamlit.py        # Epic 3: LangFuse context injection for Streamlit
│   ├── cost_monitor.py               # Epic 3: Cost monitoring and enforcement (optional, security)
│   ├── rate_limiter.py               # Epic 3: Rate limiting (optional, security)
│   └── streamlit_auth.py            # Epic 3: Simple authentication (optional, security)
│
├── api/                              # Epic 4: FastAPI Service (optional)
│   ├── __init__.py
│   ├── main.py                       # FastAPI app + endpoints
│   └── models.py                     # API request/response models
│
├── tests/                            # Epic 5: Testing Infrastructure
│   ├── __init__.py
│   ├── conftest.py                   # Shared fixtures
│   ├── unit/                         # Unit tests (>70% coverage)
│   │   ├── test_rag_service.py
│   │   ├── test_embedder.py
│   │   └── test_chunker.py
│   ├── integration/                 # Integration tests
│   │   ├── test_mcp_server.py
│   │   └── test_api_endpoints.py
│   ├── e2e/                         # E2E tests (Playwright)
│   │   └── test_streamlit_workflow.py
│   └── fixtures/                    # Test fixtures + golden dataset
│       └── golden_dataset.json      # 20+ query-answer pairs (RAGAS)
│
├── scripts/                          # Epic 4: Utility Scripts
│   ├── verification/                 # Verification scripts
│   │   ├── verify_api_endpoints.py
│   │   ├── verify_mcp_setup.py
│   │   └── verify_client_integration.py
│   └── debug/                        # Debug utilities
│       └── debug_mcp_tools.py
│
├── docs/                            # Epic 1: Documentation
│   ├── index.md
│   ├── architecture.md              # This file
│   ├── prd.md
│   ├── epics.md
│   ├── development-guide.md
│   └── ...
│
├── sql/                             # Database Schema
│   ├── schema.sql                   # PostgreSQL + PGVector schema
│   ├── optimize_index.sql
│   └── removeDocuments.sql
│
├── .github/                         # Epic 4: CI/CD Workflows
│   └── workflows/
│       ├── ci.yml                   # Lint, type-check, test, build
│       └── release.yml              # Release automation
│
├── app.py                           # Epic 3: Streamlit UI entry point
├── pyproject.toml                   # Project configuration (UV)
├── uv.lock                          # Dependency lock file
├── docker-compose.yml               # Docker orchestration
├── Dockerfile                       # Streamlit container
├── Dockerfile.api                   # API container (optional)
├── .env.example                     # Environment variables template
├── coderabbit.yaml                  # CodeRabbit configuration
├── CHANGELOG.md                     # Semantic versioning changelog
├── .gitignore
└── README.md                        # Project documentation
```

## Epic to Architecture Mapping

| Epic                                  | Stories | Directory/Component                                                                                                                                                               | Responsibility                                           |
| ------------------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| **Epic 1: Core RAG Baseline**         | 1.1-1.4 | `docs/`, `ingestion/`                                                                                                                                                             | Documentation + ingestion pipeline                       |
| **Epic 2: MCP Observability**         | 2.1-2.5 | `mcp/`, `core/rag_service.py`                                                                                                                                                     | LangFuse integration + MCP standalone                    |
| **Epic 3: Streamlit Observability**   | 3.1-3.2 | `app.py`, `utils/session_manager.py`, `utils/langfuse_streamlit.py`, `utils/cost_monitor.py` (optional), `utils/rate_limiter.py` (optional), `utils/streamlit_auth.py` (optional) | Session tracking + LangFuse tracing + Security hardening |
| **Epic 4: Production Infrastructure** | 4.1-4.3 | `api/`, `scripts/`, `.github/workflows/`                                                                                                                                          | CI/CD, health checks, Docker optimization                |
| **Epic 5: Testing & QA**              | 5.1-5.4 | `tests/`                                                                                                                                                                          | TDD infrastructure, unit/integration/E2E tests           |
| **Epic 6: Project Structure**         | 6.1-6.2 | All directories                                                                                                                                                                   | Cleanup + validation                                     |

## Technology Stack Details

### Core Technologies

| Component               | Technology         | Version | Verified   | Purpose               | Notes                                                                     |
| ----------------------- | ------------------ | ------- | ---------- | --------------------- | ------------------------------------------------------------------------- |
| **Language**            | Python             | 3.11    | 2025-11-26 | Runtime               | Requires >=3.10                                                           |
| **Package Manager**     | UV                 | 0.9.13+ | 2025-11-26 | Dependency Management | Fast, reliable                                                            |
| **Vector Database**     | PostgreSQL         | 16+     | 2025-11-26 | Storage               | With PGVector extension                                                   |
| **Vector Extension**    | PGVector           | 0.8.0+  | 2025-11-26 | Vector Search         | HNSW index for performance                                                |
| **LLM Provider**        | OpenAI             | 2.8.1+  | 2025-11-26 | Generation            | GPT-4o-mini                                                               |
| **Embeddings**          | OpenAI             | 2.8.1+  | 2025-11-26 | Vectors               | text-embedding-3-small (1536 dims)                                        |
| **UI Framework**        | Streamlit          | 1.31+   | 2025-11-26 | Web Interface         | Chat interface                                                            |
| **MCP Framework**       | FastMCP            | 0.4.x+  | 2025-11-26 | MCP Server            | Standalone server. Breaking changes: lifespan pattern, ToolError handling |
| **API Framework**       | FastAPI            | 0.109+  | 2025-11-26 | API Service           | Optional, for scaling                                                     |
| **Agent Framework**     | PydanticAI         | 0.7.4+  | 2025-11-26 | LLM Agent             | Streamlit integration                                                     |
| **Document Processing** | Docling            | 2.55+   | 2025-11-26 | Multi-format          | PDF, DOCX, PPTX, XLSX, HTML, MD, TXT                                      |
| **Observability**       | LangFuse           | 3.0.0+  | 2025-11-26 | Tracing & Monitoring  | Python SDK v3 (OTel-based)                                                |
| **Testing Framework**   | pytest             | 8.x+    | 2025-11-26 | Testing               | With pytest-asyncio, pytest-cov                                           |
| **E2E Testing**         | Playwright         | 1.40.0+ | 2025-11-26 | E2E Tests             | Streamlit workflow testing                                                |
| **RAG Evaluation**      | RAGAS              | 0.1.0+  | 2025-11-26 | Quality Metrics       | Faithfulness, relevancy scores                                            |
| **Logging**             | python-json-logger | 4.0.0+  | 2025-11-26 | Structured Logging    | JSON format for production                                                |
| **Retry Logic**         | tenacity           | 9.1.2+  | 2025-11-26 | Resilience            | Exponential backoff                                                       |

**Note on Version Verification:** All versions listed above were verified via WebSearch on 2025-11-26. Version numbers use minimum version format (e.g., "0.4.x+") to allow flexibility while ensuring compatibility. Breaking changes are documented in ADRs where relevant (e.g., FastMCP 0.4.x+ breaking changes documented in ADR-002). Versions should be re-verified periodically, especially before major releases or when upgrading dependencies.

### Integration Points

**1. MCP Server → Core RAG Service** (Pattern: Direct Service Integration)

- **Pattern Name**: Direct Service Integration Pattern
- **Implementation**: Direct import `from core.rag_service import search_knowledge_base_structured`
- **Communication**: Function calls (no HTTP overhead)
- **Lifecycle**: FastMCP lifespan initializes DB pool + embedder at startup
- **Error Handling**: `ToolError` for user-facing errors, exception wrapping for unexpected errors
- **Implementation Guide**:

  ```python
  # mcp/server.py
  from fastmcp import FastMCP
  from core.rag_service import search_knowledge_base_structured

  mcp = FastMCP("docling-rag-agent")

  @mcp.tool
  async def query_knowledge_base(query: str, limit: int = 5):
      # Direct function call, no HTTP overhead
      return await search_knowledge_base_structured(query, limit)
  ```

**2. Streamlit → Core Agent** (Pattern: Agent Wrapper Integration)

- **Pattern Name**: Agent Wrapper Integration Pattern
- **Implementation**: `from core.agent import RAGAgent`
- **Communication**: PydanticAI agent wrapper
- **Lifecycle**: Streamlit session manages agent instance
- **Session Tracking**: `st.session_state` for session_id, LangFuse context injection

**3. Core RAG Service → Utils** (Pattern: Shared Resource Pattern)

- **Pattern Name**: Shared Resource Pattern
- **Implementation**: `from utils.db_utils import db_pool`, `from utils.providers import get_provider_config`
- **Communication**: Shared connection pool + config
- **Lifecycle**: Global singleton pattern for embedder, connection pool per process

**4. Ingestion → Database** (Pattern: Direct Database Access)

- **Pattern Name**: Direct Database Access Pattern
- **Implementation**: Direct DB connection via `utils.db_utils`
- **Communication**: AsyncPG connection pool
- **Lifecycle**: Per-ingestion connection, cleanup on completion

**5. LangFuse Integration** (Pattern: Decorator-Based Observability)

- **Pattern Name**: Decorator-Based Observability Pattern
- **Implementation**: `@observe()` decorator on critical functions
- **Communication**: LangFuse SDK v3 (async HTTP, OpenTelemetry-based)
- **Lifecycle**: Initialized at startup via env vars, graceful degradation if unavailable
- **Cost Tracking**: Automatic via `langfuse.openai` wrapper (Story 2.2)
  - Embedding cost: Tracked via `langfuse.openai.AsyncOpenAI` in `ingestion/embedder.py`
  - LLM cost: Tracked via `langfuse.openai.chat.completions.create()` (future LLM integration)
  - Nested spans: `embedding-generation` span in `docling_mcp/server.py` for cost breakdown visibility
- **Implementation Guide**:

  ```python
  # core/rag_service.py
  from langfuse import observe, get_client

  langfuse = get_client()

  @observe(name="search_knowledge_base")
  async def search_knowledge_base_structured(query: str, limit: int = 5):
      """
      LangFuse automatically captures:
      - Function inputs/outputs
      - Execution time
      - Errors (if any)
      - Nested spans for child operations
      """
      # Embedding generation (nested span)
      with langfuse.start_as_current_observation(
          as_type="span", name="embedding-generation"
      ) as embedding_span:
          embedding = await generate_embedding(query)
          embedding_span.update(output={"embedding_dim": len(embedding)})

      # DB search (nested span)
      with langfuse.start_as_current_observation(
          as_type="span", name="vector-search"
      ) as search_span:
          results = await search_vector_db(embedding, limit)
          search_span.update(output={"results_count": len(results)})

      return results

  # For LLM calls, use generation type:
  @observe(name="llm-generation", as_type="generation")
  async def generate_response(context: str, query: str):
      from langfuse.openai import openai

      response = await openai.chat.completions.create(
          model="gpt-4o-mini",
          messages=[
              {"role": "system", "content": f"Context: {context}"},
              {"role": "user", "content": query}
          ]
      )
      # Cost tracking automatic via langfuse.openai wrapper
      return response.choices[0].message.content
  ```

  **Key Points**:

  - Use `@observe()` for automatic tracing of function calls
  - Use `langfuse.start_as_current_observation()` for nested spans
  - Use `as_type="generation"` for LLM calls to enable cost tracking
  - Use `langfuse.openai` wrapper instead of direct `openai` import for automatic cost tracking
  - Trace attributes (user_id, session_id) can be set via `propagate_attributes()` context manager

**6b. LangFuse Streamlit Context Injection** (Pattern: Context Manager Integration - Story 3.2)

- **Pattern Name**: Streamlit Context Injection Pattern
- **Implementation**: `utils/langfuse_streamlit.py` module with `with_streamlit_context()` context manager
- **Communication**: LangFuse SDK v3 context propagation via `propagate_attributes()`
- **Purpose**: Create root trace for Streamlit queries with session_id propagation to all nested spans
- **Implementation Guide**:

  ```python
  # utils/langfuse_streamlit.py
  from langfuse import get_client, propagate_attributes
  from contextlib import contextmanager
  from uuid import UUID

  @contextmanager
  def with_streamlit_context(session_id: UUID, query: str):
      """
      Context manager for LangFuse tracing in Streamlit.
      Creates root span 'streamlit_query' with session_id propagation.
      Implements graceful degradation if LangFuse unavailable.
      """
      langfuse = get_client()

      with langfuse.start_as_current_observation(
          as_type="span",
          name="streamlit_query",
          input={"query": query}
      ) as root_span:
          with propagate_attributes(
              session_id=str(session_id),
              metadata={"source": "streamlit", "query_text": query}
          ):
              ctx = StreamlitTraceContext(trace_id=root_span.trace_id)
              yield ctx

  # Usage in app.py
  from utils.langfuse_streamlit import with_streamlit_context

  with with_streamlit_context(session_id, query) as ctx:
      response = await run_agent(query)
      # Nested spans (embedding, DB, LLM) automatically inherit session_id
      trace_id = ctx.trace_id  # For cost extraction
  ```

  **Key Points**:

  - Root span named `streamlit_query` separates Streamlit traces from MCP traces
  - `metadata={"source": "streamlit"}` enables dashboard filtering by source
  - `session_id` propagated to all child observations via `propagate_attributes()`
  - Graceful degradation: if LangFuse unavailable, continues without tracing
  - Trace ID returned for post-execution cost extraction via `extract_cost_from_langfuse()`

**6. Prometheus Metrics Integration** (Pattern: Metrics Instrumentation)

- **Pattern Name**: Metrics Instrumentation Pattern
- **Implementation**: `prometheus_client` library with Counter, Histogram, Gauge types
- **Communication**: HTTP `/metrics` endpoint in Prometheus format
- **Lifecycle**: Metrics initialized lazily on first use, graceful degradation if unavailable
- **Components**:
  - `docling_mcp/metrics.py`: Metric definitions and recording functions
  - `docling_mcp/health.py`: Health check logic for database, langfuse, embedder
  - `docling_mcp/http_server.py`: FastAPI server for `/metrics` and `/health` endpoints
- **Implementation Guide**:

  ```python
  # docling_mcp/server.py - Instrument MCP tools
  from docling_mcp.metrics import record_request_start, record_request_end

  @mcp.tool()
  @observe(name="query_knowledge_base")
  async def query_knowledge_base(query: str, limit: int = 5):
      tool_name = "query_knowledge_base"
      request_start = record_request_start(tool_name)
      status = "success"

      try:
          # ... tool logic ...
          return results
      except Exception as e:
          status = "error"
          raise
      finally:
          record_request_end(tool_name, request_start, status)
  ```

  **Metrics Exposed**:

  | Metric                            | Type      | Labels            | SLO Alignment          |
  | --------------------------------- | --------- | ----------------- | ---------------------- |
  | `mcp_requests_total`              | Counter   | tool_name, status | Request tracking       |
  | `mcp_request_duration_seconds`    | Histogram | tool_name         | <2s p95                |
  | `rag_embedding_time_seconds`      | Histogram | -                 | <500ms                 |
  | `rag_db_search_time_seconds`      | Histogram | -                 | <100ms                 |
  | `rag_llm_generation_time_seconds` | Histogram | -                 | <1.5s                  |
  | `mcp_active_requests`             | Gauge     | -                 | Concurrency monitoring |

## Implementation Patterns

These patterns ensure consistent implementation across all AI agents:

### Naming Patterns

**File Naming:**

- Python files: `snake_case.py` (es. `rag_service.py`, `mcp_server.py`)
- Directories: `snake_case/` (es. `mcp/`, `core/`, `ingestion/`)
- Test files: `test_*.py` o `*_test.py` (es. `test_rag_service.py`)

**Code Naming:**

- Classes: `PascalCase` (es. `RAGService`, `EmbeddingGenerator`)
- Functions: `snake_case` (es. `query_knowledge_base`, `search_knowledge_base_structured`)
- Constants: `UPPER_SNAKE_CASE` (es. `MAX_RETRIES`, `DEFAULT_LIMIT`)
- Variables: `snake_case` (es. `query_embedding`, `search_results`)

**API Endpoints:**

- REST routes: Plural nouns, lowercase (es. `/v1/documents`, `/v1/search`)
- Route parameters: `{document_id}` format
- Query parameters: `snake_case` (es. `source_filter`, `limit`)

**Database:**

- Tables: `snake_case`, plural (es. `documents`, `chunks`)
- Columns: `snake_case` (es. `document_id`, `chunk_content`)
- Indexes: `idx_<table>_<column>_<type>` (es. `idx_chunks_embedding_hnsw`)

### Structure Patterns

**Test Organization:**

- Unit tests: `tests/unit/` - Isolated, fast, mocked dependencies
- Integration tests: `tests/integration/` - With mocked DB/API, no real external services
- E2E tests: `tests/e2e/` - Full system tests with Playwright
- Fixtures: `tests/fixtures/` - Shared test data, golden dataset for RAGAS

**Component Organization:**

- By responsibility: `mcp/` (MCP server), `core/` (business logic), `ingestion/` (processing)
- Shared utilities: `utils/` (DB, models, providers)
- Entry points: Root level (`app.py` for Streamlit, `mcp/server.py` for MCP)

**Script Organization:**

- Verification: `scripts/verification/` - Setup/health check scripts
- Debug: `scripts/debug/` - Debug utilities
- Performance: `scripts/` or `tests/performance/` - Performance testing

### Format Patterns

**API Responses:**

- Format: Direct Pydantic models (no wrapper)
- Success: Pydantic model instance (es. `SearchResponse`, `IngestResponse`)
- Errors: `HTTPException` with status codes (400, 404, 500)
- Date format: ISO 8601 strings (`2025-11-26T10:30:00Z`)

**Error Format:**

- MCP: `ToolError("User-friendly message")` for handled errors
- API: `HTTPException(status_code=500, detail="Error message")`
- Logging: JSON structured with `{"error": str, "context": dict, "stack_trace": str}`

**Date/Time:**

- Storage: UTC, ISO 8601 format (`2025-11-26T10:30:00Z`)
- Display: Locale-aware formatting in UI
- Library: Standard `datetime` (no additional dependencies)

### Communication Patterns

**MCP Tools:**

- Tool naming: `verb_noun` pattern (es. `query_knowledge_base`, `list_knowledge_base_documents`)
- Parameters: `snake_case`, descriptive names
- Return: String (formatted) or structured dict for complex data

**API Endpoints:**

- RESTful: Resource-based URLs (`/v1/documents`, `/v1/documents/{id}`)
- Methods: GET (read), POST (create/search), PUT/PATCH (update), DELETE (delete)
- Status codes: 200 (success), 400 (bad request), 404 (not found), 500 (server error)

**LangFuse Tracing:**

- Decorator: `@observe()` on critical functions
- Context: Session ID, metadata via LangFuse context injection
- Spans: Hierarchical (query → embedding → retrieval → generation)

### Lifecycle Patterns

**Loading States:**

- Pattern: Async initialization with `asyncio.Event` for readiness
- Example: Global embedder initialization with `_embedder_ready` event
- Error handling: Timeout after 60s, clear error messages

**Error Recovery:**

- Pattern: Exponential backoff with `tenacity` (max 3 retries)
- Applicable to: OpenAI API calls, DB connections
- Non-retryable: HTTP 4xx errors, validation errors

**Retry Logic:**

- Pattern: `@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))`
- Scope: Transient errors only (timeout, network errors)
- Logging: Retry attempts logged with attempt number

**Session Management:**

- Streamlit: `st.session_state` for session_id persistence
- MCP: Session ID from LangFuse context injection
- Storage: PostgreSQL or in-memory (per session)

### Location Patterns

**API Route Structure:**

- Base: `/v1/` prefix for versioning
- Resources: `/v1/documents`, `/v1/search`, `/v1/ingest`
- Health: `/health` (no version prefix)

**Static Assets:**

- Documentation: `docs/` directory
- SQL scripts: `sql/` directory
- Config files: Root level (`.env.example`, `pyproject.toml`)

**Config File Locations:**

- Environment: `.env` (gitignored), `.env.example` (template)
- Project config: `pyproject.toml` (UV/Python)
- Docker: `docker-compose.yml`, `Dockerfile`
- CI/CD: `.github/workflows/`

### Consistency Patterns

**Date Formatting:**

- UI: Locale-aware, human-readable (es. "26 Nov 2025, 10:30")
- API: ISO 8601 strings
- Logs: ISO 8601 strings for parsing

**Logging Format:**

- Production: JSON structured (`{"timestamp": "...", "level": "INFO", "module": "...", "message": "...", "context": {...}}`)
- Development: Text format (readable)
- Levels: DEBUG (dev), INFO (production), WARNING, ERROR, CRITICAL

**User-Facing Errors:**

- Format: Clear, actionable messages (no stack traces)
- Context: What went wrong, what user can do
- Example: "RAG API Service is unavailable. Please check if the service is running."

## Consistency Rules

### Naming Conventions

- **Files**: `snake_case.py`
- **Directories**: `snake_case/`
- **Classes**: `PascalCase`
- **Functions**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **API endpoints**: Plural nouns, lowercase
- **Database tables**: Plural, `snake_case`

### Code Organization

- **By responsibility**: `mcp/`, `core/`, `ingestion/`, `utils/`, `api/`
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/e2e/`
- **Scripts**: `scripts/verification/`, `scripts/debug/`
- **Documentation**: `docs/` (centralized)

### Error Handling

- **MCP**: `ToolError` for handled errors, exception wrapping for unexpected
- **API**: `HTTPException` with appropriate status codes
- **Logging**: JSON structured with full context
- **User messages**: Clear, actionable, no technical jargon

### Logging Strategy

- **Format**: JSON structured (production), text (development)
- **Levels**: DEBUG (dev), INFO (production), WARNING, ERROR, CRITICAL
- **Destination**: stdout (Docker-friendly)
- **Context**: Include request_id, session_id, user_id when available

## Data Architecture

### Database Schema

**Tables:**

- `documents`: Document metadata (id, title, source, created_at, updated_at)
- `chunks`: Document chunks with embeddings (id, document_id, content, embedding, metadata)
- `sessions`: Streamlit session tracking (Epic 3) - session_id, query_count, total_cost, total_latency_ms
- `query_logs`: Query logging per sessione (Epic 3) - session_id, query_text, cost, latency_ms, langfuse_trace_id

**Indexes:**

- `idx_chunks_embedding_hnsw`: HNSW index for vector similarity search (m=16, ef_construction=64)
- `idx_documents_source`: B-tree index for source filtering
- `idx_chunks_document_id`: B-tree index for document-chunk relationships
- `idx_query_logs_session_id`: B-tree index for session query lookups (Epic 3)
- `idx_query_logs_timestamp`: B-tree index for time-based queries (Epic 3)
- `idx_sessions_last_activity`: B-tree index for session activity tracking (Epic 3)

**Row Level Security (RLS):**

- All tables in `public` schema have RLS enabled
- `sessions` and `query_logs`: Policies restrict access to `service_role` only (backend access)
- `documents` and `chunks`: RLS enabled, no policies (protected by default, backend access only)

**Connection Pool:**

- `min_size`: 2 (reduced idle overhead)
- `max_size`: 10 (right-sized for MCP workload)
- `statement_cache_size`: 100 (prepared statements)
- `max_queries`: 50000 (connection recycling)

### Data Models

**Pydantic Models (`utils/models.py`):**

- `Document`: Document metadata
- `Chunk`: Chunk with embedding
- `Session`: Session model (generic, Epic 3 uses custom SessionStats model)
- Request/Response models in `api/models.py`

**Epic 3 Models (to be added to `utils/models.py`):**

- `SessionStats`: Session statistics (session_id, query_count, total_cost, avg_latency_ms)
- `QueryLog`: Query log entry (session_id, query_text, cost, latency_ms, langfuse_trace_id)

**API Models (`api/models.py`):**

- `SearchRequest`: Query, limit, source_filter
- `SearchResponse`: Results list, count, processing_time_ms
- `SearchResult`: Content, similarity, source, title, metadata
- `IngestRequest`: Documents folder, clean flag, fast mode
- `IngestResponse`: Status, message, task_id

## API Contracts

### Search Endpoint

**POST `/v1/search`**

- **Request**: `SearchRequest` (query: str, limit: int, source_filter: Optional[str])
- **Response**: `SearchResponse` (results: List[SearchResult], count: int, processing_time_ms: float)
- **Errors**: 400 (bad request), 500 (server error)
- **Timing**: Breakdown in response (embedding_ms, db_ms, total_ms)

### Documents Endpoint

**GET `/v1/documents`**

- **Query Params**: `limit` (default: 100), `offset` (default: 0)
- **Response**: `{"documents": [...], "count": int}`
- **Errors**: 500 (server error)

**GET `/v1/documents/{document_id}`**

- **Path Params**: `document_id` (UUID)
- **Response**: Document object with full content
- **Errors**: 404 (not found), 500 (server error)

### Overview Endpoint

**GET `/v1/overview`**

- **Response**: `{"total_documents": int, "total_chunks": int, "unique_sources": int, "sources": [...], "documents": [...]}`
- **Errors**: 500 (server error)

### Health Check

**GET `/health`**

- **Response**: `{"status": "ok", "timestamp": float}`
- **Purpose**: Service availability check

## Security Architecture

### Authentication & Authorization

- **Pattern**: No user authentication (RAG system, no user management)
- **API Keys**: Environment variables (`OPENAI_API_KEY`, `LANGFUSE_SECRET_KEY`)
- **Protection**: Keys never logged, never committed to git
- **Validation**: Secret scanning in CI/CD (TruffleHog)

### Data Protection

- **Encryption**: PostgreSQL connection string encrypted in production
- **Secrets Management**: Environment variables, `.env` file (gitignored)
- **Logging**: No secrets in logs, masking enabled for sensitive data

### Security Best Practices

- **Secret Scanning**: TruffleHog OSS on every PR
- **Dependency Scanning**: Regular dependency updates, security advisories
- **Input Validation**: Pydantic models for all API inputs
- **Error Messages**: No sensitive information in user-facing errors

## Performance Considerations

### Latency Targets (from NFRs)

- **MCP Query**: < 2s (95th percentile)
- **Embedding Generation**: < 500ms per batch (100 chunks)
- **DB Vector Search**: < 100ms per query (with HNSW index)
- **Throughput**: 50 queries/second with <10% degradation

### Optimization Strategies

**Global Embedder:**

- Singleton pattern, initialized once at startup
- Persistent cache (2000 entries) across requests
- Eliminates 300-500ms overhead per query

**Database:**

- HNSW index for vector similarity (10-100x faster than IVFFlat)
- Connection pooling (2-10 connections, right-sized)
- Prepared statements caching (100 statements)

**Caching:**

- Embedding cache: LRU cache, 2000 entries
- Query results: Not cached (always fresh, semantic search)

### Scalability

- **Horizontal Scaling**: Supported via load balancer (future)
- **Connection Pool**: Dynamic (2-10 connections)
- **Database**: PostgreSQL with PGVector (scales with hardware)

## Deployment Architecture

### Docker Configuration

**Streamlit Container (`Dockerfile`):**

- Base: `python:3.11-slim-bookworm`
- UV: Copied from official image
- Multi-stage: Dependency installation → code copy → final image
- Size: < 500MB target
- Health check: `/_stcore/health` endpoint

**API Container (`Dockerfile.api`):**

- Base: `python:3.11-slim-bookworm`
- FastAPI + Uvicorn
- Health check: `/health` endpoint

**Docker Compose:**

- Services: Streamlit app, PostgreSQL (optional), LangFuse (optional)
- Networks: Internal network for service communication
- Volumes: Document storage, database persistence

### Environment Configuration

**Required Variables:**

- `OPENAI_API_KEY`: OpenAI API key
- `DATABASE_URL`: PostgreSQL connection string
- `LANGFUSE_PUBLIC_KEY`: LangFuse public key (optional)
- `LANGFUSE_SECRET_KEY`: LangFuse secret key (optional)
- `LANGFUSE_BASE_URL`: LangFuse server URL (optional, defaults to cloud)

**Optional Variables:**

- `LLM_CHOICE`: LLM model (default: `gpt-4o-mini`)
- `EMBEDDING_MODEL`: Embedding model (default: `text-embedding-3-small`)
- `DEBUG_MODE`: Enable debug logging (default: `false`)

**Epic 3 Security Hardening (Optional):**

- `COST_DAILY_LIMIT`: Daily cost limit in USD (default: `10.00`)
- `COST_HOURLY_LIMIT`: Hourly cost limit in USD (default: `2.00`)
- `COST_ALERT_THRESHOLD`: Cost alert threshold in USD (default: `5.00`)
- `STREAMLIT_PASSWORD_HASH`: SHA256 hash for Streamlit authentication (optional)
- `REDIS_URL`: Redis connection URL for persistent rate limiting (optional, default: `redis://localhost:6379`)

### CI/CD Pipeline

**GitHub Actions Workflow (`.github/workflows/ci.yml`):**

Il CI/CD pipeline completo è documentato in dettaglio in:
- **Technical Specification**: `docs/stories/4/tech-spec-epic-4.md`
- **Setup Guide**: `docs/stories/4/epic-4-setup-guide.md`

**Pipeline Components:**

```yaml
name: CI

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  lint:
    - ruff check (zero warnings)
    - ruff format check
  type-check:
    - mypy (zero errors)
  test:
    - pytest with coverage >70%
    - Fail build if coverage <70%
    - Upload coverage report artifacts
  build:
    - Docker build test (Streamlit + API)
    - Verify image sizes <500MB
  secret-scan:
    - TruffleHog OSS scan (full git history)
    - Fail build if secrets detected
```

**Release Workflow (`.github/workflows/release.yml`):**

- Trigger: Git tag creation (`v*.*.*`)
- Actions: Update CHANGELOG, create GitHub Release
- **Reference**: `docs/stories/4/epic-4-setup-guide.md` (Step 6)

**Security Scanning:**

- **TruffleHog OSS**: Automatic secret scanning su ogni PR/push
- **CodeRabbit**: AI-powered code review automatica
- **References**: 
  - TruffleHog: https://github.com/marketplace/actions/trufflehog-oss
  - CodeRabbit: https://docs.coderabbit.ai/platforms/github-com

## Development Environment

### Prerequisites

- **Python**: 3.11+ (3.10+ minimum)
- **UV**: Latest version (package manager)
- **PostgreSQL**: 16+ with PGVector extension
- **Docker**: Latest (for containerized development)
- **Git**: Latest (for version control)

### Setup Commands

```bash
# Install dependencies
uv sync

# Setup environment
cp .env.example .env
# Edit .env with your API keys and database URL

# Initialize database
psql $DATABASE_URL < sql/optimize_index.sql

# Run Streamlit app
streamlit run app.py

# Run MCP server (for Cursor/Claude Desktop)
uv run python -m mcp.server

# Run tests
pytest --cov=core --cov=ingestion --cov=mcp --cov-report=html

# Run linting
ruff check .

# Run type checking
mypy .
```

### Git Workflow

**Branching Strategy:**

- `main`: Production-ready code
- `develop`: Integration branch
- `feature/*`: Feature development
- `hotfix/*`: Urgent production fixes

**Commit Conventions:**

- Format: `<type>(<scope>): <description>`
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
- Example: `feat(mcp): add LangFuse tracing to query_knowledge_base`

**Pull Request Process:**

1. Create feature branch from `develop`
2. Implement changes with tests
3. Ensure CI passes (lint, type-check, test, secret-scan)
4. CodeRabbit review (automatic)
5. Manual review (if needed)
6. Merge to `develop`, then `main`

### Versionamento

**Semantic Versioning:**

- Format: `MAJOR.MINOR.PATCH` (es. `0.1.0`)
- Current: `0.1.0` (in `pyproject.toml`)
- Changelog: `CHANGELOG.md` with Keep a Changelog format
- Tagging: Git tags `v0.1.0` for each release

**Release Process:**

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with changes
3. Create git tag: `git tag v0.1.0`
4. Push tag: `git push origin v0.1.0`
5. GitHub Actions creates release automatically
6. Set `LANGFUSE_RELEASE` env var with tag

## Architecture Decision Records (ADRs)

### ADR-001: LangFuse Integration Pattern

**Status**: Accepted  
**Date**: 2025-11-26  
**Verified**: 2025-11-26  
**Context**: Need observability for MCP server operations with cost tracking and performance metrics.

**Decision**: Use LangFuse decorator-based pattern (`@observe()`) with `langfuse.openai` wrapper for automatic cost tracking.

**Rationale**:

- Minimal code changes required
- Automatic hierarchical trace structure
- Cost tracking built-in with current OpenAI pricing
- Graceful degradation if LangFuse unavailable
- OpenTelemetry-based (v3) enables third-party library integration

**Implementation**:

```python
# Step 1: Initialize LangFuse client (once at startup)
from langfuse import get_client

langfuse = get_client()  # Uses env vars: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY

# Step 2: Decorate critical functions
from langfuse import observe

@observe(name="search_knowledge_base")
async def search_knowledge_base_structured(query: str, limit: int = 5):
    # Automatic tracing: inputs, outputs, timing, errors
    pass

# Step 3: Use langfuse.openai wrapper for LLM calls
from langfuse.openai import openai

response = await openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": query}]
)
# Automatic cost tracking and token usage

# Step 4: Set trace attributes (user_id, session_id)
from langfuse import propagate_attributes

with propagate_attributes(user_id="user_123", session_id="session_abc"):
    # All child observations inherit these attributes
    result = await search_knowledge_base_structured(query)
```

**Consequences**:

- All critical functions must use `@observe()` decorator
- LangFuse SDK v3.0.0+ required (OTel-based)
- Environment variables needed: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (optional)
- Use `langfuse.openai` wrapper instead of direct `openai` import for cost tracking
- Trace attributes must be set via `propagate_attributes()` context manager (not directly on calls)

---

### ADR-002: MCP Server Standalone Architecture

**Status**: Accepted  
**Date**: 2025-11-26  
**Verified**: 2025-11-26  
**Context**: MCP server currently depends on external API server, causing reliability issues.

**Decision**: Refactor MCP server to use `core/rag_service.py` directly, eliminating HTTP dependency.

**Rationale**:

- Eliminates external dependency
- Reduces latency (no HTTP overhead)
- Simpler architecture, easier debugging
- Aligns with existing design (core logic decoupled)

**Implementation**:

```python
# mcp/server.py
from fastmcp import FastMCP
from contextlib import asynccontextmanager

mcp = FastMCP("docling-rag-agent")

@asynccontextmanager
async def lifespan(app: FastMCP):
    """FastMCP lifespan pattern for startup/shutdown."""
    # Startup: Initialize resources
    from utils.db_utils import init_db_pool
    from ingestion.embedder import init_embedder

    await init_db_pool()
    await init_embedder()

    yield  # Server runs here

    # Shutdown: Cleanup resources
    from utils.db_utils import close_db_pool
    await close_db_pool()

mcp.lifespan = lifespan

# Direct import from core (no HTTP)
from core.rag_service import search_knowledge_base_structured

@mcp.tool
async def query_knowledge_base(query: str, limit: int = 5):
    """Query knowledge base with direct function call."""
    try:
        return await search_knowledge_base_structured(query, limit)
    except Exception as e:
        from mcp.server import ToolError
        raise ToolError(f"Failed to query knowledge base: {str(e)}")
```

**Breaking Changes** (FastMCP 0.4.x+):

- FastMCP 0.4.x+ uses lifespan pattern instead of startup/shutdown hooks
- Tool error handling uses `ToolError` instead of generic exceptions
- Context injection via `Context` parameter (type-hinted) instead of global state

**Consequences**:

- MCP server must initialize DB pool and embedder at startup via lifespan
- Requires FastMCP lifespan management pattern (`@asynccontextmanager`)
- `client/api_client.py` no longer needed for MCP (kept for other use cases)
- Testing requires FastMCP Client with in-memory transport for unit tests

---

### ADR-003: TDD Structure Rigorosa

**Status**: Accepted  
**Date**: 2025-11-26  
**Context**: Need comprehensive testing infrastructure for production-ready system.

**Decision**: Implement TDD structure with `tests/unit/`, `tests/integration/`, `tests/e2e/`, coverage >70% enforcement.

**Rationale**:

- Prevents regressions
- Ensures code quality
- RAGAS evaluation for RAG quality
- Playwright E2E tests for user workflows

**Consequences**:

- All new code must have tests first (Red-Green-Refactor)
- CI/CD fails if coverage <70%
- Golden dataset required for RAGAS evaluation (20+ pairs)

---

### ADR-004: Git Workflow & CI/CD

**Status**: Accepted  
**Date**: 2025-11-26  
**Context**: Need automated quality gates and security scanning for production deployment.

**Decision**: Git Flow + Conventional Commits + GitHub Actions CI/CD + TruffleHog secret scanning + CodeRabbit code review.

**Rationale**:

- Automated quality checks prevent bad code from merging
- Secret scanning prevents credential leaks
- CodeRabbit provides AI-powered code review
- Semantic versioning enables release tracking

**Consequences**:

- All commits must follow Conventional Commits format
- PRs must pass CI/CD before merging
- Secrets detected in PRs cause build failure
- CodeRabbit reviews every PR automatically

---

### ADR-005: Prometheus Metrics and Health Check Endpoints

**Status**: Accepted  
**Date**: 2025-11-27  
**Context**: Need production-grade monitoring with standard Prometheus metrics and health check endpoints for Kubernetes/Docker orchestration.

**Decision**: Implement Prometheus metrics via `prometheus_client` library and JSON health check endpoint via FastAPI.

**Rationale**:

- Prometheus is industry standard for container monitoring
- Health check endpoints enable Kubernetes liveness/readiness probes
- Graceful degradation maintains service availability
- Histogram buckets aligned with SLO targets for meaningful alerting

**Implementation**:

```python
# docling_mcp/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request counter (labeled by tool and status)
mcp_requests_total = Counter(
    "mcp_requests_total",
    "Total MCP requests",
    ["tool_name", "status"]
)

# Request duration histogram (SLO: <2s p95)
mcp_request_duration_seconds = Histogram(
    "mcp_request_duration_seconds",
    "Request latency",
    ["tool_name"],
    buckets=[0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
)

# RAG-specific histograms
rag_embedding_time_seconds = Histogram(
    "rag_embedding_time_seconds",
    "Embedding generation time",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 1.0]  # SLO: <500ms
)

rag_db_search_time_seconds = Histogram(
    "rag_db_search_time_seconds",
    "Database search time",
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0]  # SLO: <100ms
)
```

```python
# docling_mcp/health.py
async def get_health_status() -> HealthResponse:
    """
    Status logic:
    - ok: All services UP
    - degraded: LangFuse DOWN (non-critical)
    - down: Database or Embedder DOWN (critical)
    """
    db_status = await check_database()
    langfuse_status = check_langfuse()
    embedder_status = await check_embedder()

    if db_status.status == "down" or embedder_status.status == "down":
        overall_status = "down"
    elif langfuse_status.status == "down":
        overall_status = "degraded"
    else:
        overall_status = "ok"

    return HealthResponse(status=overall_status, ...)
```

**Endpoints**:

| Endpoint   | Port | Content-Type                 | Purpose             |
| ---------- | ---- | ---------------------------- | ------------------- |
| `/metrics` | 8080 | application/openmetrics-text | Prometheus scraping |
| `/health`  | 8080 | application/json             | Kubernetes probes   |

**Prometheus Configuration** (recommended `scrape_interval`):

- **15s**: Default for real-time monitoring
- **60s**: Cost-sensitive deployments (reduced alert responsiveness)

**Consequences**:

- HTTP server (`docling_mcp/http_server.py`) runs on port 8080 (configurable via `METRICS_PORT`)
- Metrics recording wrapped in try/except for graceful degradation
- Health check status "degraded" returns HTTP 200 (service still functional)
- Health check status "down" returns HTTP 503 (service unavailable)

---

## References

### Related Documentation

- **[Coding Standards](./coding-standards.md)**: Complete code style guide, naming conventions, documentation standards, error handling patterns, and best practices based on existing codebase patterns.
- **[Testing Strategy](./testing-strategy.md)**: Comprehensive testing strategy with TDD workflow, test organization (unit/integration/e2e), RAGAS evaluation, and CI/CD integration.
- **[Unified Project Structure](./unified-project-structure.md)**: Standardized directory structure, file organization rules, epic-to-directory mapping, and validation checklist.
- **[Development Guide](./development-guide.md)**: Setup instructions, development workflow, database operations, and troubleshooting.
- **[Epics Breakdown](./epics.md)**: Complete epic and story breakdown with acceptance criteria and technical notes.
- **[PRD](./prd.md)**: Product Requirements Document with functional requirements inventory.

### External References

- **LangFuse Documentation**: https://langfuse.com/docs
- **FastMCP Documentation**: https://github.com/jlowin/fastmcp
- **PydanticAI Documentation**: https://ai.pydantic.dev
- **Prometheus Best Practices**: https://prometheus.io/docs/practices/histograms/
- **PostgreSQL PGVector**: https://github.com/pgvector/pgvector

---

_Generated by BMAD Decision Architecture Workflow v1.0_  
_Date: 2025-11-26_  
_Updated: 2025-11-27_  
_For: Stefano_
