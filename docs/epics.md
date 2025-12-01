# docling-rag-agent - Epic Breakdown

**Author:** Stefano  
**Date:** 2025-11-24  
**Updated:** 2025-11-26  
**Project Level:** Brownfield Enhancement  
**Target Scale:** Production-Ready MVP

---

## Overview

This document provides the complete epic and story breakdown for `docling-rag-agent`, decomposing the requirements from the [PRD](./prd.md) into implementable stories. The primary goal is to transform the system into a production-ready RAG agent with comprehensive LangFuse monitoring, cost tracking, and GitHub deployment readiness.

**Living Document Notice:** This is the initial version. It will be updated after Architecture workflow adds technical implementation details.

---

## Functional Requirements Inventory

### Core RAG Capabilities

- **FR1:** Ingestione documenti multi-formato via Docling
- **FR2:** Generazione embeddings vettoriali (1536 dim)
- **FR3:** Storage PostgreSQL + PGVector
- **FR4:** Ricerca semantica (cosine similarity)
- **FR5:** Risposte RAG con citazioni fonti
- **FR6:** Filtraggio per fonte documentale

### MCP Server Observability

- **FR7:** Tracking chiamate `query_knowledge_base`
- **FR8:** Calcolo costo per query
- **FR9:** Trace LangFuse per operazioni MCP
- **FR10:** Breakdown timing (embedding, DB, LLM)
- **FR11:** Endpoint `/metrics` real-time
- **FR12:** Logging errori con stack trace

### MCP Server Architecture & Fix

- **FR12.1:** MCP server usa direttamente `core/rag_service.py` senza dipendenza API esterna
- **FR12.2:** MCP server standalone senza `api/main.py` richiesto
- **FR12.3:** MCP server organizzato in modulo `mcp/` con tools separati per dominio
- **FR12.4:** MCP server implementa pattern FastMCP nativi (lifespan, context injection)
- **FR12.5:** Tutti i tool e prompt MCP funzionano correttamente senza errori
- **FR12.6:** Gestione errori con messaggi informativi e graceful degradation

### Streamlit UI Observability

- **FR13:** Session tracking con session_id
- **FR14:** Registrazione query utente
- **FR15:** Calcolo costi per sessione
- **FR16:** Statistiche sidebar

### Cost Tracking & Analytics

- **FR17:** Calcolo costo per token
- **FR18:** Aggregazione costi (daily/monthly)
- **FR19:** Export report CSV/JSON
- **FR20:** Dashboard LangFuse

### Production Infrastructure

- **FR21:** Linting (ruff) senza warning
- **FR22:** Type checking (mypy) senza errori
- **FR23:** Health check endpoints
- **FR24:** Docker deployment
- **FR25:** GitHub Actions CI/CD

### Documentation & Developer Experience

- **FR26:** README con setup < 5 min
- **FR27:** API documentation auto-generata
- **FR28:** Guida monitoring setup
- **FR29:** Esempi query con costi
- **FR30:** Badge GitHub
- **FR30.1:** Documentazione centralizzata in `docs/` senza file markdown sparsi
- **FR30.2:** Troubleshooting guide completa per MCP server
- **FR30.3:** Guida struttura progetto e organizzazione codice

### Testing & Quality Assurance (TDD)

- **FR31:** Unit tests con coverage > 70%
- **FR32:** PydanticAI TestModel per LLM mocking
- **FR33:** RAGAS evaluation suite
- **FR34:** Playwright E2E tests
- **FR35:** Integration tests MCP
- **FR36:** Tests in CI/CD
- **FR37:** Coverage report pubblicato
- **FR38:** Test fixtures database
- **FR39:** Golden dataset RAGAS (20+ pairs)
- **FR40:** Test results in LangFuse

### TDD Structure & Organization

