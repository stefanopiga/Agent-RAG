# Epic Technical Specification: MCP Server Observability (LangFuse)

Date: 2025-11-26
Author: Stefano
Epic ID: 2
Status: Draft

---

## Overview

Epic 2 implementa monitoring completo per il MCP server usando LangFuse, fornendo observability nativa con cost tracking granulare e performance metrics real-time. Questo epic trasforma il MCP server da sistema senza visibilità a sistema production-ready con tracciamento completo di ogni operazione, calcolo accurato dei costi, e dashboard real-time per monitoring. L'implementazione segue il pattern decorator-based di LangFuse (`@observe()`) con integrazione automatica del cost tracking tramite `langfuse.openai` wrapper, garantendo zero overhead di codice aggiuntivo e pricing sempre aggiornato. Inoltre, questo epic include il refactoring dell'architettura MCP server per renderlo standalone, eliminando la dipendenza da API server esterno e migliorando affidabilità e facilità di deployment.

## Objectives and Scope

**In-Scope:**

- Integrazione LangFuse SDK nel MCP server con decorator pattern `@observe()`
- Cost tracking automatico per ogni query MCP (embedding tokens + LLM tokens)
- Performance metrics con breakdown timing (embedding_time, db_search_time, llm_generation_time)
- Endpoint `/metrics` in formato Prometheus per real-time monitoring
- Dashboard LangFuse configurata con metriche chiave (queries, latency, cost)
- Refactoring MCP server architecture: standalone senza dipendenza API esterna
- Organizzazione modulo `mcp/` con tools separati per dominio (search, documents, overview)
- Implementazione pattern FastMCP nativi (lifespan management, context injection)
- Error handling robusto con messaggi informativi e graceful degradation
- Logging strutturato JSON per tutte le operazioni MCP

**Out-of-Scope:**

- Streamlit UI observability (Epic 3)
- Production infrastructure (CI/CD, Docker) - Epic 4
- Testing infrastructure (Epic 5)
- Modifiche al core RAG logic (solo integrazione observability)

## System Architecture Alignment

Epic 2 si allinea direttamente con l'architettura documentata in `docs/architecture.md`, implementando le decisioni architetturali ADR-001 (LangFuse Integration Pattern) e ADR-002 (MCP Server Standalone Architecture). I componenti principali coinvolti sono:

- **`mcp/`**: Modulo MCP server standalone con struttura organizzata per dominio

  - `mcp/server.py`: FastMCP instance con tool registration
  - `mcp/lifespan.py`: Server lifecycle management (DB init, embedder init)
  - `mcp/tools/search.py`: Tools per query (`query_knowledge_base`, `ask_knowledge_base`)
  - `mcp/tools/documents.py`: Tools per documenti (`list_knowledge_base_documents`, `get_knowledge_base_document`)
  - `mcp/tools/overview.py`: Tool overview (`get_knowledge_base_overview`)

- **`core/rag_service.py`**: Pure RAG logic decoupled, chiamato direttamente da MCP server (no HTTP overhead)

- **LangFuse Integration**: Decorator-based pattern con `@observe()` su funzioni critiche, `langfuse.openai` wrapper per cost tracking automatico

- **Prometheus Metrics**: Endpoint `/metrics` con metriche latency histograms, request count, error rate

L'epic implementa il pattern "Direct Service Integration" per MCP → Core RAG Service, eliminando la dipendenza HTTP e migliorando performance e affidabilità.

## Detailed Design

### Services and Modules

| Service/Module           | Responsibility                              | Inputs                           | Outputs                      | Owner    |
| ------------------------ | ------------------------------------------- | -------------------------------- | ---------------------------- | -------- |
| `mcp/server.py`          | FastMCP instance, tool registration         | FastMCP config, tool definitions | MCP server ready             | Dev Team |
| `mcp/lifespan.py`        | Server lifecycle (startup/shutdown)         | FastMCP app                      | Initialized resources        | Dev Team |
| `mcp/tools/search.py`    | Query tools (query_knowledge_base, ask)     | Query string, limit              | Search results, LLM response | Dev Team |
| `mcp/tools/documents.py` | Document tools (list, get)                  | Document ID, filters             | Document metadata/content    | Dev Team |
| `mcp/tools/overview.py`  | Overview tool (get_knowledge_base_overview) | None                             | KB statistics                | Dev Team |
| `core/rag_service.py`    | Pure RAG logic (decoupled)                  | Query, limit                     | Search results               | Dev Team |
| LangFuse Client          | Observability tracing                       | Function calls, LLM calls        | Traces, spans, cost data     | Dev Team |
| Prometheus Metrics       | Real-time metrics                           | Request data                     | Prometheus-format metrics    | Dev Team |

