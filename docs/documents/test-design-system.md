# System-Level Test Design

**Date:** 2025-11-26  
**Author:** Stefano  
**Project:** docling-rag-agent  
**Assessment Type:** System-Level Testability Review (Phase 3)  
**Status:** Draft

---

## Executive Summary

Questo documento valuta la testabilità dell'architettura di **docling-rag-agent** prima dell'implementazione (Phase 3 → Phase 4 gate check). L'analisi identifica punti di forza, aree di preoccupazione, e raccomandazioni per garantire che l'architettura supporti testing efficace a tutti i livelli (unit, integration, E2E).

**Overall Assessment:** ✅ **PASS WITH CONCERNS**

**Rationale:**

- ✅ Controllabilità: Buona (API seeding, dependency injection, mockable boundaries)
- ⚠️ Osservabilità: Parziale (LangFuse integrato, ma mancano metriche Prometheus complete)
- ✅ Affidabilità: Buona (isolamento, cleanup discipline, deterministic waits)
- ⚠️ Testability Concerns: Alcune aree richiedono attenzione (MCP server standalone, test environment setup)

---

## Testability Assessment

### Controllabilità: ✅ PASS

**Valutazione:** L'architettura supporta controllo efficace dello stato del sistema per testing.

**Punti di Forza:**

- **API Seeding**: Setup dati via API (`apiRequest.post('/api/users')`) invece di UI navigation (10-50x più veloce)
- **Dependency Injection**: Core business logic decoupled (`core/rag_service.py`) facilita mocking
- **Mockable Boundaries**:
  - LangFuse: Decorator `@observe()` può essere mocked o disabilitato per testing
  - OpenAI: PydanticAI `TestModel` per LLM mocking senza costi API
  - Database: Connection pool configurabile, test database supportato
- **Error Conditions**:
  - Retry logic con `tenacity` facilita testing di transient failures
  - `ToolError` pattern in MCP server permette testing di error handling

**Evidenze dall'Architettura:**

```python
# core/rag_service.py - Pure business logic, no framework dependencies
def search_knowledge_base_structured(query: str, limit: int = 5):
    # Testabile senza MCP server o Streamlit
    pass

# MCP server usa core direttamente (no HTTP overhead)
from core.rag_service import search_knowledge_base_structured
```

**Raccomandazioni:**

- ✅ Nessuna azione richiesta - controllabilità è adeguata

---

### Osservabilità: ⚠️ CONCERNS

**Valutazione:** Osservabilità è parziale - LangFuse integrato ma mancano metriche complete per NFR validation.

**Punti di Forza:**

- **LangFuse Integration**: Trace gerarchici automatici (`@observe()` decorator)
- **Structured Logging**: JSON logging configurato (`python-json-logger`)
- **Session Tracking**: `session_id` tracciato in Streamlit e MCP
- **Cost Tracking**: Automatico via `langfuse.openai` wrapper

**Aree di Preoccupazione:**

- **Prometheus Metrics**: Endpoint `/metrics` menzionato in PRD (FR11) ma non documentato in architecture
- **Health Checks**: `/health` endpoint definito ma dettagli di implementazione non chiari
- **Performance Baselines**: NFR targets definiti (latency < 2s, embedding < 500ms) ma mancano test infrastructure per validazione
- **Error Telemetry**: Logging strutturato presente ma manca integrazione con monitoring system (Sentry/Datadog)

**Evidenze dall'Architettura:**

```python
# LangFuse decorator pattern
@observe()
def search_knowledge_base_structured(query: str):
    # Trace automatico, ma mancano metriche Prometheus
    pass
```

**Raccomandazioni:**