- **FR41:** Test suite organizzata rigorosamente in `tests/unit/`, `tests/integration/`, `tests/e2e/`
- **FR42:** Test fixtures in `tests/fixtures/` con golden dataset per RAGAS
- **FR43:** Test seguono pattern Red-Green-Refactor rigoroso (test prima del codice)
- **FR44:** Coverage report generato automaticamente in CI/CD con threshold > 70%

### Project Structure & Organization

- **FR45:** Progetto segue struttura directory rigorosa senza file sparsi in root
- **FR46:** Tutti i file markdown in `docs/` (eccetto README.md root)
- **FR47:** Tutti gli script organizzati in `scripts/` con sottodirectory per categoria
- **FR48:** Codice organizzato per responsabilità (mcp/, core/, ingestion/, utils/, api/)
- **FR49:** Zero file temporanei o di debug in root directory

---

## FR Coverage Map

| Epic   | Stories                 | FRs Covered                        |
| ------ | ----------------------- | ---------------------------------- |
| Epic 1 | 1.1, 1.2, 1.3, 1.4      | FR1-FR6, FR26-FR30, FR30.1-FR30.3  |
| Epic 2 | 2.1, 2.2, 2.3, 2.4, 2.5 | FR7-FR12, FR12.1-FR12.6, FR17-FR20 |
| Epic 3 | 3.1, 3.2                | FR13-FR16                          |
| Epic 4 | 4.1, 4.2, 4.3           | FR21-FR25                          |
| Epic 5 | 5.1, 5.2, 5.3, 5.4      | FR31-FR40, FR41-FR44               |
| Epic 6 | 6.1, 6.2                | FR45-FR49                          |

---

## Epic 1: Core RAG Baseline & Documentation

**Goal:** Stabilire la baseline documentale del sistema esistente e creare fondamenta per monitoring. Questo epic fornisce l'infrastruttura di base (documentazione + API reference) necessaria per gli epic successivi.

**Why Foundation:** Senza documentazione completa e API reference, l'implementazione di monitoring (Epic 2) sarebbe difficile da validare. Questo epic crea la "single source of truth" per il sistema.

### Story 1.1: Document Current Architecture

As a developer,  
I want comprehensive documentation of the existing RAG architecture,  
So that I can understand the system before adding monitoring.

**Acceptance Criteria:**

- **Given** the current codebase, **When** I read `docs/architecture.md`, **Then** it accurately reflects all components (core, ingestion, utils, MCP, Streamlit)
- **Given** the architecture doc, **When** I review data flows, **Then** I see complete diagrams for ingestion and query pipelines
- **Given** the architecture doc, **When** I check component descriptions, **Then** each module has clear responsibilities documented

**Prerequisites:** None (foundation story)

**Technical Notes:** Update existing `docs/architecture.md` to reflect current state post-audio removal. Include MCP server architecture.

---

### Story 1.2: Generate API Reference Documentation

As a developer,  
I want auto-generated API documentation for all public functions,  
So that I can quickly understand how to use and extend the system.

**Acceptance Criteria:**

- **Given** the codebase, **When** I run documentation generation, **Then** all public functions in `core/`, `ingestion/`, `utils/` have docstrings
- **Given** the generated docs, **When** I search for a function, **Then** I find parameters, return types, and usage examples
- **Given** the API docs, **When** I deploy them, **Then** they are accessible via GitHub Pages or local server

**Prerequisites:** Story 1.1 (architecture understanding)

**Technical Notes:** Use Sphinx or MkDocs. Configure auto-build in GitHub Actions.

---

### Story 1.3: Create Production-Ready README

As a new developer,  
I want to setup the project locally in < 5 minutes,  
So that I can start contributing immediately.

**Acceptance Criteria:**

- **Given** the README, **When** I follow setup instructions, **Then** I have a working local environment in < 5 minutes
- **Given** the README, **When** I check prerequisites, **Then** all required tools are listed with version numbers
- **Given** the README, **When** I view the top, **Then** I see GitHub badges (build status, coverage, version)

**Prerequisites:** Story 1.1, 1.2 (docs complete)