### Data Models and Contracts

**LangFuse Trace Structure:**

```python
Trace {
    id: str (UUID)
    name: str (e.g., "query_knowledge_base")
    user_id: Optional[str]
    session_id: Optional[str]
    metadata: Dict[str, Any] {
        "tool_name": str,
        "query": str,
        "limit": int,
        "source": "mcp"
    }
    start_time: datetime
    end_time: datetime
    duration_ms: float
    cost: float (total cost in USD)
    spans: List[Span] {
        embedding_generation: {
            name: "embedding-generation",
            duration_ms: float,
            input_tokens: int,
            cost: float
        },
        vector_search: {
            name: "vector-search",
            duration_ms: float,
            results_count: int
        },
        llm_generation: {
            name: "llm-generation",
            duration_ms: float,
            input_tokens: int,
            output_tokens: int,
            cost: float
        }
    }
}
```

**Prometheus Metrics:**

```python
# Counter: Total MCP requests
mcp_requests_total{tool_name="query_knowledge_base", status="success"} 42
mcp_requests_total{tool_name="query_knowledge_base", status="error"} 2

# Histogram: Request latency (seconds)
mcp_request_duration_seconds{tool_name="query_knowledge_base", le="0.5"} 10
mcp_request_duration_seconds{tool_name="query_knowledge_base", le="1.0"} 30
mcp_request_duration_seconds{tool_name="query_knowledge_base", le="2.0"} 40

# Histogram: Embedding generation time
rag_embedding_time_seconds{le="0.1"} 5
rag_embedding_time_seconds{le="0.3"} 20
rag_embedding_time_seconds{le="0.5"} 35

# Histogram: DB search time
rag_db_search_time_seconds{le="0.05"} 10
rag_db_search_time_seconds{le="0.1"} 30
rag_db_search_time_seconds{le="0.2"} 38

# Histogram: LLM generation time
rag_llm_generation_time_seconds{le="1.0"} 15
rag_llm_generation_time_seconds{le="2.0"} 35
rag_llm_generation_time_seconds{le="3.0"} 40

# Gauge: Active requests
mcp_active_requests 3
```

**MCP Tool Error Response:**

```python
ToolError {
    message: str (user-friendly error message)
    code: Optional[str] (error code for programmatic handling)
    details: Optional[Dict[str, Any]] (additional context, masked in production)
}
```

### APIs and Interfaces

**MCP Tools:**

1. **`query_knowledge_base(query: str, limit: int = 5)`**

   - **Input**: Query string, optional limit (default: 5)
   - **Output**: Formatted string with search results and citations
   - **Error Handling**: `ToolError` for validation errors, exception wrapping for unexpected errors
   - **Tracing**: Full trace with spans for embedding, DB search, LLM generation

2. **`ask_knowledge_base(query: str, limit: int = 5)`**

   - **Input**: Query string, optional limit
   - **Output**: LLM-generated response with citations
   - **Error Handling**: `ToolError` for validation errors
   - **Tracing**: Full trace with cost tracking for LLM generation

3. **`list_knowledge_base_documents(limit: int = 100, offset: int = 0)`**

   - **Input**: Optional limit and offset for pagination
   - **Output**: List of document metadata (id, title, source, created_at)
   - **Error Handling**: `ToolError` for DB errors
   - **Tracing**: Simple trace for DB query

4. **`get_knowledge_base_document(document_id: str)`**

   - **Input**: Document ID (UUID)
   - **Output**: Full document content with metadata
   - **Error Handling**: `ToolError` if document not found
   - **Tracing**: Simple trace for DB query