1. **Implementare `/metrics` endpoint** (Epic 2, Story 2.3):

   - Prometheus format con latency histograms, request count, error rate
   - Metriche per: embedding_time, db_search_time, llm_generation_time
   - Threshold: Completare prima di Epic 2 completion

   **Implementazione Prometheus (Python `prometheus_client`):**

   ```python
   # api/metrics.py o mcp/metrics.py
   from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
   from fastapi import Response

   # Metric definitions
   REQUEST_COUNT = Counter(
       'mcp_requests_total',
       'Total number of MCP requests',
       ['tool_name', 'status']  # Labels for filtering
   )

   REQUEST_LATENCY = Histogram(
       'mcp_request_latency_seconds',
       'MCP request latency',
       ['tool_name'],
       buckets=[0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]  # Custom buckets for latency
   )

   EMBEDDING_TIME = Histogram(
       'rag_embedding_time_seconds',
       'Embedding generation time',
       buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 1.0]
   )

   DB_SEARCH_TIME = Histogram(
       'rag_db_search_time_seconds',
       'Database vector search time',
       buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
   )

   LLM_GENERATION_TIME = Histogram(
       'rag_llm_generation_time_seconds',
       'LLM response generation time',
       buckets=[0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
   )

   ACTIVE_REQUESTS = Gauge(
       'mcp_active_requests',
       'Number of active MCP requests'
   )

   # FastAPI endpoint
   @app.get("/metrics")
   async def metrics():
       return Response(
           content=generate_latest(),
           media_type=CONTENT_TYPE_LATEST
       )
   ```

   **Usage Pattern:**

   ```python
   # In MCP tool handlers
   @mcp.tool
   async def query_knowledge_base(query: str, ctx: Context):
       ACTIVE_REQUESTS.inc()
       start_time = time.time()

       try:
           # Embedding generation
           with EMBEDDING_TIME.time():
               embedding = await generate_embedding(query)

           # DB search
           with DB_SEARCH_TIME.time():
               results = await search_vector_db(embedding)

           # LLM generation
           with LLM_GENERATION_TIME.time():
               response = await generate_response(results)

           REQUEST_COUNT.labels(tool_name='query_knowledge_base', status='success').inc()
           return response
       except Exception as e:
           REQUEST_COUNT.labels(tool_name='query_knowledge_base', status='error').inc()
           raise
       finally:
           REQUEST_LATENCY.labels(tool_name='query_knowledge_base').observe(time.time() - start_time)
           ACTIVE_REQUESTS.dec()
   ```

   **Prometheus Scraping Configuration (Pull Model):**

   Prometheus usa un **pull model** - il server Prometheus "scrapes" (raccoglie) metriche dal tuo endpoint `/metrics` via HTTP. Non è necessario pushare metriche manualmente.

   ```yaml
   # prometheus.yml
   global:
     scrape_interval: 15s # Default: scrape ogni 15 secondi
     evaluation_interval: 15s # Valuta regole ogni 15 secondi

   scrape_configs:
     - job_name: "docling-rag-agent"
       scrape_interval: 15s # Override per questo job
       metrics_path: "/metrics" # Default path
       static_configs:
         - targets: ["localhost:8000"] # MCP server or API server
           labels:
             service: "mcp-server"
             environment: "production"
   ```

   **Prometheus Architecture (da [documentazione ufficiale](https://prometheus.io/docs/introduction/overview/)):**

   - **Pull Model**: Prometheus scrapes metrics dal tuo endpoint `/metrics` via HTTP
   - **Time Series Data**: Metriche sono memorizzate come time series con timestamp e labels opzionali
   - **Multi-dimensional Data Model**: Ogni metrica può avere multiple labels (key/value pairs) per filtering e aggregation
   - **Standalone Server**: Ogni server Prometheus è autonomo, non dipende da storage distribuito
   - **PromQL**: Query language flessibile per analisi e alerting

   **Metric Naming Best Practices (da [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)):**

   - ✅ Usare suffissi standard: `_total` (Counter), `_seconds` (duration), `_bytes` (size)
   - ✅ Usare prefissi per dominio: `mcp_`, `rag_`, `db_`
   - ✅ Evitare underscore iniziali (riservati per uso interno)
   - ✅ Usare snake_case per metric names
   - ✅ Labels per differenziare caratteristiche: `tool_name`, `status`, `model`

   **Label Best Practices:**

   - ✅ Usare labels per filtering e aggregation (es. `tool_name`, `status`)
   - ⚠️ Limitare cardinalità labels (evitare valori unbounded come user_id, session_id)
   - ✅ Mantenere label values corti e bounded
   - ✅ Usare naming convention consistente per label keys

   **References:**

   - [Prometheus Overview](https://prometheus.io/docs/introduction/overview/) - Architecture e concetti base
   - [Prometheus Data Model](https://prometheus.io/docs/concepts/data_model/) - Time series e labels
   - [Prometheus Metric Naming](https://prometheus.io/docs/practices/naming/) - Best practices naming
   - [Prometheus Python Client](https://prometheus.io/docs/instrumenting/clientlibs/python/) - Python client library
   - [Prometheus Histograms Best Practices](https://prometheus.io/docs/practices/histograms/) - Histogram configuration
   - [FastAPI Prometheus Integration](https://github.com/trallnag/prometheus-fastapi-instrumentator) - FastAPI integration

2. **Definire Health Check Contract** (Epic 4, Story 4.2):

   - JSON response con `status: ok/degraded/down`
   - Verifica: DB connection, LangFuse connectivity, embedder readiness
   - Threshold: Completare prima di Epic 4 completion

   **Implementazione Health Check (FastAPI Pattern):**

   ```python
   # api/health.py o mcp/health.py
   from fastapi import FastAPI, HTTPException
   from pydantic import BaseModel
   from typing import Dict, Literal
   import asyncpg
   from langfuse import Langfuse

   class HealthStatus(BaseModel):
       status: Literal["ok", "degraded", "down"]
       timestamp: float
       services: Dict[str, Dict[str, str]]

   async def check_database() -> Dict[str, str]:
       """Check PostgreSQL + PGVector connection."""
       try:
           pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=1)
           async with pool.acquire() as conn:
               await conn.fetchval("SELECT 1")
           await pool.close()
           return {"status": "UP", "message": "Database connection OK"}
       except Exception as e:
           return {"status": "DOWN", "message": f"Database error: {str(e)}"}

   async def check_langfuse() -> Dict[str, str]:
       """Check LangFuse connectivity."""
       try:
           langfuse = Langfuse()
           # Simple connectivity check (no actual API call needed)
           if langfuse.public_key and langfuse.secret_key:
               return {"status": "UP", "message": "LangFuse configured"}
           return {"status": "DEGRADED", "message": "LangFuse not configured"}
       except Exception as e:
           return {"status": "DOWN", "message": f"LangFuse error: {str(e)}"}

   async def check_embedder() -> Dict[str, str]:
       """Check embedder readiness."""
       try:
           # Check if global embedder is initialized
           from ingestion.embedder import _embedder_ready
           if _embedder_ready.is_set():
               return {"status": "UP", "message": "Embedder ready"}
           return {"status": "DEGRADED", "message": "Embedder initializing"}
       except Exception as e:
           return {"status": "DOWN", "message": f"Embedder error: {str(e)}"}

   @app.get("/health", response_model=HealthStatus)
   async def health_check():
       """Health check endpoint with service status."""
       import time

       services = {
           "database": await check_database(),
           "langfuse": await check_langfuse(),
           "embedder": await check_embedder()
       }

       # Determine overall status
       service_statuses = [s["status"] for s in services.values()]

       if "DOWN" in service_statuses:
           status = "down"
       elif "DEGRADED" in service_statuses:
           status = "degraded"
       else:
           status = "ok"

       return HealthStatus(
           status=status,
           timestamp=time.time(),
           services=services
       )
   ```

   **Health Check Response Example:**

   ```json
   {
     "status": "ok",
     "timestamp": 1701000000.0,
     "services": {
       "database": {
         "status": "UP",
         "message": "Database connection OK"
       },
       "langfuse": {
         "status": "UP",
         "message": "LangFuse configured"
       },
       "embedder": {
         "status": "UP",
         "message": "Embedder ready"
       }
     }
   }
   ```

   **Testing Health Checks:**

   ```python
   # tests/integration/test_health.py
   async def test_health_check_ok(api_client):
       response = await api_client.get("/health")
       assert response.status_code == 200
       data = response.json()
       assert data["status"] == "ok"
       assert all(s["status"] == "UP" for s in data["services"].values())

   async def test_health_check_degraded(api_client, monkeypatch):
       # Mock LangFuse unavailable
       monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
       response = await api_client.get("/health")
       assert response.status_code == 200
       data = response.json()
       assert data["status"] == "degraded"
   ```

   **References:**

   - [FastAPI Health Check Patterns](https://github.com/Kludex/fastapi-health)
   - [Health Check API Pattern](https://microservices.io/patterns/observability/health-check-api.html)

3. **Setup Performance Test Infrastructure** (Epic 5, Story 5.3):
   - k6 load testing per NFR validation (NFR-P1: latency < 2s)
   - Baseline measurements per embedding generation (NFR-P2: < 500ms)
   - Threshold: Completare prima di Epic 5 completion

**Risk Score:** 4 (TECH, Probability: 2, Impact: 2) - Medium priority, mitigation plan definito

---

### Affidabilità: ✅ PASS

**Valutazione:** L'architettura supporta test isolati e deterministici.

**Punti di Forza:**

- **Test Isolation**:
  - Connection pool per-process (non shared state)
  - Session state isolato (`st.session_state` per Streamlit)
  - MCP server standalone (no shared API server)
- **Cleanup Discipline**:
  - Fixtures con auto-cleanup (pattern documentato in test-quality.md)
  - Database transactions per test isolation
- **Deterministic Waits**:
  - Network-first pattern (`waitForResponse` invece di `waitForTimeout`)
  - LangFuse spans per timing breakdown
- **Loosely Coupled Components**:
  - `core/rag_service.py` decoupled da framework (MCP, Streamlit)
  - Dependency injection pattern per external services

**Evidenze dall'Architettura:**

```python
# MCP server standalone - no shared state
# mcp/server.py
from core.rag_service import search_knowledge_base_structured
# Direct function calls, no HTTP overhead

# Connection pool per-process
# utils/db_utils.py
db_pool = asyncpg.create_pool(...)  # Isolated per test
```

**Raccomandazioni:**

- ✅ Nessuna azione richiesta - affidabilità è adeguata

---

## Architecturally Significant Requirements (ASRs)

ASRs sono requisiti di qualità che guidano decisioni architetturali e pongono sfide di testabilità.

### ASR-001: LangFuse Observability Integration

**Requirement:** FR7-FR12 (MCP Server Observability), FR13-FR16 (Streamlit Observability)

**Architecture Decision:** ADR-001 - LangFuse decorator-based pattern (`@observe()`) con `langfuse.openai` wrapper

**Testability Challenge:** Validare trace completi, cost tracking accuracy, performance breakdown

**Risk Score:** 3 (TECH, Probability: 2, Impact: 1.5) - Low-Medium

**Mitigation Strategy:**

- **Unit Tests**: Mock LangFuse client, validare decorator application
- **Integration Tests**: Validare trace structure, cost calculation accuracy
- **E2E Tests**: Validare trace visibility in LangFuse dashboard
- **NFR Tests**: Validare performance overhead < 50ms per trace

**Test Levels Strategy:**

- **Unit**: Mock LangFuse, test decorator logic (70% coverage)
- **Integration**: Real LangFuse client, test trace creation (20% coverage)
- **E2E**: Full system, validare dashboard visibility (10% coverage)

---

### ASR-002: MCP Server Standalone Architecture

**Requirement:** FR12.1-FR12.6 (MCP Server Architecture & Fix)

**Architecture Decision:** ADR-002 - MCP server usa `core/rag_service.py` direttamente, elimina dipendenza HTTP

**Testability Challenge:** Validare MCP server funziona senza API server, testare FastMCP lifespan pattern

**Risk Score:** 4 (TECH, Probability: 2, Impact: 2) - Medium

**Mitigation Strategy:**

- **Unit Tests**: Mock `core/rag_service.py`, test MCP tool logic
- **Integration Tests**: Test MCP server startup, lifespan management, tool execution
- **E2E Tests**: Test MCP server standalone, validare tutti i tool funzionano

**Test Levels Strategy:**

- **Unit**: Mock core services, test tool handlers (60% coverage)
- **Integration**: Real DB + embedder, test MCP server lifecycle (30% coverage)
- **E2E**: Full MCP server, test tool execution end-to-end (10% coverage)

**FastMCP Testing Patterns:**

```python
# tests/integration/test_mcp_server.py
import pytest
from fastmcp import FastMCP, Client
from fastmcp.client.transports import FastMCPTransport
from mcp.server import mcp_server  # Import your MCP server instance

@pytest.fixture
async def mcp_client():
    """Create FastMCP client for testing."""
    async with Client(transport=mcp_server) as client:
        yield client

async def test_mcp_server_startup(mcp_client: Client[FastMCPTransport]):
    """Test MCP server startup and tool registration."""
    tools = await mcp_client.list_tools()
    assert len(tools) >= 4  # query_knowledge_base, list_documents, get_document, get_overview
    tool_names = [tool.name for tool in tools]
    assert "query_knowledge_base" in tool_names

async def test_query_knowledge_base_tool(mcp_client: Client[FastMCPTransport]):
    """Test query_knowledge_base tool execution."""
    result = await mcp_client.call_tool(
        "query_knowledge_base",
        {"query": "test query", "limit": 5}
    )
    assert result.content[0].text is not None
    assert len(result.content) > 0

async def test_mcp_lifespan_management():
    """Test FastMCP lifespan pattern (startup/shutdown)."""
    from mcp.lifespan import lifespan_manager

    # Test startup
    async with lifespan_manager():
        # Verify resources initialized
        from utils.db_utils import db_pool
        assert db_pool is not None

        from ingestion.embedder import _embedder_ready
        assert _embedder_ready.is_set()

    # After context exit, resources should be cleaned up
    # (FastMCP lifespan handles cleanup automatically)

async def test_mcp_error_handling(mcp_client: Client[FastMCPTransport]):
    """Test MCP error handling with ToolError pattern."""
    # Test invalid parameters
    with pytest.raises(Exception) as exc_info:
        await mcp_client.call_tool(
            "query_knowledge_base",
            {"query": ""}  # Empty query should fail validation
        )
    assert "query" in str(exc_info.value).lower()
```

**FastMCP Context Testing:**

```python
# tests/integration/test_mcp_context.py
from fastmcp import Context
from mcp.tools.search import query_knowledge_base

async def test_context_injection():
    """Test FastMCP context injection in tool handlers."""
    # Mock context
    mock_ctx = Mock(spec=Context)
    mock_ctx.log = AsyncMock()

    # Test tool with context
    result = await query_knowledge_base("test", ctx=mock_ctx)

    # Verify context was used for logging
    mock_ctx.log.assert_called()
```

**References:**

- [FastMCP Testing Guide](https://gofastmcp.com/development/tests.md)
- [FastMCP Client Testing](https://gofastmcp.com/patterns/testing)
- [FastMCP Context Documentation](https://gofastmcp.com/servers/context.md)

---

### ASR-003: Performance Targets (NFR-P1, NFR-P2, NFR-P3)

**Requirement:** NFR-P1 (latency < 2s), NFR-P2 (embedding < 500ms), NFR-P3 (DB search < 100ms)

**Architecture Decision:** Global embedder singleton, HNSW index, connection pooling

**Testability Challenge:** Validare performance targets con k6 load testing, baseline measurements

**Risk Score:** 6 (PERF, Probability: 2, Impact: 3) - High Priority

**Mitigation Strategy:**

- **Performance Tests**: k6 load testing per latency validation (NFR-P1)
- **Baseline Tests**: Embedding generation timing (NFR-P2), DB search timing (NFR-P3)
- **Stress Tests**: Identificare breaking point (50 queries/secondo, NFR-P4)
- **Monitoring**: Prometheus metrics per real-time performance tracking

**Test Levels Strategy:**

- **Performance**: k6 load tests (stages: ramp up, sustained load, spike)
- **Baseline**: Unit tests con timing assertions per embedding/DB operations
- **Integration**: API tests con performance assertions

**Owner:** DevOps/QA Team  
**Timeline:** Epic 5 completion (Story 5.3 - RAGAS Evaluation Suite)  
**Status:** Planned

---

### ASR-004: TDD Structure Rigorosa

**Requirement:** FR31-FR44 (Testing & Quality Assurance)

**Architecture Decision:** ADR-003 - TDD structure con `tests/unit/`, `tests/integration/`, `tests/e2e/`, coverage >70%

**Testability Challenge:** Garantire struttura test rigorosa, coverage enforcement, RAGAS evaluation

**Risk Score:** 3 (TECH, Probability: 1, Impact: 3) - Low-Medium

**Mitigation Strategy:**

- **Test Infrastructure**: Setup pytest con fixtures, coverage tracking
- **Coverage Enforcement**: CI/CD fail se coverage < 70%
- **RAGAS Evaluation**: Golden dataset (20+ pairs), faithfulness > 0.85, relevancy > 0.80
- **E2E Tests**: Playwright per Streamlit workflows critici

**Test Levels Strategy:**

- **Unit**: 70% coverage target (core/, ingestion/, utils/)
- **Integration**: MCP server, API endpoints
- **E2E**: Critical user journeys (Streamlit query flow)

---

### ASR-005: Security Requirements (NFR-SEC1, NFR-SEC2, NFR-SEC3)

**Requirement:** NFR-SEC1 (API keys in env vars), NFR-SEC2 (LangFuse key protected), NFR-SEC3 (DB encryption)

**Architecture Decision:** Environment variables, secret scanning (TruffleHog), no hardcoding

**Testability Challenge:** Validare secret handling, security scanning, no secrets in logs

**Risk Score:** 6 (SEC, Probability: 2, Impact: 3) - High Priority

**Mitigation Strategy:**

- **Security Tests**: Playwright E2E per validare secrets non esposti
- **CI/CD Scanning**: TruffleHog OSS su ogni PR (fail build se secrets rilevati)
- **Logging Validation**: Test che verificano secrets non appaiono in logs
- **Secret Rotation**: Test per validare environment variable loading

**Test Levels Strategy:**

- **E2E**: Security tests (secrets non esposti, auth bypass attempts)
- **CI/CD**: Automated secret scanning
- **Unit**: Environment variable loading, secret masking

**Owner:** Security Team  
**Timeline:** Epic 4 completion (Story 4.1 - CI/CD Setup)  
**Status:** Planned

---

## Test Levels Strategy

**Rationale:** Distribuzione test levels basata su architettura (API-heavy RAG system con MCP server standalone).

### Recommended Split: 60% Unit / 25% Integration / 15% E2E

**Unit Tests (60%):**

- **Scope**: Core business logic (`core/rag_service.py`, `ingestion/embedder.py`, `ingestion/chunker.py`)
- **Rationale**:
  - Pure functions facilmente testabili
  - Mock LLM con PydanticAI `TestModel` (zero API costs)
  - Fast feedback (< 1s per test)
- **Coverage Target**: > 70% per core modules
- **Tools**: pytest, PydanticAI TestModel, pytest-mock

**Integration Tests (25%):**

- **Scope**:
  - MCP server tools (`mcp/tools/*.py`)
  - API endpoints (`api/main.py`)
  - Database operations (`utils/db_utils.py`)
- **Rationale**:
  - Validare component boundaries (MCP → core, API → core)
  - Test database operations con test DB
  - Validare LangFuse integration
- **Coverage Target**: Critical paths (MCP tools, API endpoints)
- **Tools**: pytest, asyncpg test pool, LangFuse test client

**E2E Tests (15%):**

- **Scope**:
  - Critical user journeys (Streamlit query flow)
  - MCP server standalone execution
  - Error handling workflows
- **Rationale**:
  - Validare user experience end-to-end
  - Highest confidence, slowest execution
  - Limitato a critical paths per velocità
- **Coverage Target**: Critical user journeys only
- **Tools**: Playwright, MCP client testing

**Test Environment Needs:**

- **Local Development**:
  - Test database (PostgreSQL + PGVector)
  - Mock LangFuse (optional, per speed)
  - Test OpenAI API key (rate-limited)
- **CI/CD**:
  - Docker containers per test isolation
  - Test database setup/teardown automatico
  - Coverage reporting automatico

---

## NFR Testing Approach

### Security (NFR-SEC1, NFR-SEC2, NFR-SEC3)

**Approach:** Playwright E2E tests + CI/CD secret scanning

**Tools:**

- **Playwright**: E2E security tests (secrets non esposti, auth bypass)
- **TruffleHog OSS**: Secret scanning su ogni PR
- **npm audit**: Dependency vulnerability scanning

**Test Scenarios:**

1. **Secret Handling**:

   - Validare API keys non loggati
   - Validare LangFuse keys non esposti in errori
   - Validare DB connection string non in logs

2. **Auth/Authz** (se applicabile):

   - Unauthenticated access blocked
   - RBAC enforcement (se multi-user)

3. **Input Validation**:
   - SQL injection blocked (se search endpoint)
   - XSS sanitization (se UI input)

**NFR Criteria:**

- ✅ PASS: Tutti i security tests green, TruffleHog passa, no secrets in logs
- ⚠️ CONCERNS: 1-2 test failures con mitigation plan
- ❌ FAIL: Critical exposure (secrets leaked, SQL injection succeeds)

---

### Performance (NFR-P1, NFR-P2, NFR-P3, NFR-P4)

**Approach:** k6 load testing + baseline unit tests

**Tools:**

- **k6**: Load/stress/spike testing per latency validation
- **Unit Tests**: Baseline measurements per embedding/DB operations
- **Prometheus**: Real-time metrics per monitoring

**Test Scenarios:**

1. **Latency Targets** (NFR-P1):

   - k6 load test: 50 VUs, validare p95 < 2s
   - SLO: 95% requests < 2s
   - Threshold: Fail se p95 > 2s

2. **Embedding Generation** (NFR-P2):

   - Unit test: Batch 100 chunks, validare < 500ms
   - Baseline: Misurare timing con cache enabled/disabled
   - Threshold: Fail se > 500ms

3. **DB Vector Search** (NFR-P3):

   - Integration test: Query con HNSW index, validare < 100ms
   - Baseline: Misurare timing con/senza index
   - Threshold: Fail se > 100ms

4. **Throughput** (NFR-P4):
   - k6 stress test: 50 queries/secondo, validare degradazione < 10%
   - Spike test: Sudden load increase, validare recovery
   - Threshold: Fail se degradazione > 10%

**NFR Criteria:**

- ✅ PASS: Tutti i SLO/SLA targets met con k6 evidence
- ⚠️ CONCERNS: Trending toward limits (p95 = 1.8s approaching 2s)
- ❌ FAIL: SLO/SLA breached (p95 > 2s, degradazione > 10%)

**Owner:** DevOps/QA Team  
**Timeline:** Epic 5 completion (Story 5.3)  
**Status:** Planned

---

### Reliability (NFR-R1, NFR-R2, NFR-R3)

**Approach:** Playwright E2E tests + API tests per error handling

**Tools:**

- **Playwright**: E2E error handling tests
- **API Tests**: Retry logic, health checks, circuit breaker

**Test Scenarios:**

1. **Error Handling**:

   - 500 error → user-friendly message + retry button
   - Network disconnection → offline indicator
   - API failure → graceful degradation

2. **Retry Logic** (NFR-R2):

   - Transient failures → 3 attempts con exponential backoff
   - Non-retryable errors → immediate failure
   - Validare retry count logged

3. **Health Checks** (NFR-R1):

   - `/health` endpoint → status: ok/degraded/down
   - DB connection verified
   - LangFuse connectivity verified

4. **Graceful Degradation** (NFR-R3):
   - LangFuse unavailable → sistema continua a funzionare
   - DB connection lost → error message, no crash
   - Embedder unavailable → clear error message

**NFR Criteria:**

- ✅ PASS: Error handling, retries, health checks verified
- ⚠️ CONCERNS: Partial coverage o missing telemetry
- ❌ FAIL: No recovery path (500 error crashes app)

---

### Maintainability (NFR-M1, NFR-M2, NFR-M3)

**Approach:** CI/CD tools + Playwright per observability validation

**Tools:**

- **GitHub Actions**: Coverage reporting, code duplication check
- **Playwright**: Observability validation (error tracking, telemetry)

**Test Scenarios:**

1. **Test Coverage** (NFR-M1):

   - CI/CD: Coverage report, fail se < 70%
   - Target: > 70% per core modules
   - Threshold: Fail build se coverage < 70%

2. **Documentation** (NFR-M2):

   - Docstrings per tutte le funzioni pubbliche
   - API documentation auto-generata
   - README con setup < 5 min

3. **Structured Logging** (NFR-M3):
   - Playwright: Validare JSON logging format
   - Validare trace IDs in headers
   - Validare error tracking (Sentry/monitoring)

**NFR Criteria:**

- ✅ PASS: Coverage > 70%, docstrings complete, structured logging validated
- ⚠️ CONCERNS: Coverage 60-69%, duplication > 5%
- ❌ FAIL: Coverage < 60%, no docstrings, no structured logging

---

## Test Environment Requirements

**Infrastructure Needs:**

1. **Test Database**:

   - PostgreSQL 16+ con PGVector extension
   - Test database isolato (non production)
   - Schema setup/teardown automatico per test isolation

2. **LangFuse Test Instance**:

   - Test LangFuse server (opzionale, mockable)
   - Test API keys per CI/CD
   - Trace validation senza production pollution

3. **OpenAI Test API Key**:

   - Rate-limited test key
   - Mock con PydanticAI `TestModel` per unit tests
   - Real API solo per integration/E2E tests

4. **Docker Containers**:
   - Test database container
   - Test LangFuse container (opzionale)
   - Isolated test environment per CI/CD

**Environment Configuration:**

```yaml
# test.env
DATABASE_URL=postgresql://test:test@localhost:5432/test_db
LANGFUSE_PUBLIC_KEY=test_public_key
LANGFUSE_SECRET_KEY=test_secret_key
LANGFUSE_BASE_URL=http://localhost:3000
OPENAI_API_KEY=test_key  # Rate-limited
ALLOW_MODEL_REQUESTS=false  # Per unit tests
```

---

## Testability Concerns

### Concern-001: MCP Server Standalone Testing

**Description:** MCP server standalone richiede test infrastructure specifica (FastMCP lifespan, context injection).

**Impact:** Medium - Richiede setup test infrastructure per MCP server lifecycle.

**Mitigation:**

- **Integration Tests**: Test MCP server startup, lifespan management
- **E2E Tests**: Test MCP server standalone execution
- **Documentation**: Guida test setup per MCP server

**Risk Score:** 3 (TECH, Probability: 2, Impact: 1.5) - Low-Medium

**Status:** Mitigation planned in Epic 2 (Story 2.5)

---

### Concern-002: Performance Test Infrastructure Missing

**Description:** Performance targets (NFR-P1, NFR-P2, NFR-P3) richiedono k6 load testing ma infrastructure non ancora setup.

**Impact:** High - Impossibile validare performance targets senza k6 infrastructure.

**Mitigation:**

- **k6 Setup**: Install k6, create load test scripts
- **Baseline Tests**: Unit tests con timing assertions
- **CI/CD Integration**: k6 tests in CI/CD pipeline

**k6 Load Test Implementation:**

```javascript
// tests/performance/mcp_load_test.k6.js
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("errors");
const mcpLatency = new Trend("mcp_latency_seconds");

// Performance thresholds (SLO/SLA)
export const options = {
  stages: [
    { duration: "1m", target: 10 }, // Ramp up to 10 VUs
    { duration: "3m", target: 10 }, // Stay at 10 VUs
    { duration: "1m", target: 50 }, // Spike to 50 VUs
    { duration: "3m", target: 50 }, // Stay at 50 VUs
    { duration: "1m", target: 0 }, // Ramp down
  ],
  thresholds: {
    // SLO: 95% of requests must complete in <2s
    http_req_duration: ["p(95)<2000"],
    // SLO: Error rate must be <1%
    errors: ["rate<0.01"],
    // Custom metric: MCP latency
    mcp_latency_seconds: ["p(95)<2.0"],
  },
};

export default function () {
  // Test MCP query_knowledge_base via API proxy (if available)
  // Or test directly via MCP client simulation
  const payload = JSON.stringify({
    method: "tools/call",
    params: {
      name: "query_knowledge_base",
      arguments: {
        query: "test query",
        limit: 5,
      },
    },
  });

  const response = http.post(`${__ENV.MCP_SERVER_URL}/mcp`, payload, {
    headers: {
      "Content-Type": "application/json",
    },
  });

  const success = check(response, {
    "status is 200": (r) => r.status === 200,
    "response time < 2s": (r) => r.timings.duration < 2000,
  });

  errorRate.add(!success);
  mcpLatency.add(response.timings.duration / 1000); // Convert to seconds

  sleep(1); // Realistic think time
}

// Threshold validation
export function handleSummary(data) {
  const p95Duration = data.metrics.http_req_duration.values["p(95)"];
  const errorRateValue = data.metrics.errors.values.rate;

  return {
    stdout: `
Performance Test Results:
- P95 request duration: ${
      p95Duration < 2000 ? "✅ PASS" : "❌ FAIL"
    } (${p95Duration.toFixed(2)}ms / 2000ms threshold)
- Error rate: ${errorRateValue < 0.01 ? "✅ PASS" : "❌ FAIL"} (${(
      errorRateValue * 100
    ).toFixed(2)}% / 1% threshold)
    `,
    "summary.json": JSON.stringify(data),
  };
}
```

**Baseline Unit Tests:**

```python
# tests/unit/test_performance_baselines.py
import pytest
import time
from ingestion.embedder import generate_embedding_batch

@pytest.mark.performance
async def test_embedding_generation_baseline():
    """NFR-P2: Embedding generation < 500ms for 100 chunks."""
    chunks = [f"chunk {i}" for i in range(100)]

    start_time = time.time()
    embeddings = await generate_embedding_batch(chunks)
    duration = (time.time() - start_time) * 1000  # Convert to ms

    assert duration < 500, f"Embedding generation took {duration:.2f}ms, exceeds 500ms threshold"
    assert len(embeddings) == 100

@pytest.mark.performance
async def test_db_search_baseline(db_pool):
    """NFR-P3: DB vector search < 100ms."""
    query_embedding = [0.1] * 1536  # Mock embedding

    start_time = time.time()
    results = await search_vector_db(query_embedding, limit=5)
    duration = (time.time() - start_time) * 1000  # Convert to ms

    assert duration < 100, f"DB search took {duration:.2f}ms, exceeds 100ms threshold"
    assert len(results) <= 5
```

**CI/CD Integration:**

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  schedule:
    - cron: "0 2 * * *" # Daily at 2 AM
  workflow_dispatch:

jobs:
  k6-load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6

      - name: Run k6 load test
        env:
          MCP_SERVER_URL: ${{ secrets.MCP_SERVER_URL }}
        run: |
          k6 run tests/performance/mcp_load_test.k6.js
```

**Risk Score:** 6 (PERF, Probability: 2, Impact: 3) - High Priority

**Owner:** DevOps/QA Team  
**Timeline:** Epic 5 completion (Story 5.3)  
**Status:** Planned

**References:**

- [k6 Documentation](https://k6.io/docs/)
- [k6 Thresholds](https://k6.io/docs/using-k6/thresholds/)
- [Prometheus Integration with k6](https://k6.io/docs/results-output/real-time/prometheus/)

---

### Concern-003: Prometheus Metrics Endpoint Not Documented

**Description:** PRD menziona `/metrics` endpoint (FR11) ma architecture non documenta implementazione.

**Impact:** Medium - Impossibile validare real-time metrics senza endpoint.

**Mitigation:**

- **Implement `/metrics`**: Prometheus format con latency histograms
- **Documentation**: Architecture update con endpoint details
- **Tests**: Validare metrics format e content

**Implementazione Dettagliata:**

```python
# api/metrics.py - Complete implementation
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, REGISTRY
)
from fastapi import Response
import time

# Custom registry (optional, for isolation)
metrics_registry = CollectorRegistry()

# MCP-specific metrics
MCP_REQUESTS_TOTAL = Counter(
    'mcp_requests_total',
    'Total MCP requests',
    ['tool_name', 'status'],
    registry=metrics_registry
)

MCP_REQUEST_DURATION = Histogram(
    'mcp_request_duration_seconds',
    'MCP request duration',
    ['tool_name'],
    buckets=[0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0],
    registry=metrics_registry
)

RAG_EMBEDDING_TIME = Histogram(
    'rag_embedding_time_seconds',
    'Embedding generation time',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 1.0],
    registry=metrics_registry
)

RAG_DB_SEARCH_TIME = Histogram(
    'rag_db_search_time_seconds',
    'Database vector search time',
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0],
    registry=metrics_registry
)

RAG_LLM_GENERATION_TIME = Histogram(
    'rag_llm_generation_time_seconds',
    'LLM response generation time',
    buckets=[0.5, 1.0, 1.5, 2.0, 3.0, 5.0],
    registry=metrics_registry
)

MCP_ACTIVE_REQUESTS = Gauge(
    'mcp_active_requests',
    'Number of active MCP requests',
    registry=metrics_registry
)

# FastAPI endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(metrics_registry),
        media_type=CONTENT_TYPE_LATEST
    )
```

**Testing Metrics Endpoint:**

```python
# tests/integration/test_metrics.py
async def test_metrics_endpoint_format(api_client):
    """Test /metrics endpoint returns Prometheus format."""
    response = await api_client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == CONTENT_TYPE_LATEST

    content = response.text
    # Verify Prometheus format
    assert "# HELP" in content
    assert "# TYPE" in content
    assert "mcp_requests_total" in content

async def test_metrics_after_request(api_client, mcp_client):
    """Test metrics are updated after MCP request."""
    # Make MCP request
    await mcp_client.call_tool("query_knowledge_base", {"query": "test"})

    # Check metrics
    response = await api_client.get("/metrics")
    content = response.text

    # Verify metrics were recorded
    assert 'mcp_requests_total{tool_name="query_knowledge_base"' in content
    assert 'mcp_request_duration_seconds{tool_name="query_knowledge_base"' in content
```

**Risk Score:** 4 (TECH, Probability: 2, Impact: 2) - Medium

**Owner:** Dev Team  
**Timeline:** Epic 2 completion (Story 2.3)  
**Status:** Planned

**References:**

- [Prometheus Python Client Documentation](https://prometheus.io/docs/instrumenting/clientlibs/python/)
- [Prometheus Histograms Best Practices](https://prometheus.io/docs/practices/histograms/)
- [FastAPI Prometheus Integration Examples](https://github.com/trallnag/prometheus-fastapi-instrumentator)

---

## Recommendations for Sprint 0

**Sprint 0 Actions** (prima di iniziare Epic 1):

1. **Setup Test Infrastructure** (`*framework` workflow):

   - Install pytest, pytest-asyncio, pytest-cov, pytest-mock
   - Create `tests/` structure: `unit/`, `integration/`, `e2e/`, `fixtures/`
   - Setup `conftest.py` con shared fixtures
   - Configure pytest.ini con coverage threshold > 70%

2. **Setup Test Database**:

   - Create test database (PostgreSQL + PGVector)
   - Setup schema migration per test isolation
   - Create test fixtures per data seeding

3. **Setup CI/CD Test Pipeline** (`*ci` workflow):

   - GitHub Actions workflow per test execution
   - Coverage reporting automatico
   - Fail build se coverage < 70%

4. **Setup Performance Test Infrastructure**:

   - Install k6
   - Create k6 load test scripts per latency validation
   - Setup baseline measurements per embedding/DB operations

5. **Document Test Strategy**:
   - Update architecture.md con test environment details
   - Document test data factories e fixtures
   - Create test setup guide

**Priority Order:**

1. **Test Infrastructure** (Sprint 0, Week 1) - Blocker per Epic 5
2. **Test Database** (Sprint 0, Week 1) - Blocker per integration tests
3. **CI/CD Pipeline** (Sprint 0, Week 1) - Blocker per Epic 4
4. **Performance Infrastructure** (Sprint 0, Week 2) - Blocker per NFR validation
5. **Documentation** (Sprint 0, Week 2) - Non-blocker ma importante

---

## Risk Summary

| Risk ID     | Category | Description                                        | Score | Status  | Owner         |
| ----------- | -------- | -------------------------------------------------- | ----- | ------- | ------------- |
| ASR-003     | PERF     | Performance targets validation (k6 infrastructure) | 6     | Planned | DevOps/QA     |
| ASR-005     | SEC      | Security requirements validation (secret scanning) | 6     | Planned | Security Team |
| Concern-002 | PERF     | Performance test infrastructure missing            | 6     | Planned | DevOps/QA     |
| Concern-003 | TECH     | Prometheus metrics endpoint not documented         | 4     | Planned | Dev Team      |
| ASR-002     | TECH     | MCP server standalone testing                      | 4     | Planned | Dev Team      |
| Concern-001 | TECH     | MCP server standalone testing infrastructure       | 3     | Planned | Dev Team      |
| ASR-001     | TECH     | LangFuse observability integration                 | 3     | Planned | Dev Team      |
| ASR-004     | TECH     | TDD structure rigorosa                             | 3     | Planned | Dev Team      |

**Total Risks:** 8  
**High-Priority (≥6):** 3  
**Medium-Priority (3-4):** 5  
**Low-Priority (1-2):** 0

---

## Gate Decision

**Overall Assessment:** ✅ **PASS WITH CONCERNS**

**Rationale:**

- ✅ Controllabilità: PASS - API seeding, dependency injection, mockable boundaries
- ⚠️ Osservabilità: CONCERNS - LangFuse integrato ma mancano metriche Prometheus complete
- ✅ Affidabilità: PASS - Test isolation, cleanup discipline, deterministic waits
- ⚠️ Testability Concerns: 3 concerns identificati con mitigation plans definiti

**Gate Criteria:**

- ✅ No critical blockers (score = 9)
- ⚠️ High-priority risks (score ≥6) con mitigation plans definiti
- ✅ Test levels strategy definita (60/25/15 split)
- ✅ NFR testing approach documentato
- ✅ Sprint 0 recommendations chiare

**Recommendation:** **PROCEED TO IMPLEMENTATION** con condizioni:

1. **Sprint 0 Actions**: Completare test infrastructure setup prima di Epic 1
2. **High-Priority Risks**: Mitigare ASR-003, ASR-005, Concern-002 durante Epic 2-5
3. **Medium-Priority Risks**: Mitigare durante Epic 2-4 come planned

**Next Steps:**

1. Eseguire `*framework` workflow per setup test infrastructure
2. Eseguire `*ci` workflow per CI/CD pipeline setup
3. Procedere con Epic 1 (Core RAG Baseline & Documentation)

---

## Appendix

### Knowledge Base References

- `nfr-criteria.md` - NFR validation approach (security, performance, reliability, maintainability)
- `test-levels-framework.md` - Test levels strategy guidance (E2E vs API vs Component vs Unit)
- `risk-governance.md` - Testability risk identification (6 categories: TECH, SEC, PERF, DATA, BUS, OPS)
- `test-quality.md` - Quality standards e Definition of Done

### External References

- [Prometheus Overview](https://prometheus.io/docs/introduction/overview/) - Architecture, pull model, time series data model
- [Prometheus Data Model](https://prometheus.io/docs/concepts/data_model/) - Time series, labels, metric types
- [Prometheus Metric Naming](https://prometheus.io/docs/practices/naming/) - Best practices per naming e labels
- [Prometheus Python Client](https://prometheus.io/docs/instrumenting/clientlibs/python/) - Python client library
- [Prometheus Histograms Best Practices](https://prometheus.io/docs/practices/histograms/) - Histogram configuration
- [FastMCP Testing Guide](https://gofastmcp.com/development/tests.md) - FastMCP testing patterns
- [FastMCP Context](https://gofastmcp.com/servers/context.md) - MCP context injection patterns
- [k6 Documentation](https://k6.io/docs/) - Load testing tool
- [FastAPI Health Checks](https://github.com/Kludex/fastapi-health) - Health check patterns

### Related Documents

- PRD: `docs/prd.md`
- Architecture: `docs/architecture.md`
- Epics: `docs/epics.md`
- Implementation Readiness: `docs/implementation-readiness-report-2025-11-26-updated.md`

---

**Generated by**: BMad TEA Agent - Test Architect Module  
**Workflow**: `.bmad/bmm/testarch/test-design`  
**Version**: 4.0 (BMad v6)  
**Mode**: System-Level (Phase 3)
