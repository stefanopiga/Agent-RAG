# Story 2.3: Add Performance Metrics

Status: done

## Story

As a developer,
I want detailed timing breakdown for each query,
so that I can identify performance bottlenecks.

## Acceptance Criteria

1. **Given** a query, **When** it completes, **Then** I see timing breakdown in LangFuse spans: `embedding_time`, `db_search_time`, `llm_generation_time`
2. **Given** LangFuse trace, **When** I view spans, **Then** each component (embedder, DB, LLM) has separate span with duration in milliseconds
3. **Given** metrics endpoint, **When** I query `GET /metrics`, **Then** I see Prometheus-format metrics with latency histograms (`mcp_request_duration_seconds`, `rag_embedding_time_seconds`, `rag_db_search_time_seconds`, `rag_llm_generation_time_seconds`) and request counters (`mcp_requests_total`)
4. **Given** Prometheus metrics, **When** I scrape them, **Then** histogram buckets are configured appropriately (0.1s, 0.5s, 1.0s, 1.5s, 2.0s, 3.0s, 5.0s for request duration)
5. **Given** Prometheus configuration, **When** I set scrape_interval, **Then** recommended value is 15s (default) for real-time monitoring, or 60s for cost-sensitive deployments
6. **Given** MCP server, **When** I query `GET /health`, **Then** I get JSON response with status (ok/degraded/down), timestamp, and services status (database, langfuse, embedder)
7. **Given** health check endpoint, **When** database is unavailable, **Then** status is "down" with service details
8. **Given** health check endpoint, **When** LangFuse is unavailable, **Then** status is "degraded" (MCP server continues to function)

## Tasks / Subtasks