5. **`get_knowledge_base_overview()`**
   - **Input**: None
   - **Output**: KB statistics (total documents, total chunks, unique sources, source list)
   - **Error Handling**: `ToolError` for DB errors
   - **Tracing**: Simple trace for DB aggregation queries

**Prometheus Metrics Endpoint:**

- **GET `/metrics`**
  - **Response**: Prometheus-format metrics (text/plain)
  - **Content-Type**: `application/openmetrics-text; version=1.0.0; charset=utf-8`
  - **Metrics**: Counters, histograms, gauges per MCP operations
  - **Scraping Configuration**: Recommended `scrape_interval: 15s` in Prometheus config (default). For cost-sensitive deployments, 60s acceptable but reduces alert responsiveness. Evaluation interval should match scrape interval (default: 15s).

**Health Check Endpoint:**

- **GET `/health`** (implemented in Epic 2, enhanced in Epic 4)
  - **Response**: `{"status": "ok"|"degraded"|"down", "timestamp": float, "services": {...}}`
  - **Services Check**:
    - Database connection (PostgreSQL + PGVector)
    - LangFuse connectivity (optional, degraded if unavailable)
    - Embedder readiness (global singleton initialized)
  - **Purpose**: Service availability check for MCP server standalone
  - **Implementation**: FastAPI endpoint in `mcp/server.py` or separate `mcp/health.py`
  - **Note**: Basic health check implemented in Epic 2 Story 2.3, enhanced with detailed service checks in Epic 4 Story 4.2

### Workflows and Sequencing

**MCP Query Workflow (with LangFuse Tracing):**

1. **Tool Invocation** (`query_knowledge_base` called)

   - LangFuse creates root trace with metadata (tool_name, query, limit)
   - Prometheus counter incremented: `mcp_requests_total{tool_name="query_knowledge_base"}`
   - Prometheus gauge incremented: `mcp_active_requests`

2. **Embedding Generation** (nested span)

   - LangFuse creates span: `embedding-generation`
   - Start timer for Prometheus histogram: `rag_embedding_time_seconds`
   - Call `generate_embedding(query)` via `langfuse.openai` wrapper
   - LangFuse automatically tracks input tokens and cost
   - End timer, record to Prometheus histogram
   - Update LangFuse span with embedding_dim output

3. **Vector Search** (nested span)

   - LangFuse creates span: `vector-search`
   - Start timer for Prometheus histogram: `rag_db_search_time_seconds`
   - Call `search_vector_db(embedding, limit)` via direct DB connection
   - End timer, record to Prometheus histogram
   - Update LangFuse span with results_count output

4. **LLM Generation** (nested span, if `ask_knowledge_base`)

   - LangFuse creates span: `llm-generation` (as_type="generation")
   - Start timer for Prometheus histogram: `rag_llm_generation_time_seconds`
   - Call LLM via `langfuse.openai.chat.completions.create()`
   - LangFuse automatically tracks input/output tokens and cost
   - End timer, record to Prometheus histogram
   - Update LangFuse span with response content

5. **Response Formatting**

   - Format results with citations
   - Update root trace with final output
   - Prometheus counter incremented: `mcp_requests_total{status="success"}`
   - Prometheus gauge decremented: `mcp_active_requests`
   - Record total duration to Prometheus histogram: `mcp_request_duration_seconds`

6. **Error Handling** (if error occurs)
   - Catch exception, wrap in `ToolError` for user-facing errors
   - Log error with structured JSON logging (error, context, stack_trace)
   - Update LangFuse trace with error information
   - Prometheus counter incremented: `mcp_requests_total{status="error"}`
   - Prometheus gauge decremented: `mcp_active_requests`
   - Raise `ToolError` with informative message

**MCP Server Startup Sequence:**

1. FastMCP lifespan context manager starts
2. Initialize LangFuse client from environment variables
3. Initialize DB connection pool (`utils.db_utils.init_db_pool()`)
4. Initialize embedder singleton (`ingestion.embedder.init_embedder()`)
5. Register all MCP tools (`mcp.tools.*`)
6. Server ready for requests
7. On shutdown: Close DB pool, cleanup resources

## Non-Functional Requirements

### Performance

**NFR-P1: Latency Targets**