**Technical Notes:** Include quick start, Docker setup, troubleshooting section. Add shields.io badges.

---

### Story 1.4: Centralize Documentation and Add Troubleshooting Guide

As a developer,  
I want all documentation centralized in `docs/` with a complete troubleshooting guide,  
So that I can quickly find information and resolve issues.

**Acceptance Criteria:**

- **Given** the project root, **When** I check for markdown files, **Then** all `.md` files are in `docs/` (except README.md)
- **Given** the documentation, **When** I look for troubleshooting, **Then** I find complete troubleshooting guide for MCP server issues
- **Given** the documentation, **When** I check project structure, **Then** I find guide explaining directory organization and code structure
- **Given** scattered documentation files, **When** I review them, **Then** they are integrated into appropriate guides in `docs/`

**Prerequisites:** Story 1.1, 1.2, 1.3 (baseline docs complete)

**Technical Notes:**

- Move all root-level `.md` files (except README.md) to `guide/`
- Integrate content from: `flusso-mcp-tool.md`, `mat-FastMCP-e-architecture.md`, `MCP_TROUBLESHOOTING.md`, `pydantic_ai_testing_reference.md`, `walkthrough.md`
- Create `guide/troubleshooting-guide.md` with MCP server troubleshooting section
- Add project structure guide to `guide/development-guide.md`
- **Note:** `docs/` directory is reserved for BMAD workflow documentation

**FRs Covered:** FR30.1, FR30.2, FR30.3

---

## Epic 2: MCP Server Observability (LangFuse)

**Goal:** Implementare monitoring completo per MCP server usando LangFuse, con cost tracking granulare e performance metrics real-time.

**Why Critical:** MCP server è l'interfaccia primaria per workflow production. Senza monitoring, impossibile ottimizzare costi o diagnosticare problemi.

### Story 2.1: Integrate LangFuse SDK

As a developer,  
I want LangFuse integrated in the MCP server,  
So that all operations are automatically traced.

**Acceptance Criteria:**

- **Given** `mcp_server.py`, **When** I start the server, **Then** LangFuse client is initialized with API key from env
- **Given** a query, **When** `query_knowledge_base` is called, **Then** a new trace is created in LangFuse
- **Given** LangFuse dashboard, **When** I view traces, **Then** I see all MCP queries with timestamps

**Prerequisites:** Story 1.1 (architecture understanding)

**Technical Notes:** Use `langfuse` Python SDK. Configure via `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` env vars.

---

### Story 2.2: Implement Cost Tracking

As a product owner,  
I want to know the exact cost of each MCP query,  
So that I can budget and optimize spending.

**Acceptance Criteria:**

- **Given** a query, **When** embeddings are generated, **Then** input tokens are counted and cost calculated
- **Given** a query, **When** LLM generates response, **Then** input/output tokens are counted and cost calculated
- **Given** LangFuse trace, **When** I view it, **Then** I see total cost breakdown (embedding + generation)

**Prerequisites:** Story 2.1 (LangFuse integrated)

**Technical Notes:** Use OpenAI pricing: `text-embedding-3-small` = $0.00002/1K tokens, `gpt-4o-mini` = $0.00015/1K input, $0.0006/1K output.

---

### Story 2.3: Add Performance Metrics

As a developer,  
I want detailed timing breakdown for each query,  
So that I can identify performance bottlenecks.

**Acceptance Criteria:**

- **Given** a query, **When** it completes, **Then** I see timing for: embedding_time, db_search_time, llm_generation_time
- **Given** LangFuse trace, **When** I view spans, **Then** each component (embedder, DB, LLM) has separate span with duration
- **Given** metrics endpoint, **When** I query `/metrics`, **Then** I see Prometheus-format metrics (latency histograms, request count)

**Prerequisites:** Story 2.1 (LangFuse integrated)

**Technical Notes:** Use LangFuse spans for hierarchical timing. Add `prometheus_client` for `/metrics` endpoint.

---

