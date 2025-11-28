# docling-rag-agent - Product Requirements Document

**Author:** Stefano  
**Date:** 2025-11-24  
**Updated:** 2025-11-26  
**Version:** 2.1  
**Project Type:** Backend RAG Application (Brownfield Enhancement)

---

## Executive Summary

Il progetto `docling-rag-agent` evolve da prototipo funzionale a **sistema production-ready enterprise-grade** con monitoring completo, cost tracking, e deployment automatizzato su GitHub. L'obiettivo primario è implementare **observability nativa per MCP Server** tramite LangFuse, fornendo visibilità totale su performance, costi, e utilizzo del sistema RAG in produzione.

### What Makes This Special

Un RAG agent **production-ready** con:

- **LangFuse integration nativa** per MCP Server observability
- **Cost tracking granulare** per ogni query (embedding + LLM tokens)
- **Real-time monitoring dashboard** con breakdown latency per componente
- **GitHub-ready deployment** con CI/CD, health checks, e documentazione enterprise

---

## Project Classification

**Technical Type:** Backend RAG Application (Brownfield Enhancement)  
**Domain:** Knowledge Management + Developer Tools  
**Complexity:** Medium-High  
**Track:** BMad Method (Brownfield)

---

## Success Criteria

### 1. MCP Monitoring Coverage

- ✅ 100% delle chiamate `query_knowledge_base` tracciate con timing completo
- ✅ Dashboard LangFuse real-time con metriche chiave
- ✅ Alert automatici per errori o latency anomale (> 3s)

### 2. Cost Tracking Accuracy

- ✅ Costo per sessione MCP calcolato con precisione (embedding + LLM tokens)
- ✅ Breakdown costi: embedding_cost + db_cost + generation_cost
- ✅ Export mensile costi in CSV per analisi budget

### 3. Production Readiness

- ✅ Zero warning nei linter (ruff, mypy)
- ✅ 100% documentazione API aggiornata
- ✅ GitHub Actions CI/CD funzionante (test + lint + build)
- ✅ Docker images ottimizzate (< 500MB)

### 4. Developer Experience

- ✅ Setup locale completato in < 5 minuti
- ✅ Monitoring dashboard accessibile via browser
- ✅ Logs strutturati e ricercabili (JSON format)

### 5. Performance Targets

- ✅ Latency media query MCP < 2 secondi (95th percentile)
- ✅ Embedding generation < 500ms per batch
- ✅ DB vector search < 100ms per query

---

## Product Scope

### MVP - Minimum Viable Product

**Epic 1: Core RAG Baseline Documentation**

- Documentazione completa architettura esistente
- API reference auto-generato
- Deployment guide aggiornato

**Epic 2: MCP Server Observability (LangFuse)**

- LangFuse integration per MCP server
- Cost tracking per `query_knowledge_base`
- Performance metrics (latency, tokens, DB time)
- Real-time dashboard LangFuse

**Epic 3: Streamlit UI Observability**

- Session tracking con session_id univoco
- Cost tracking per sessione utente
- Sidebar con statistiche sessione corrente

**Epic 4: Production Infrastructure**

- GitHub Actions CI/CD pipeline
- Docker optimization (multi-stage builds)
- Health checks per tutti i servizi
- Linting & type checking automatizzato

**Epic 5: Testing & Quality Assurance (TDD)**

- Test infrastructure con pytest e fixtures
- Unit tests con PydanticAI TestModel
- RAGAS evaluation suite
- Playwright E2E tests
- TDD structure rigorosa (Red-Green-Refactor)

**Epic 6: Project Structure Refactoring & Organization**

- Eliminazione file sparsi in root
- Centralizzazione documentazione in `docs/`
- Riorganizzazione scripts in sottodirectory
- Struttura modulo `mcp/` con tools separati per dominio
- Validazione struttura rigorosa

### Growth Features (Post-MVP)

- **Advanced Analytics**: Trend analysis, cost forecasting
- **Multi-user Monitoring**: Per-user cost tracking
- **Alert System**: Slack/Email notifications per anomalie
- **Document Management UI**: Upload/delete via Streamlit
- **Custom Dashboards**: Grafana integration

### Vision (Future)

- **Auto-scaling**: Basato su load metrics
- **A/B Testing**: Confronto modelli LLM (GPT-4 vs GPT-4o-mini)
- **Multi-tenancy**: Isolamento dati per team
- **GraphRAG**: Knowledge graph integration

---

## Functional Requirements

### Core RAG Capabilities (Baseline)

**FR1:** Il sistema DEVE supportare ingestione di documenti PDF, DOCX, PPTX, XLSX, HTML, MD, TXT via Docling  
**FR2:** Il sistema DEVE generare embeddings vettoriali (1536 dimensioni) per ogni chunk di documento  
**FR3:** Il sistema DEVE memorizzare documenti e chunks in PostgreSQL con estensione PGVector  
**FR4:** Il sistema DEVE eseguire ricerca semantica usando similarità coseno  
**FR5:** Il sistema DEVE fornire risposte RAG con citazioni delle fonti originali  
**FR6:** Il sistema DEVE supportare filtraggio per fonte documentale (source_filter)