- MCP query latency < 2s (95th percentile) - measured via Prometheus histogram `mcp_request_duration_seconds`
- Embedding generation < 500ms per batch - measured via `rag_embedding_time_seconds`
- DB vector search < 100ms per query - measured via `rag_db_search_time_seconds`
- LLM generation < 1.5s for typical queries - measured via `rag_llm_generation_time_seconds`

**NFR-P2: Throughput**

- Support 50 queries/second with <10% degradation
- Connection pool sized appropriately (2-10 connections)
- Global embedder singleton eliminates per-request initialization overhead

**NFR-P3: Observability Overhead**

- LangFuse tracing overhead < 50ms per trace
- Prometheus metrics collection overhead < 5ms per request
- Graceful degradation: system continues if LangFuse unavailable

### Security

**NFR-SEC1: API Key Management**

- LangFuse API keys stored in environment variables (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`)
- Keys never logged, never committed to git
- Secret scanning in CI/CD (TruffleHog) prevents key leaks

**NFR-SEC2: Error Message Security**

- User-facing errors via `ToolError` do not expose sensitive information
- Stack traces only in structured logs (not in user messages)
- `mask_error_details=True` in production for FastMCP

**NFR-SEC3: Trace Data Privacy**

- No PII in LangFuse traces (query text may contain sensitive data, handled per org policy)
- Metadata sanitized before sending to LangFuse

### Reliability/Availability

**NFR-R1: Graceful Degradation**

- System continues to function if LangFuse unavailable (no blocking)
- Errors in LangFuse integration do not crash MCP server
- Fallback logging to structured JSON if LangFuse fails

**NFR-R2: Error Recovery**

- Retry logic for transient LangFuse API errors (max 3 attempts, exponential backoff)
- Non-retryable errors logged and operation continues
- DB connection errors handled gracefully with informative messages

**NFR-R3: Resource Management**

- DB connection pool properly sized (2-10 connections)
- Embedder singleton prevents resource leaks
- FastMCP lifespan pattern ensures proper cleanup on shutdown

### Observability

**NFR-OBS1: Trace Completeness**

- 100% of MCP tool calls traced in LangFuse
- All critical operations have nested spans (embedding, DB, LLM)
- Trace metadata includes: tool_name, query, limit, source, session_id

**NFR-OBS2: Cost Tracking Accuracy**

- Cost calculated automatically via `langfuse.openai` wrapper
- Pricing always current (LangFuse SDK updates pricing)
- Breakdown available: embedding_cost + llm_generation_cost

**NFR-OBS3: Metrics Availability**

- Prometheus metrics endpoint `/metrics` always available
- Metrics updated in real-time (no batching delay)
- Histogram buckets configured for latency analysis (0.1s, 0.5s, 1.0s, 1.5s, 2.0s, 3.0s, 5.0s)

**NFR-OBS4: Logging Structure**

- All logs in JSON format (structured logging)
- Log levels: DEBUG (dev), INFO (production), WARNING, ERROR, CRITICAL
- Context included: request_id, session_id, tool_name, error details

## Dependencies and Integrations

**External Dependencies:**

- **LangFuse Python SDK**: v3.0.0+ (OTel-based, async HTTP)

  - Purpose: Observability tracing and cost tracking
  - Integration: Decorator pattern `@observe()`, `langfuse.openai` wrapper
  - Environment Variables: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` (optional)

- **FastMCP**: 0.4.x+

  - Purpose: MCP server framework
  - Integration: Lifespan pattern, tool registration, context injection
  - Breaking Changes: Lifespan pattern (not startup/shutdown hooks), `ToolError` for errors

- **prometheus_client**: Latest

  - Purpose: Prometheus metrics collection
  - Integration: Counters, histograms, gauges, `/metrics` endpoint

- **python-json-logger**: 4.0.0+

  - Purpose: Structured JSON logging
  - Integration: Logging configuration for production

- **tenacity**: 9.1.2+
  - Purpose: Retry logic for transient errors
  - Integration: Exponential backoff for LangFuse API calls

**Internal Dependencies:**

- **`core/rag_service.py`**: Pure RAG logic (direct import, no HTTP)

  - Functions: `search_knowledge_base_structured()`, `generate_response()`
  - Integration: Direct function calls from MCP tools

- **`utils/db_utils.py`**: Database connection pooling

  - Functions: `init_db_pool()`, `close_db_pool()`, `get_db_pool()`
  - Integration: FastMCP lifespan initializes pool at startup

- **`ingestion/embedder.py`**: Embedding generation
  - Functions: `init_embedder()`, `generate_embedding()`
  - Integration: Global singleton initialized at startup

**Integration Points:**

1. **MCP Server → Core RAG Service**: Direct function calls (no HTTP overhead)
2. **MCP Server → LangFuse**: Async HTTP via LangFuse SDK v3
3. **MCP Server → Prometheus**: Metrics exposed via `/metrics` endpoint (pull model)
4. **MCP Server → Database**: Direct connection via AsyncPG pool
5. **MCP Server → OpenAI**: Via `langfuse.openai` wrapper for cost tracking

## Acceptance Criteria (Authoritative)

**Story 2.1: Integrate LangFuse SDK**

1. **Given** `mcp/server.py`, **When** I start the MCP server, **Then** LangFuse client is initialized with API keys from environment variables (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`)
2. **Given** a query, **When** `query_knowledge_base` tool is called, **Then** a new trace is created in LangFuse with metadata (tool_name, query, limit)
3. **Given** LangFuse dashboard, **When** I view traces, **Then** I see all MCP queries with timestamps and tool names
4. **Given** LangFuse unavailable, **When** I call MCP tools, **Then** system continues to function without errors (graceful degradation)

**Story 2.2: Implement Cost Tracking**

5. **Given** a query, **When** embeddings are generated via `langfuse.openai`, **Then** input tokens are counted and cost calculated automatically
6. **Given** a query, **When** LLM generates response via `langfuse.openai.chat.completions.create()`, **Then** input/output tokens are counted and cost calculated automatically
7. **Given** LangFuse trace, **When** I view it, **Then** I see total cost breakdown (embedding_cost + llm_generation_cost) in USD
8. **Given** cost data, **When** I check pricing, **Then** it matches current OpenAI pricing (`text-embedding-3-small` = $0.00002/1K tokens, `gpt-4o-mini` = $0.00015/1K input, $0.0006/1K output)

**Story 2.3: Add Performance Metrics**

9. **Given** a query, **When** it completes, **Then** I see timing breakdown in LangFuse spans: `embedding_time`, `db_search_time`, `llm_generation_time`
10. **Given** LangFuse trace, **When** I view spans, **Then** each component (embedder, DB, LLM) has separate span with duration in milliseconds
11. **Given** metrics endpoint, **When** I query `GET /metrics`, **Then** I see Prometheus-format metrics with latency histograms (`mcp_request_duration_seconds`, `rag_embedding_time_seconds`, `rag_db_search_time_seconds`, `rag_llm_generation_time_seconds`) and request counters (`mcp_requests_total`)
12. **Given** Prometheus metrics, **When** I scrape them, **Then** histogram buckets are configured appropriately (0.1s, 0.5s, 1.0s, 1.5s, 2.0s, 3.0s, 5.0s for request duration)
13. **Given** Prometheus configuration, **When** I set scrape_interval, **Then** recommended value is 15s (default) for real-time monitoring, or 60s for cost-sensitive deployments
14. **Given** MCP server, **When** I query `GET /health`, **Then** I get JSON response with status (ok/degraded/down), timestamp, and services status (database, langfuse, embedder)
15. **Given** health check endpoint, **When** database is unavailable, **Then** status is "down" with service details
16. **Given** health check endpoint, **When** LangFuse is unavailable, **Then** status is "degraded" (MCP server continues to function)

**Story 2.4: Create LangFuse Dashboard**

17. **Given** LangFuse UI, **When** I open the dashboard, **Then** I see key metrics: total queries, avg latency, total cost (today/week/month)
18. **Given** the dashboard, **When** I filter by date range, **Then** I see cost trends over time with charts
19. **Given** the dashboard, **When** I click a trace, **Then** I see full query details (input, output, cost breakdown, timing breakdown, spans)
20. **Given** dashboard views, **When** I configure them, **Then** custom charts for cost trends are available

**Story 2.5: Refactor MCP Server Architecture (Standalone)**

21. **Given** the MCP server, **When** I start it, **Then** it works without `api/main.py` running (standalone)
22. **Given** the codebase, **When** I check MCP server structure, **Then** it's organized in `mcp/` module with tools separated by domain (`mcp/tools/search.py`, `mcp/tools/documents.py`, `mcp/tools/overview.py`)
23. **Given** the MCP server, **When** I inspect it, **Then** it uses `core/rag_service.py` directly via `from core.rag_service import search_knowledge_base_structured` (no `client/api_client.py` dependency)
24. **Given** the MCP server, **When** I check implementation, **Then** it uses FastMCP native patterns: lifespan management (`@asynccontextmanager`), context injection (`Context` parameter type-hinted)
25. **Given** all MCP tools, **When** I test them, **Then** `query_knowledge_base`, `list_knowledge_base_documents`, `get_knowledge_base_document`, `get_knowledge_base_overview`, and `ask_knowledge_base` all work correctly without errors
26. **Given** an error occurs, **When** the MCP server handles it, **Then** it provides informative error messages via `ToolError` and graceful degradation (no crashes)

## Traceability Mapping

| AC ID | Spec Section                     | Component/API                         | Test Idea                                                |
| ----- | -------------------------------- | ------------------------------------- | -------------------------------------------------------- |
| AC1   | LangFuse Integration             | `mcp/server.py` (startup)             | Test LangFuse client initialization from env vars        |
| AC2   | LangFuse Tracing                 | `mcp/tools/search.py`                 | Test trace creation on tool call                         |
| AC3   | LangFuse Dashboard               | LangFuse UI                           | Verify traces visible in dashboard                       |
| AC4   | Graceful Degradation             | `mcp/server.py` (error handling)      | Test MCP server works without LangFuse                   |
| AC5   | Cost Tracking (Embedding)        | `ingestion/embedder.py`               | Test token counting and cost calculation                 |
| AC6   | Cost Tracking (LLM)              | `mcp/tools/search.py` (ask_knowledge) | Test LLM token counting and cost                         |
| AC7   | Cost Breakdown                   | LangFuse trace                        | Verify cost breakdown in trace view                      |
| AC8   | Pricing Accuracy                 | LangFuse SDK                          | Verify pricing matches OpenAI current rates              |
| AC9   | Timing Breakdown                 | LangFuse spans                        | Test span creation with timing data                      |
| AC10  | Span Hierarchy                   | LangFuse trace structure              | Verify nested spans for each component                   |
| AC11  | Prometheus Metrics               | `mcp/metrics.py` or FastAPI endpoint  | Test `/metrics` endpoint returns Prometheus format       |
| AC12  | Histogram Buckets                | Prometheus metrics config             | Verify histogram bucket configuration                    |
| AC13  | Prometheus Scraping Config       | Prometheus `prometheus.yml`           | Verify scrape_interval configured (15s recommended)      |
| AC14  | Health Check Endpoint            | `mcp/health.py` or `mcp/server.py`    | Test `/health` endpoint returns status and services      |
| AC15  | Health Check (DB Down)           | `mcp/health.py`                       | Test health check detects database unavailability        |
| AC16  | Health Check (LangFuse Degraded) | `mcp/health.py`                       | Test health check shows degraded if LangFuse unavailable |
| AC17  | Dashboard Metrics                | LangFuse UI                           | Verify key metrics displayed                             |
| AC18  | Cost Trends                      | LangFuse dashboard                    | Test date range filtering                                |
| AC19  | Trace Details                    | LangFuse trace view                   | Verify full query details in trace                       |
| AC20  | Custom Charts                    | LangFuse dashboard config             | Test custom chart configuration                          |
| AC21  | Standalone MCP                   | `mcp/server.py`                       | Test MCP server starts without API server                |
| AC22  | Module Organization              | `mcp/` directory structure            | Verify tools organized by domain                         |
| AC23  | Direct Core Integration          | `mcp/tools/*.py`                      | Test direct import from `core/rag_service.py`            |
| AC24  | FastMCP Patterns                 | `mcp/lifespan.py`, tool handlers      | Test lifespan pattern and context injection              |
| AC25  | Tool Functionality               | All MCP tools                         | Integration tests for all tools                          |
| AC26  | Error Handling                   | `mcp/tools/*.py`                      | Test `ToolError` handling and graceful degradation       |

## Risks, Assumptions, Open Questions

**Risks:**

1. **LangFuse API Availability** (Risk: Medium)

   - **Description**: LangFuse API unavailable could impact observability
   - **Mitigation**: Graceful degradation implemented - system continues without LangFuse
   - **Status**: Mitigated via error handling

2. **Performance Overhead** (Risk: Low)

   - **Description**: LangFuse tracing could add latency overhead
   - **Mitigation**: Async HTTP, non-blocking tracing, overhead < 50ms per trace
   - **Status**: Acceptable overhead

3. **Cost Tracking Accuracy** (Risk: Low)

   - **Description**: Pricing changes could affect cost calculation accuracy
   - **Mitigation**: LangFuse SDK automatically updates pricing, no manual updates needed
   - **Status**: Mitigated via SDK

4. **MCP Server Refactoring Complexity** (Risk: Medium)
   - **Description**: Refactoring to standalone could introduce bugs
   - **Mitigation**: Comprehensive testing (Story 2.5), incremental refactoring
   - **Status**: Requires careful implementation

**Assumptions:**

1. LangFuse API keys available in environment variables
2. LangFuse dashboard accessible for monitoring
3. FastMCP 0.4.x+ breaking changes understood and handled
4. Core RAG service (`core/rag_service.py`) stable and tested

**Open Questions:**

1. **Prometheus Scraping Frequency**: ✅ **RESOLVED** - Recommended scraping interval: **15 seconds** (default Prometheus). Rationale: For real-time monitoring of MCP server performance and costs, 15s provides good balance between data freshness and resource usage. For cost-sensitive deployments, 60s is acceptable but reduces alert responsiveness. Configuration: Set `scrape_interval: 15s` in Prometheus `prometheus.yml` for MCP server job. Evaluation interval should match or be multiple of scrape interval (default: 15s).
2. **Trace Retention**: How long should traces be retained in LangFuse? (Org policy - typically 7-30 days for production)
3. **Cost Alerting**: Should we implement cost alerts for budget thresholds? (Future enhancement - Epic 2 focuses on cost tracking, alerting can be added post-MVP)

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests** (60% coverage target):

   - LangFuse decorator application (`@observe()`)
   - Cost calculation logic (mock LangFuse client)
   - Prometheus metrics collection (mock requests)
   - Error handling (`ToolError` pattern)

2. **Integration Tests** (25% coverage target):

   - MCP server startup with LangFuse initialization
   - Tool execution with LangFuse tracing (mock LangFuse API)
   - Prometheus metrics endpoint (`/metrics` format validation)
   - FastMCP lifespan pattern (resource initialization)

3. **E2E Tests** (15% coverage target):
   - Full MCP query workflow with LangFuse tracing (real LangFuse, test instance)
   - Cost tracking accuracy validation (compare calculated vs LangFuse reported)
   - Dashboard visibility (verify traces appear in LangFuse UI)
   - Standalone MCP server (no API server dependency)

**Test Frameworks:**

- **pytest**: Unit and integration tests
- **pytest-asyncio**: Async test support
- **pytest-mock**: Mocking LangFuse client
- **FastMCP Client**: MCP server testing (in-memory transport)

**Coverage Targets:**

- `mcp/` module: >70% coverage
- LangFuse integration: >80% coverage (critical path)
- Prometheus metrics: >70% coverage

**Test Scenarios:**

1. LangFuse client initialization from env vars
2. Trace creation on tool call
3. Cost tracking accuracy (embedding + LLM)
4. Prometheus metrics format validation
5. Prometheus scraping configuration (15s interval)
6. Health check endpoint functionality (ok/degraded/down states)
7. Health check service detection (database, LangFuse, embedder)
8. MCP server standalone functionality
9. Error handling and graceful degradation
10. FastMCP lifespan pattern validation
11. Tool functionality (all 5 tools)