### Story 2.4: Create LangFuse Dashboard

As a product owner,  
I want a real-time dashboard showing MCP performance and costs,  
So that I can monitor the system without technical knowledge.

**Acceptance Criteria:**

- **Given** LangFuse UI, **When** I open the dashboard, **Then** I see: total queries, avg latency, total cost (today/week/month)
- **Given** the dashboard, **When** I filter by date range, **Then** I see cost trends over time
- **Given** the dashboard, **When** I click a trace, **Then** I see full query details (input, output, cost, timing)

**Prerequisites:** Story 2.1, 2.2, 2.3 (all monitoring implemented)

**Technical Notes:** Configure LangFuse dashboard views. Create custom charts for cost trends.

---

### Story 2.5: Refactor MCP Server Architecture (Standalone)

As a developer,  
I want the MCP server to work standalone without requiring an external API server,  
So that it's simpler to deploy and debug.

**Acceptance Criteria:**

- **Given** the MCP server, **When** I start it, **Then** it works without `api/main.py` running
- **Given** the codebase, **When** I check MCP server structure, **Then** it's organized in `mcp/` module with tools separated by domain (search, documents, overview)
- **Given** the MCP server, **When** I inspect it, **Then** it uses `core/rag_service.py` directly instead of `client/api_client.py`
- **Given** the MCP server, **When** I check implementation, **Then** it uses FastMCP native patterns (lifespan management, context injection)
- **Given** all MCP tools, **When** I test them, **Then** `query_knowledge_base`, `list_knowledge_base_documents`, `get_knowledge_base_document`, `get_knowledge_base_overview`, and `ask_knowledge_base` all work correctly without errors
- **Given** an error occurs, **When** the MCP server handles it, **Then** it provides informative error messages and graceful degradation

**Prerequisites:** Story 1.1 (architecture understanding), Story 2.1 (LangFuse integration for tracing refactoring)

**Technical Notes:**

- Create `mcp/` directory structure:
  - `mcp/server.py` - FastMCP instance
  - `mcp/tools/search.py` - query_knowledge_base, ask_knowledge_base
  - `mcp/tools/documents.py` - list_knowledge_base_documents, get_knowledge_base_document
  - `mcp/tools/overview.py` - get_knowledge_base_overview
  - `mcp/lifespan.py` - Server lifecycle management
- Remove dependency on `client/api_client.py`
- Use direct calls to `core/rag_service.py` functions
- Implement FastMCP lifespan pattern for resource initialization
- Add comprehensive error handling with informative messages

**FRs Covered:** FR12.1, FR12.2, FR12.3, FR12.4, FR12.5, FR12.6

---

## Epic 3: Streamlit UI Observability

**Goal:** Estendere monitoring a Streamlit UI con session tracking e cost visibility per utenti. Include security hardening opzionale per prevenire cost explosion e abuse.

**Security Hardening:** Epic 3 include protezioni multi-layer documentate in `docs/stories/3/epic-3-security-hardening-guide.md`:

- Cost protection con threshold enforcement (priorità ALTA)
- Rate limiting per prevenzione abuse (priorità MEDIA)
- Network security (VPN/IP whitelist) (priorità ALTA)
- Streamlit authentication opzionale (priorità BASSA)

**Documentazione Completa:**

- Tech Spec: `docs/stories/3/tech-spec-epic-3.md`
- Security Hardening Guide: `docs/stories/3/epic-3-security-hardening-guide.md`
- Setup Guide: `docs/stories/3/epic-3-setup-guide.md`

### Story 3.1: Implement Session Tracking

As a Streamlit user,  
I want to see my session statistics in the sidebar,  
So that I know how many queries I've made and their total cost.

**Acceptance Criteria:**