### MCP Server Observability

**FR7:** Il sistema DEVE tracciare ogni chiamata `query_knowledge_base` con timestamp, latency, e risultato  
**FR8:** Il sistema DEVE calcolare il costo per ogni query MCP (embedding tokens + LLM tokens)  
**FR9:** Il sistema DEVE inviare trace completi a LangFuse per ogni operazione MCP  
**FR10:** Il sistema DEVE registrare breakdown timing: embedding_time, db_search_time, llm_generation_time  
**FR11:** Il sistema DEVE esporre metriche real-time via endpoint `/metrics` (Prometheus format)  
**FR12:** Il sistema DEVE loggare errori MCP con stack trace completo e context

### MCP Server Architecture & Fix

**FR12.1:** Il MCP server DEVE usare direttamente `core/rag_service.py` senza dipendenza da API server esterno  
**FR12.2:** Il MCP server DEVE essere standalone e funzionare senza `api/main.py` in esecuzione  
**FR12.3:** Il MCP server DEVE essere organizzato in modulo `mcp/` con tools separati per dominio (search, documents, overview)  
**FR12.4:** Il MCP server DEVE implementare pattern FastMCP nativi (lifespan management, context injection)  
**FR12.5:** Il MCP server DEVE garantire che tutti i tool (`query_knowledge_base`, `list_knowledge_base_documents`, `get_knowledge_base_document`, `get_knowledge_base_overview`) e prompt (`ask_knowledge_base`) funzionino correttamente senza errori  
**FR12.6:** Il MCP server DEVE gestire errori con messaggi informativi e graceful degradation

### Streamlit UI Observability

**FR13:** Il sistema DEVE tracciare sessioni utente Streamlit con session_id univoco  
**FR14:** Il sistema DEVE registrare ogni query utente con timestamp, input, e risposta  
**FR15:** Il sistema DEVE calcolare costi cumulativi per sessione Streamlit  
**FR16:** Il sistema DEVE mostrare statistiche sessione corrente nella sidebar (query count, total cost, avg latency)

### Cost Tracking & Analytics

**FR17:** Il sistema DEVE calcolare costo per token (input/output) basato su pricing OpenAI corrente  
**FR18:** Il sistema DEVE aggregare costi giornalieri, settimanali, e mensili  
**FR19:** Il sistema DEVE esportare report costi in formato CSV e JSON  
**FR20:** Il sistema DEVE mostrare dashboard LangFuse con metriche chiave (cost, latency, throughput)

### Production Infrastructure

**FR21:** Il sistema DEVE passare linting (ruff) senza warning  
**FR22:** Il sistema DEVE passare type checking (mypy) senza errori  
**FR23:** Il sistema DEVE avere health check endpoint (`/health`) per ogni servizio (MCP, Streamlit, DB)  
**FR24:** Il sistema DEVE supportare deployment Docker con docker-compose  
**FR25:** Il sistema DEVE avere GitHub Actions per CI/CD (test + lint + build + deploy)

### Documentation & Developer Experience

**FR26:** Il sistema DEVE avere README con setup instructions completabili in < 5 minuti  
**FR27:** Il sistema DEVE avere API documentation auto-generata (Sphinx o MkDocs)  
**FR28:** Il sistema DEVE avere guida monitoring setup (LangFuse configuration step-by-step)  
**FR29:** Il sistema DEVE avere esempi di query con costi stimati e performance attese  
**FR30:** Il sistema DEVE avere badge GitHub (build status, coverage, version, license)  
**FR30.1:** Documentazione DEVE essere centralizzata in `docs/` senza file markdown sparsi  
**FR30.2:** Documentazione DEVE includere troubleshooting guide completa per MCP server  
**FR30.3:** Documentazione DEVE includere guida struttura progetto e organizzazione codice

### Testing & Quality Assurance (TDD)

**FR31:** Il sistema DEVE avere unit tests per tutti i moduli core (core/, ingestion/, utils/) con coverage > 70%  
**FR32:** Il sistema DEVE usare PydanticAI TestModel per mock LLM responses durante unit testing  
**FR33:** Il sistema DEVE avere RAGAS evaluation suite per validare qualità RAG (faithfulness, relevancy)  
**FR34:** Il sistema DEVE avere Playwright E2E tests per workflow Streamlit critici  
**FR35:** Il sistema DEVE avere integration tests per MCP server endpoints  
**FR36:** Il sistema DEVE eseguire tests automaticamente in CI/CD pipeline  
**FR37:** Il sistema DEVE generare coverage report e pubblicarlo su GitHub  
**FR38:** Il sistema DEVE avere test fixtures per database (setup/teardown automatico)  
**FR39:** Il sistema DEVE avere golden dataset per RAGAS evaluation (min 20 query-answer pairs)  
**FR40:** Il sistema DEVE loggare test results in LangFuse per tracking qualità nel tempo