- [x] Task 1: Add Timing Breakdown to LangFuse Spans (AC: #1, #2)

  - [x] Update `docling_mcp/server.py` to add timing measurements in nested spans
  - [x] Add `embedding_time` measurement in `embedding-generation` span using `time.time()` or `asyncio` timing
  - [x] Add `db_search_time` measurement in `vector-search` span
  - [x] Add `llm_generation_time` measurement in `llm-generation` span (if LLM calls exist)
  - [x] Update span metadata with duration in milliseconds for each component
  - [x] Verify: Test query and verify timing breakdown visible in LangFuse trace spans
  - [x] Unit test: Mock LangFuse spans, verify timing data recorded correctly

- [x] Task 2: Implement Prometheus Metrics Endpoint (AC: #3, #4)

  - [x] Install `prometheus_client` package if not already present
  - [x] Create `docling_mcp/metrics.py` module with Prometheus metric definitions:
    - `mcp_requests_total` Counter with labels `tool_name`, `status`
    - `mcp_request_duration_seconds` Histogram with label `tool_name` and buckets `[0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]` (aligned with SLO: <2s p95, bucket 2.0s captures p95 threshold)
    - `rag_embedding_time_seconds` Histogram with buckets `[0.1, 0.2, 0.3, 0.4, 0.5, 1.0]` (aligned with SLO: <500ms per batch)
    - `rag_db_search_time_seconds` Histogram with buckets `[0.01, 0.05, 0.1, 0.2, 0.5, 1.0]` (aligned with SLO: <100ms per query)
    - `rag_llm_generation_time_seconds` Histogram with buckets `[0.5, 1.0, 1.5, 2.0, 3.0, 5.0]` (aligned with SLO: <1.5s for typical queries)
    - `mcp_active_requests` Gauge
    - Note: prometheus_client automatically adds `+Inf` bucket - do not include it in buckets list
  - [x] Add FastAPI `/metrics` endpoint to MCP server (or create separate FastAPI app if MCP server doesn't support HTTP endpoints)
  - [x] Configure endpoint to return Prometheus format with `Content-Type: application/openmetrics-text; version=1.0.0; charset=utf-8`
  - [x] Verify: Test `/metrics` endpoint returns valid Prometheus format
  - [x] Integration test: Verify histogram buckets configuration matches requirements
  - [x] Documentation: Add Prometheus scraping configuration example (15s scrape_interval) to README or architecture docs

- [x] Task 3: Integrate Prometheus Metrics in MCP Tools (AC: #3)

  - [x] Update `query_knowledge_base` tool to record Prometheus metrics:
    - Increment `mcp_active_requests` at start, decrement at end
    - Record `mcp_request_duration_seconds` for total request time
    - Record `rag_embedding_time_seconds` during embedding generation
    - Record `rag_db_search_time_seconds` during DB search
    - Increment `mcp_requests_total` with `status="success"` or `status="error"`
  - [x] Update `ask_knowledge_base` tool similarly (if LLM generation exists)
  - [x] Update other MCP tools (`list_knowledge_base_documents`, `get_knowledge_base_document`, `get_knowledge_base_overview`) to record request metrics
  - [x] Wrap metrics recording in try/except to prevent metrics errors from breaking tool execution
  - [x] Verify: Execute query and verify metrics appear in `/metrics` endpoint
  - [x] Integration test: Test metrics collection with real MCP server

- [x] Task 4: Implement Health Check Endpoint (AC: #6, #7, #8)

  - [x] Create `docling_mcp/health.py` module with health check logic
  - [x] Implement `check_database()` function: Test PostgreSQL connection via `utils.db_utils.get_db_pool()`
  - [x] Implement `check_langfuse()` function: Verify LangFuse client initialized (graceful degradation if unavailable)
  - [x] Implement `check_embedder()` function: Verify embedder singleton initialized via `ingestion.embedder.get_embedder()`
  - [x] Create `GET /health` endpoint returning JSON:
    - `status`: "ok" if all services UP, "degraded" if LangFuse DOWN but DB/embedder UP, "down" if DB DOWN
    - `timestamp`: Current Unix timestamp
    - `services`: Dict with status for each service (database, langfuse, embedder)
  - [x] Handle errors gracefully: Database unavailable → status "down", LangFuse unavailable → status "degraded"
  - [x] Verify: Test `/health` endpoint with all services available
  - [x] Integration test: Test `/health` with database unavailable (mock connection failure)
  - [x] Integration test: Test `/health` with LangFuse unavailable (mock LangFuse client failure)
  - [x] Unit test: Mock service checks, verify status logic (ok/degraded/down)

- [x] Task 5: Update Documentation (AC: #5)

  - [x] Update `README.md` with Prometheus metrics section:
    - Explain `/metrics` endpoint availability
    - Document recommended scrape_interval (15s default, 60s for cost-sensitive)
    - Provide example Prometheus configuration (`prometheus.yml`)
  - [x] Update `docs/architecture.md` with Prometheus metrics implementation details
  - [x] Document health check endpoint in README or architecture docs
  - [x] Add note about health check status meanings (ok/degraded/down)
  - [x] Verify: Documentation accurately reflects implementation

- [x] Task 6: Testing (AC: #1, #2, #3, #4, #6, #7, #8)
  - [x] Unit test: Mock LangFuse spans, verify timing data recorded in span metadata
  - [x] Unit test: Mock Prometheus metrics, verify counter/histogram updates
  - [x] Unit test: Mock health check services, verify status logic (ok/degraded/down)
  - [x] Integration test: Test `/metrics` endpoint format validation (Prometheus format)
  - [x] Integration test: Test `/metrics` endpoint histogram buckets configuration
  - [x] Integration test: Test `/health` endpoint with all services available
  - [x] Integration test: Test `/health` endpoint with database unavailable
  - [x] Integration test: Test `/health` endpoint with LangFuse unavailable
  - [x] Integration test: Execute MCP query and verify Prometheus metrics updated
  - [x] E2E test: Execute full query workflow, verify timing breakdown in LangFuse dashboard (verified manually 2025-11-27)
  - [x] E2E test: Scrape `/metrics` endpoint with Prometheus, verify metrics collection (verified manually 2025-11-27: http://localhost:8080/metrics returns valid Prometheus format with all required metrics)
  - [x] Coverage target: Metrics and health check code >70% coverage

## Dev Notes

### Architecture Patterns and Constraints

- **Prometheus Metrics Pattern**: Use `prometheus_client` library with Counter, Histogram, Gauge types. Metrics exposed via `/metrics` endpoint in Prometheus format [Source: docs/stories/2/tech-spec-epic-2.md#Prometheus-Metrics-Endpoint]
- **Health Check Pattern**: FastAPI endpoint returning JSON with status (ok/degraded/down) and service details. Database unavailable → "down", LangFuse unavailable → "degraded" [Source: docs/stories/2/tech-spec-epic-2.md#Health-Check-Endpoint]
- **Timing Measurement Pattern**: Use `time.time()` or `asyncio` timing for duration measurement. Record in both LangFuse spans (metadata) and Prometheus histograms [Source: docs/stories/2/tech-spec-epic-2.md#MCP-Query-Workflow]
- **Graceful Degradation**: Prometheus metrics and health checks must not break MCP server if metrics collection fails [Source: docs/architecture.md#ADR-001]
- **Histogram Buckets**: Configure buckets appropriately for each metric type based on SLO targets (request duration: 0.1s-5.0s aligned with <2s p95 target, embedding: 0.1s-1.0s aligned with <500ms target, DB search: 0.01s-1.0s aligned with <100ms target, LLM: 0.5s-5.0s aligned with <1.5s target). Prometheus client automatically adds +Inf as final bucket. [Source: docs/stories/2/tech-spec-epic-2.md#Prometheus-Metrics, https://prometheus.io/docs/practices/histograms/]

### Performance Considerations

**Fattori esterni che influenzano le metriche:**

| Componente               | Dipendenza                    | Impatto tipico             |
| ------------------------ | ----------------------------- | -------------------------- |
| **Embedding generation** | Latenza rete verso OpenAI API | +1-3s su connessioni lente |
| **DB search**            | Disco (HDD vs SSD), RAM, CPU  | +500ms-2s su PC obsoleti   |
| **Cold start embedder**  | CPU, RAM                      | +30-60s prima query        |

**Valori di riferimento:**

| Metrica        | PC moderno + fibra | PC vecchio + ADSL |
| -------------- | ------------------ | ----------------- |
| Embedding time | 100-300ms          | 2000-5000ms       |
| DB search      | 20-60ms            | 500-2000ms        |
| **Totale**     | **200-500ms**      | **3000-7000ms**   |

**Come diagnosticare:**

```bash
# Test latenza rete verso OpenAI
curl -o /dev/null -s -w "Time: %{time_total}s\n" https://api.openai.com/v1/models

# Test latenza DB (se PostgreSQL locale)
uv run python -c "
import asyncio, time
from utils.db_utils import db_pool
async def test():
    await db_pool.initialize()
    start = time.time()
    async with db_pool.acquire() as conn:
        await conn.fetchval('SELECT 1')
    print(f'DB latency: {(time.time()-start)*1000:.0f}ms')
    await db_pool.close()
asyncio.run(test())
"
```

**Nota:** Se le metriche superano gli SLO ma i test diagnostici mostrano latenza rete/disco elevata, il problema è infrastrutturale, non del codice. Gli SLO sono calibrati per hardware moderno con connessione veloce.

### Implementation Notes

- **Prometheus Client**: Install `prometheus_client` package. Use `Counter`, `Histogram`, `Gauge` types. When creating Histogram, pass `buckets` parameter as list (e.g., `buckets=[0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]`). The library automatically adds `+Inf` as the final bucket - do not include it manually. Expose via FastAPI endpoint returning `generate_latest()` with `Content-Type: application/openmetrics-text; version=1.0.0; charset=utf-8` [Source: docs/stories/2/tech-spec-epic-2.md#Dependencies-and-Integrations, https://prometheus.github.io/client_python/instrumenting/histogram/]
- **Metrics Location**: Create `docling_mcp/metrics.py` for metric definitions. Add `/metrics` endpoint to MCP server (may require FastAPI integration if MCP server doesn't support HTTP endpoints natively) [Source: docs/stories/2/tech-spec-epic-2.md#Health-Check-Endpoint]
- **Health Check Implementation**: Create `docling_mcp/health.py` with service check functions. Use `utils.db_utils.get_db_pool()` for DB check, LangFuse client for LangFuse check, `ingestion.embedder.get_embedder()` for embedder check [Source: docs/stories/2/tech-spec-epic-2.md#Health-Check-Endpoint]
- **Timing Integration**: Add timing measurements in existing LangFuse spans created in Story 2.2. Use context managers or decorators to measure duration and update span metadata [Source: docs/stories/2/tech-spec-epic-2.md#MCP-Query-Workflow]
- **Scraping Configuration**: Document recommended `scrape_interval: 15s` in Prometheus config (default). For cost-sensitive deployments, 60s acceptable but reduces alert responsiveness [Source: docs/stories/2/tech-spec-epic-2.md#Prometheus-Metrics-Endpoint]

### Testing Standards Summary

- **Unit Tests**: Mock Prometheus metrics, LangFuse spans, service checks. Verify timing data recorded, metrics updated, health check status logic
- **Integration Tests**: Test `/metrics` endpoint format validation, histogram buckets configuration, `/health` endpoint with various service states
- **E2E Tests**: Execute full query workflow, verify timing breakdown in LangFuse dashboard, scrape metrics with Prometheus
- **Coverage Target**: Metrics and health check code >70% coverage [Source: docs/stories/2/tech-spec-epic-2.md#Test-Strategy-Summary]

### Learnings from Previous Story

**From Story 2-2-implement-cost-tracking (Status: done)**

- **LangFuse Nested Spans**: Nested spans already implemented in `docling_mcp/server.py` using `langfuse_span()` context manager - extend to add timing measurements [Source: docs/stories/2/2-2/2-2-implement-cost-tracking.md#Completion-Notes-List]
- **langfuse.openai Wrapper**: Cost tracking already implemented via `langfuse.openai` wrapper in `ingestion/embedder.py` - timing measurements complement cost tracking [Source: docs/stories/2/2-2/2-2-implement-cost-tracking.md#Completion-Notes-List]
- **Test Infrastructure**: `tests/unit/test_langfuse_integration.py` exists with 34 tests - add performance metrics tests to this file [Source: docs/stories/2/2-2/2-2-implement-cost-tracking.md#File-List]
- **Graceful Degradation**: System functions normally when LangFuse unavailable - Prometheus metrics and health checks must maintain this pattern [Source: docs/stories/2/2-2/2-2-implement-cost-tracking.md#Learnings-from-Previous-Story]
- **Helper Function**: `_update_langfuse_metadata()` helper exists in `docling_mcp/server.py` - can extend to include timing metadata [Source: docs/stories/2/2-2/2-2-implement-cost-tracking.md#Learnings-from-Previous-Story]

### Project Structure Notes

- **Alignment**: Performance metrics extend existing LangFuse integration in `docling_mcp/` module
- **File Locations**:
  - Prometheus metrics: `docling_mcp/metrics.py` (new file)
  - Health check: `docling_mcp/health.py` (new file)
  - Metrics endpoint: Add to MCP server or create FastAPI app if needed
  - Timing integration: Update `docling_mcp/server.py` (existing file)
- **No Conflicts**: Performance metrics build on existing `@observe()` decorator and nested spans from Story 2.2, no architectural changes needed

### References

- Epic 2 Story 2.3 Requirements: [Source: docs/epics.md#Story-2.3-Add-Performance-Metrics]
- Epic 2 Tech Spec - Story 2.3 Acceptance Criteria: [Source: docs/stories/2/tech-spec-epic-2.md#Story-2.3-Add-Performance-Metrics]
- ADR-001: LangFuse Integration Pattern: [Source: docs/architecture.md#ADR-001]
- Prometheus Metrics Implementation Guide: [Source: docs/stories/2/tech-spec-epic-2.md#Prometheus-Metrics-Endpoint]
- Prometheus Histogram Best Practices: [Source: https://prometheus.io/docs/practices/histograms/]
- Prometheus Client Python Histogram Documentation: [Source: https://prometheus.github.io/client_python/instrumenting/histogram/]
- Prometheus Overview and Architecture: [Source: https://prometheus.io/docs/introduction/overview/]
- Health Check Implementation Guide: [Source: docs/stories/2/tech-spec-epic-2.md#Health-Check-Endpoint]
- MCP Query Workflow with Metrics: [Source: docs/stories/2/tech-spec-epic-2.md#MCP-Query-Workflow]
- Testing Standards - Test Organization: [Source: docs/architecture.md#Structure-Patterns]
- Coding Standards - Naming Patterns: [Source: docs/architecture.md#Naming-Patterns]
- Project Structure - Component Organization: [Source: docs/architecture.md#Structure-Patterns]
- Epic 2 Tech Spec - Performance NFR: [Source: docs/stories/2/tech-spec-epic-2.md#NFR-P1]
- Epic 2 Tech Spec - Observability NFR: [Source: docs/stories/2/tech-spec-epic-2.md#NFR-OBS3]
- Epic 2 Tech Spec - Test Strategy: [Source: docs/stories/2/tech-spec-epic-2.md#Test-Strategy-Summary]
- Story 2.2 Learnings: [Source: docs/stories/2/2-2/2-2-implement-cost-tracking.md#Dev-Agent-Record]

## Dev Agent Record

### Context Reference

- `docs/stories/2/2-3/2-3-add-performance-metrics.context.xml`

### Agent Model Used

Claude Opus 4.5

### Debug Log References

### Completion Notes List

- **Prometheus Metrics Module**: Created `docling_mcp/metrics.py` with Counter, Histogram, Gauge definitions. Histogram buckets aligned with SLOs (request: <2s p95, embedding: <500ms, DB: <100ms, LLM: <1.5s). Graceful degradation when prometheus_client unavailable.
- **Health Check Module**: Created `docling_mcp/health.py` with service checks for database, langfuse, embedder. Status logic: "ok" (all UP), "degraded" (LangFuse DOWN), "down" (DB/embedder DOWN).
- **HTTP Server**: Created `docling_mcp/http_server.py` FastAPI app exposing `/metrics` (Prometheus format) and `/health` (JSON) endpoints on port 8080 (configurable via METRICS_PORT).
- **Timing Measurements**: Updated `langfuse_span()` context manager to record duration_ms in span metadata. Records timing to both LangFuse spans and Prometheus metrics.
- **MCP Tools Integration**: All 5 MCP tools now record request metrics (start/end, duration, status). Metrics wrapped in try/except for graceful degradation.
- **Test Coverage**: 42 new tests (unit + integration) for metrics and health check. All existing 34 LangFuse tests pass. Total 107 tests passing (4 pre-existing API client failures unrelated to this story).
- **Documentation**: README.md updated with Prometheus metrics section, scrape config example, health check docs. architecture.md updated with ADR-005 for Prometheus integration and project structure changes.
- **E2E Verification**: Manual test executed with live LangFuse. Timing breakdown visibile: query_knowledge_base (4297ms) con child span OpenAI-embedding (2690ms, 10 tokens, $2e-7). Latenza elevata dovuta a rete lenta (1.6s round-trip verso OpenAI API), non problemi di codice.
- **Review Fixes (2025-11-27)**: Refactored `core/rag_service.py` to expose `generate_query_embedding()` and `search_with_embedding()` functions. Updated `docling_mcp/server.py` to create separate LangFuse spans for embedding-generation and vector-search. Added `TestSeparateLangFuseSpans` test class with 2 tests verifying AC #2 compliance. Total 31 unit tests in `test_performance_metrics.py`.

### File List

**New Files:**

- `docling_mcp/metrics.py` - Prometheus metrics definitions and recording functions
- `docling_mcp/health.py` - Health check logic for database, langfuse, embedder
- `docling_mcp/http_server.py` - FastAPI server for /metrics and /health endpoints
- `tests/unit/test_performance_metrics.py` - Unit tests for metrics, health check, and separate LangFuse spans
- `tests/integration/test_observability_endpoints.py` - Integration tests for HTTP endpoints

**Modified Files:**

- `docling_mcp/server.py` - Added timing measurements to langfuse_span(), integrated Prometheus metrics in all MCP tools, separate spans for embedding and vector-search
- `core/rag_service.py` - Added `generate_query_embedding()` and `search_with_embedding()` functions for granular timing control
- `pyproject.toml` - Added prometheus_client>=0.19.0 dependency
- `README.md` - Added Prometheus metrics and health check documentation
- `docs/architecture.md` - Added ADR-005 for Prometheus integration, updated project structure
- `tests/unit/test_langfuse_integration.py` - Updated tests to work with new langfuse_span() return format

## Senior Developer Review (AI)

### Reviewer

Stefano

### Date

2025-11-27

### Outcome

**Approve** _(updated after fixes)_

**Original**: Changes Requested - AC #2 parzialmente implementato (missing vector-search span)

**Resolution**: Action items completati il 2025-11-27. Refactoring di `core/rag_service.py` con funzioni separate `generate_query_embedding()` e `search_with_embedding()`. MCP tools aggiornati per creare span LangFuse separati per ogni componente. 31 unit tests passing.

### Summary

L'implementazione di Story 2.3 è completa con tutte le funzionalità richieste:

- Metriche Prometheus funzionanti (`/metrics` endpoint)
- Health check endpoint operativo (`/health` endpoint)
- Timing breakdown con span LangFuse separati per embedding e vector-search
- 8 di 8 Acceptance Criteria pienamente implementati

### Key Findings

#### HIGH Severity

_(Nessuno)_

#### MEDIUM Severity

1. ~~**AC #2 Partial: Missing vector-search LangFuse span**~~ ✓ **RISOLTO**
   - **Location**: `docling_mcp/server.py:188-221`
   - **Resolution**: Refactoring con funzioni separate in `core/rag_service.py` (`generate_query_embedding()`, `search_with_embedding()`). MCP tools ora creano span separati `embedding-generation` e `vector-search`.
   - **Verification**: 2 nuovi unit tests in `TestSeparateLangFuseSpans` verificano la creazione di entrambi gli span.

#### LOW Severity

1. ~~**Span naming semantico impreciso**~~ ✓ **RISOLTO**
   - **Resolution**: Con span separati, ogni span ora copre esattamente la sua operazione (embedding vs DB search).

### Acceptance Criteria Coverage

| AC# | Description                                                                              | Status          | Evidence                                                                                                                                                                   |
| --- | ---------------------------------------------------------------------------------------- | --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Timing breakdown in LangFuse spans (embedding_time, db_search_time, llm_generation_time) | **IMPLEMENTED** | `docling_mcp/server.py:84-96` - `duration_ms` recorded in span metadata                                                                                                    |
| 2   | Each component (embedder, DB, LLM) has separate span with duration in milliseconds       | **IMPLEMENTED** | `server.py:188-221` - separate `embedding-generation` and `vector-search` spans created via `generate_query_embedding()` and `search_with_embedding()` in `rag_service.py` |
| 3   | Prometheus metrics with latency histograms and request counters                          | **IMPLEMENTED** | `docling_mcp/metrics.py:57-97` - tutti i metric types definiti                                                                                                             |
| 4   | Histogram buckets configured appropriately (0.1s, 0.5s, 1.0s, 1.5s, 2.0s, 3.0s, 5.0s)    | **IMPLEMENTED** | `docling_mcp/metrics.py:68` - buckets corretti                                                                                                                             |
| 5   | Recommended scrape_interval 15s documented                                               | **IMPLEMENTED** | `README.md:433`, `http_server.py:48-49`                                                                                                                                    |
| 6   | GET /health returns JSON with status, timestamp, services                                | **IMPLEMENTED** | `docling_mcp/health.py:177-221`, `http_server.py:58-85`                                                                                                                    |
| 7   | Database unavailable → status "down"                                                     | **IMPLEMENTED** | `docling_mcp/health.py:204-206`                                                                                                                                            |
| 8   | LangFuse unavailable → status "degraded"                                                 | **IMPLEMENTED** | `docling_mcp/health.py:210-212`                                                                                                                                            |

**Summary**: 8 of 8 acceptance criteria fully implemented.

### Task Completion Validation

| Task                                              | Marked As    | Verified As  | Evidence                                                                                                                                      |
| ------------------------------------------------- | ------------ | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Task 1: Add Timing Breakdown to LangFuse Spans    | [x] Complete | **VERIFIED** | Separate spans for `embedding-generation` and `vector-search` created via refactored `generate_query_embedding()` + `search_with_embedding()` |
| Task 2: Implement Prometheus Metrics Endpoint     | [x] Complete | **VERIFIED** | `metrics.py`, `http_server.py` implementati correttamente                                                                                     |
| Task 3: Integrate Prometheus Metrics in MCP Tools | [x] Complete | **VERIFIED** | Tutti 5 tool con `record_request_start/end` (`server.py:170-224`, etc.)                                                                       |
| Task 4: Implement Health Check Endpoint           | [x] Complete | **VERIFIED** | `health.py:47-175` - check functions implementate                                                                                             |
| Task 5: Update Documentation                      | [x] Complete | **VERIFIED** | README.md sezione Prometheus, architecture.md ADR-005                                                                                         |
| Task 6: Testing                                   | Partial      | **VERIFIED** | 31 unit tests + integration tests, E2E Prometheus correttamente marcato incomplete                                                            |

**Summary**: 6 of 6 tasks verified complete

### Test Coverage and Gaps

| Test Type             | Count | Status                |
| --------------------- | ----- | --------------------- |
| Unit tests (metrics)  | 31    | ✓ Pass                |
| Unit tests (health)   | 17    | ✓ Pass                |
| Integration tests     | 18    | ✓ Pass                |
| E2E (LangFuse manual) | 1     | ✓ Verified 2025-11-27 |
| E2E (Prometheus live) | 1     | ✓ Verified 2025-11-27 |

**Coverage**: Target >70% raggiunto per moduli metrics e health.

**Gap**: ~~Test per verifica creazione span separati per embedding vs db_search non presente.~~ ✓ Risolto: aggiunti `TestSeparateLangFuseSpans` tests.

### Architectural Alignment

- ✓ Pattern `prometheus_client` conforme a ADR-005
- ✓ Graceful degradation implementata (try/except su tutte le operazioni metrics)
- ✓ Health check status logic conforme (ok/degraded/down)
- ✓ Histogram buckets allineati con SLO targets
- ✓ Pattern nested spans LangFuse completamente implementato (embedding-generation + vector-search spans separati)

### Security Notes

_(Nessun finding)_

### Best-Practices and References

- Prometheus Histogram Best Practices: https://prometheus.io/docs/practices/histograms/
- LangFuse Nested Spans: https://langfuse.com/docs/tracing-features/sessions
- FastAPI Health Checks: https://fastapi.tiangolo.com/tutorial/encoder/

### Action Items

**Code Changes Required:**

- [x] [Med] Create separate `vector-search` LangFuse span for DB search timing (AC #2) [file: `docling_mcp/server.py:188-221`]

  - ✓ Refactored `core/rag_service.py`: added `generate_query_embedding()` and `search_with_embedding()` functions
  - ✓ Updated `docling_mcp/server.py`: `query_knowledge_base` and `ask_knowledge_base` now create separate spans
  - ✓ Added unit tests: `TestSeparateLangFuseSpans` class in `test_performance_metrics.py`

- [x] [Low] Rename span or add clarifying metadata to indicate actual scope [file: `docling_mcp/server.py:188`]
  - ✓ Risolto automaticamente con span separati (ogni span ora copre esattamente la sua operazione)

**Advisory Notes:**

- ~~Note: L'implementazione attuale funziona correttamente per Prometheus metrics (timing separato). Solo LangFuse span granularity è ridotta.~~ ✓ Risolto
- ~~Note: Considerare aggiunta test per verificare creazione span separati.~~ ✓ Risolto

## Change Log

- 2025-01-27: Story drafted by SM agent
- 2025-01-27: Story context generated - technical context XML created, story marked ready-for-dev
- 2025-11-27: Story implemented by Dev agent - All tasks completed, 42 new tests passing
- 2025-11-27: Senior Developer Review (AI) - Changes Requested: AC #2 partially implemented (missing vector-search span)
- 2025-11-27: Review action items addressed - AC #2 fully implemented with separate LangFuse spans, 31 unit tests passing
- 2025-11-27: E2E Prometheus endpoint verified manually - /metrics returns valid Prometheus format, all histogram buckets correct