- **Given** a Streamlit session, **When** I open the app, **Then** a unique session_id is generated
- **Given** a query, **When** I submit it, **Then** it's logged with session_id, timestamp, and cost
- **Given** the sidebar, **When** I view it, **Then** I see: query count, total cost, avg latency for current session
- **Given** PostgreSQL, **When** session is initialized, **Then** record is created in `sessions` table with RLS protection
- **Given** a query, **When** it's processed, **Then** it's logged in `query_logs` table with cost and latency

**Prerequisites:** Story 2.2 (cost tracking logic)

**Technical Notes:**

- Use `st.session_state` for session_id persistence
- Store session data in PostgreSQL (`sessions` and `query_logs` tables)
- RLS enabled on all tables (service_role only access)
- Modules: `utils/session_manager.py` for session management

**Security Considerations:**

- RLS Supabase protects database access
- Cost monitoring optional via `utils/cost_monitor.py` (see Security Hardening Guide)

---

### Story 3.2: Add LangFuse Tracing to Streamlit

As a developer,  
I want Streamlit queries traced in LangFuse,  
So that I can compare MCP and UI performance.

**Acceptance Criteria:**

- **Given** a Streamlit query, **When** it's processed, **Then** a LangFuse trace is created with session_id
- **Given** LangFuse dashboard, **When** I filter by source, **Then** I can separate MCP vs Streamlit queries
- **Given** a trace, **When** I view metadata, **Then** I see: user_agent, session_id, query_text
- **Given** LangFuse context injection, **When** trace is created, **Then** session_id propagates to all nested spans

**Prerequisites:** Story 2.1 (LangFuse SDK), Story 3.1 (session tracking)

**Technical Notes:**

- Tag traces with `source: streamlit` metadata
- Module: `utils/langfuse_streamlit.py` for context injection
- Graceful degradation if LangFuse unavailable

---

## Epic 4: Production Infrastructure & CI/CD

**Goal:** Preparare il sistema per deployment GitHub con CI/CD, health checks, e quality gates.

### Story 4.1: Setup GitHub Actions CI/CD

As a developer,  
I want automated testing and linting on every push,  
So that code quality is maintained automatically.

**Acceptance Criteria:**

- **Given** a push to main, **When** GitHub Actions runs, **Then** all tests pass
- **Given** the CI pipeline, **When** it runs, **Then** ruff linting passes with zero warnings
- **Given** the CI pipeline, **When** it runs, **Then** mypy type checking passes with zero errors

**Prerequisites:** Story 1.3 (README with setup)

**Technical Notes:** Create `.github/workflows/ci.yml`. Run: `ruff check`, `mypy`, `pytest`.

---

### Story 4.2: Add Health Check Endpoints

As a DevOps engineer,  
I want health check endpoints for all services,  
So that I can monitor system status in production.

**Acceptance Criteria:**

- **Given** MCP server, **When** I query `/health`, **Then** I get JSON response with status: ok/degraded/down
- **Given** Streamlit app, **When** I query `/_stcore/health`, **Then** I get 200 OK
- **Given** PostgreSQL, **When** health check runs, **Then** connection is verified

**Prerequisites:** None (infrastructure story)

**Technical Notes:** Add FastAPI `/health` endpoint to MCP server. Check DB connection, LangFuse connectivity.

---

### Story 4.3: Optimize Docker Images

As a DevOps engineer,  
I want Docker images < 500MB,  
So that deployment is fast and cost-effective.

**Acceptance Criteria:**

- **Given** Dockerfile, **When** I build it, **Then** final image size is < 500MB
- **Given** docker-compose, **When** I run it, **Then** all services start in < 30 seconds
- **Given** the images, **When** I inspect layers, **Then** I see multi-stage build optimization

**Prerequisites:** Story 4.2 (health checks for validation)

**Technical Notes:** Use multi-stage builds. Base image: `python:3.11-slim`. Remove build dependencies in final stage.

---

## Epic 5: Testing & Quality Assurance (TDD)

**Goal:** Implementare Test-Driven Development con suite completa di unit tests, RAG evaluation, e E2E tests per garantire qualità production-ready.