### TDD Structure & Organization

**FR41:** Test suite DEVE essere organizzata rigorosamente in `tests/unit/`, `tests/integration/`, `tests/e2e/`  
**FR42:** Test fixtures DEVE essere in `tests/fixtures/` con golden dataset per RAGAS  
**FR43:** Test DEVE seguire pattern Red-Green-Refactor rigoroso (test prima del codice)  
**FR44:** Coverage report DEVE essere generato automaticamente in CI/CD con threshold > 70%

### Project Structure & Organization

**FR45:** Il progetto DEVE seguire struttura directory rigorosa senza file sparsi in root  
**FR46:** Tutti i file markdown DEVE essere in `docs/` (eccetto README.md root)  
**FR47:** Tutti gli script DEVE essere organizzati in `scripts/` con sottodirectory per categoria  
**FR48:** Il codice DEVE essere organizzato per responsabilità (mcp/, core/, ingestion/, utils/, api/)  
**FR49:** Zero file temporanei o di debug in root directory

---

## Non-Functional Requirements

### Performance

**NFR-P1:** Latency media query MCP < 2 secondi (95th percentile)  
**NFR-P2:** Embedding generation < 500ms per batch (100 chunks)  
**NFR-P3:** DB vector search < 100ms per query (con HNSW index)  
**NFR-P4:** Throughput MCP server: 50 query/secondo con degradazione < 10%

### Scalability

**NFR-S1:** Supporto 50 query concorrenti MCP senza degradazione performance  
**NFR-S2:** Connection pool PostgreSQL: 10-50 connessioni dinamiche  
**NFR-S3:** Horizontal scaling supportato via load balancer (future)

### Reliability

**NFR-R1:** Uptime 99.5% per MCP server (downtime pianificato escluso)  
**NFR-R2:** Retry automatico per fallimenti OpenAI API (max 3 tentativi con exponential backoff)  
**NFR-R3:** Graceful degradation: sistema continua a funzionare se LangFuse non disponibile

### Maintainability

**NFR-M1:** Code coverage > 70% per core modules (core/, ingestion/, utils/)  
**NFR-M2:** Documentazione inline (docstrings) per tutte le funzioni pubbliche  
**NFR-M3:** Logging strutturato (JSON) per facile parsing e analisi

### Security

**NFR-SEC1:** API keys memorizzate in variabili ambiente (no hardcoding)  
**NFR-SEC2:** LangFuse API key protetta e non loggata  
**NFR-SEC3:** PostgreSQL connection string criptata in produzione

### Testing & Quality

**NFR-T1:** Test suite execution time < 5 minuti (unit tests)  
**NFR-T2:** E2E tests execution time < 10 minuti  
**NFR-T3:** RAGAS faithfulness score > 0.85 per golden dataset  
**NFR-T4:** RAGAS answer relevancy score > 0.80 per golden dataset  
**NFR-T5:** Test coverage mantenuto > 70% in CI/CD (fail build se < 70%)

---

## Domain-Specific Requirements

### LangFuse Integration

**Domain Context:** LangFuse è la piattaforma standard per LLM observability. Richiede:

- Trace gerarchici (query → embedding → retrieval → generation)
- Metadata ricchi (model, tokens, cost)
- Session grouping per analisi utente

**Requirements:**

- Trace completi per ogni operazione RAG
- Cost calculation accurato basato su pricing OpenAI
- Session tracking per analisi comportamentale
- LangFuse client inizializzato via environment variables (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`)
- Decorator `@observe()` per auto-tracing funzioni critiche
- Cost tracking automatico per OpenAI calls (drop-in replacement `langfuse.openai`)
- Graceful degradation se LangFuse non disponibile (sistema continua a funzionare)

### MCP Protocol Compliance

**Domain Context:** Model Context Protocol richiede:

- Tool registration standardizzato
- Error handling robusto
- Logging non invasivo (no stdout pollution)

**Requirements:**

- MCP server conforme a spec FastMCP
- Logging via stderr o file dedicato
- Health check non bloccante

---

## References

- [Project Documentation Index](./index.md)
- [Architecture Documentation](./architecture.md)
- [API & Data Analysis](./api-and-data-analysis.md)
- [Technical Requirements Analysis](./technical-requirements-analysis.md)
- [LangFuse Documentation](https://langfuse.com/docs)
- [LangFuse Python SDK Setup](https://langfuse.com/docs/observability/sdk/python/setup)
- [FastMCP Specification](https://github.com/jlowin/fastmcp)
- [FastMCP Best Practices](https://gofastmcp.com/servers/server)
- [PydanticAI Testing Guide](https://ai.pydantic.dev/testing/)
- [RAGAS Documentation](https://docs.ragas.io/)

---

_This PRD defines the roadmap for transforming docling-rag-agent into a production-ready, enterprise-grade RAG system with comprehensive observability and cost tracking._

_Created through collaborative discovery between Stefano and BMAD PM Agent._