**Why Critical:** Senza testing robusto, impossibile validare monitoring accuracy, prevent regressions, o garantire RAG quality. TDD assicura che ogni feature sia testabile e testata.

### Story 5.1: Setup Testing Infrastructure with TDD Structure

As a developer,  
I want a complete testing infrastructure with rigorous TDD structure and pytest fixtures,  
So that I can write and run tests efficiently following Red-Green-Refactor pattern.

**Acceptance Criteria:**

- **Given** the project, **When** I run `pytest`, **Then** all tests are discovered and executed
- **Given** `tests/` directory, **When** I inspect it, **Then** I see rigorous organization: `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`
- **Given** `tests/fixtures/`, **When** I check it, **Then** I see golden dataset for RAGAS evaluation (20+ query-answer pairs)
- **Given** pytest config, **When** I check it, **Then** I see async support, coverage tracking with threshold > 70%, and markers configured
- **Given** CI/CD pipeline, **When** it runs, **Then** coverage report is generated automatically and build fails if coverage < 70%
- **Given** test workflow, **When** I follow TDD, **Then** I write test first (Red), implement code (Green), then refactor (Refactor)

**Prerequisites:** None (foundation story)

**Technical Notes:**

- Install `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-mock`
- Create `conftest.py` with shared fixtures
- Organize tests rigorously: `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`
- Create `tests/fixtures/golden_dataset.json` with 20+ query-answer pairs for RAGAS
- Configure pytest.ini with coverage threshold > 70%
- Setup CI/CD to generate coverage report and fail build if threshold not met

**FRs Covered:** FR31, FR38, FR39, FR41, FR42, FR43, FR44

---

### Story 5.2: Implement Unit Tests with TDD

As a developer,  
I want unit tests for all core modules using PydanticAI TestModel,  
So that I can validate logic without API costs.

**Acceptance Criteria:**

- **Given** `core/rag_service.py`, **When** I run unit tests, **Then** all functions are tested with mocked LLM
  - **Nota:** Se contiene PydanticAI Agent, usare TestModel con `agent.override(model=TestModel())`. Per altre funzioni, usare mock appropriati.
- **Given** `ingestion/embedder.py`, **When** I run tests, **Then** embedding logic is validated with mocked OpenAI client
  - **Nota:** TestModel è solo per PydanticAI Agent, non per EmbeddingGenerator. Per EmbeddingGenerator usare `pytest-mock` `mocker` fixture per mockare `LangfuseAsyncOpenAI` client.
- **Given** coverage report, **When** I check it, **Then** core modules have > 70% coverage

**Prerequisites:** Story 5.1 (testing infrastructure)

**Technical Notes:** Use `PydanticAI.TestModel` for LLM mocking. Set `ALLOW_MODEL_REQUESTS=False` in tests.

---

### Story 5.3: Implement RAGAS Evaluation Suite

As a product owner,  
I want RAGAS metrics to validate RAG quality,  
So that I can ensure high-quality responses.

**Acceptance Criteria:**

- **Given** golden dataset (20+ query-answer pairs), **When** I run RAGAS eval, **Then** I see faithfulness, relevancy, precision, recall scores
- **Given** RAGAS results, **When** I check thresholds, **Then** faithfulness > 0.85 and relevancy > 0.80
- **Given** LangFuse, **When** I view eval results, **Then** I see RAGAS metrics tracked over time

**Prerequisites:** Story 2.1 (LangFuse integration)

**Technical Notes:** Install `ragas`. Create `tests/golden_dataset.json`. Integrate with LangFuse for tracking.

---

### Story 5.4: Implement Playwright E2E Tests

As a QA engineer,  
I want E2E tests for critical Streamlit workflows,  
So that I can validate user experience.

**Acceptance Criteria:**

- **Given** Streamlit app running, **When** Playwright test runs, **Then** it simulates user query and validates response
- **Given** E2E test, **When** it completes, **Then** I see screenshot/video recording for debugging
- **Given** CI/CD, **When** tests run, **Then** E2E tests execute in headless mode

**Prerequisites:** Story 3.1 (Streamlit session tracking)

**Technical Notes:** Install `playwright`. Create `tests/e2e/test_streamlit_workflow.py`. Use `data-testid` selectors.

---

## Epic 6: Project Structure Refactoring & Organization

**Goal:** Implementare struttura directory rigorosa eliminando file sparsi e organizzando codice per responsabilità, seguendo best practices FastMCP e TDD.

**Why Critical:** Struttura rigorosa è fondamentale per mantenibilità, testabilità, e scalabilità. File sparsi creano confusione e rendono difficile onboarding nuovi sviluppatori.

### Story 6.1: Reorganize Project Structure

As a developer,  
I want a rigorous directory structure without scattered files in root,  
So that the project is maintainable and easy to navigate.

**Acceptance Criteria:**

- **Given** the project root, **When** I check for files, **Then** no markdown files exist except README.md
- **Given** the project root, **When** I check for Python files, **Then** no temporary or debug files exist (temp_query.py, debug_mcp_tools.py removed or moved)
- **Given** the scripts directory, **When** I inspect it, **Then** scripts are organized in subdirectories: `scripts/verification/`, `scripts/debug/`
- **Given** the codebase, **When** I check organization, **Then** code is organized by responsibility: `mcp/`, `core/`, `ingestion/`, `utils/`, `api/`
- **Given** the MCP server, **When** I check location, **Then** it's in `mcp/` module, not root

**Prerequisites:** Story 1.4 (documentation centralized), Story 2.5 (MCP server refactored)

**Technical Notes:**

- Remove `temp_query.py` from root
- Move `debug_mcp_tools.py` to `scripts/debug/` or remove
- Move `mcp_server.py` to `mcp/server.py` (if not already done in Story 2.5)
- Reorganize scripts: `scripts/verify_*.py` → `scripts/verification/`
- Move `scripts/test_mcp_performance.py` to `tests/performance/` or keep in scripts if it's a utility
- Ensure zero temporary files in root

**FRs Covered:** FR45, FR46, FR47, FR48, FR49

---

### Story 6.2: Clean Up and Validate Structure

As a developer,  
I want to verify that the project structure is rigorous and complete,  
So that I can confidently proceed with implementation.

**Acceptance Criteria:**

- **Given** the project structure, **When** I validate it, **Then** all files are in appropriate directories
- **Given** the root directory, **When** I check it, **Then** only essential files exist (README.md, pyproject.toml, docker-compose.yml, app.py entry point)
- **Given** the documentation, **When** I check structure guide, **Then** it accurately reflects the new organization
- **Given** the codebase, **When** I check imports, **Then** all imports work correctly after reorganization

**Prerequisites:** Story 6.1 (structure reorganized)

**Technical Notes:**

- Run import validation: `python -m py_compile` on all modules
- Update any hardcoded paths in scripts/docs
- Verify Docker builds still work
- Update CI/CD paths if needed

**FRs Covered:** FR45, FR48, FR49

---

## Summary

This breakdown defines **6 Epics** and **20 Stories** to execute the production-ready transformation.

**Epic Sequence:**

1. **Epic 1** (Foundation) → Establishes documentation baseline
2. **Epic 2** (MCP Monitoring + Architecture Fix) → Core observability + standalone MCP server
3. **Epic 3** (Streamlit Monitoring) → Extends monitoring to UI
4. **Epic 4** (Production Infra) → Deployment readiness
5. **Epic 5** (Testing & QA) → TDD implementation with rigorous structure
6. **Epic 6** (Project Structure) → Rigorous organization and cleanup

**Total FRs Covered:** 49/49 (100%)

**Estimated Timeline:** 7-9 weeks (assuming 1 developer, part-time)

---

_For implementation: Use the `create-story` workflow to generate individual story implementation plans from this epic breakdown._

_This document will be updated after Architecture workflow to incorporate technical design decisions._
