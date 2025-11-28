# Analisi Requisiti Tecnici e Struttura Rigorosa

**Data:** 2025-11-26  
**Preparato da:** PM Agent (BMAD)  
**Contesto:** Allineamento PRD con requisiti tecnici ufficiali e implementazione struttura rigorosa

---

## Executive Summary

Analisi completa dei requisiti tecnici per trasformare `docling-rag-agent` in un sistema production-ready con:
1. **MCP Server funzionante** con pattern nativi FastMCP (eliminazione dipendenza API esterna)
2. **Struttura rigorosa** basata su best practices FastMCP e TDD
3. **TDD Framework completo** con pytest, PydanticAI TestModel, RAGAS
4. **Allineamento con langfuse-docs MCP** per funzionalità equivalenti

---

## 1. Requisiti Tecnici Recuperati da Fonti Ufficiali

### 1.1 FastMCP Best Practices (da gofastmcp.com e GitHub templates)

**Struttura Modulare:**
- Server principale in modulo dedicato (`mcp/` non root)
- Tools organizzati per dominio funzionale
- Lifespan management per inizializzazione risorse
- Context injection per dependency management

**Pattern Consigliati:**
- **Stateless Design**: Ogni request crea nuovo server instance (Langfuse pattern)
- **Modular Composition**: Usare `import_server` e `mount` per componenti riutilizzabili
- **Tool Organization**: Raggruppare tools per dominio (search, documents, overview)
- **Error Handling**: ToolError per errori gestiti, exception wrapping per errori inattesi

**Struttura Directory Consigliata:**
```
mcp/
├── __init__.py
├── server.py          # FastMCP server instance
├── tools/
│   ├── __init__.py
│   ├── search.py      # query_knowledge_base, ask_knowledge_base
│   ├── documents.py   # list_knowledge_base_documents, get_knowledge_base_document
│   └── overview.py    # get_knowledge_base_overview
├── resources.py       # Se necessario per resources MCP
└── prompts.py         # Se necessario per prompts MCP
```

### 1.2 LangFuse Python SDK v3 (da langfuse.com/docs)

**Setup Requirements:**
- Environment variables: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`
- Singleton client access via `get_client()`
- Graceful degradation se LangFuse non disponibile
- Batch export automatico (`flush_at=512`, `flush_interval=5s`)

**Integration Pattern:**
```python
from langfuse import observe
from langfuse.openai import openai

@observe()
async def query_knowledge_base(query: str):
    # Auto-traced con LangFuse
    embedding = await embedder.embed_query(query)
    results = await db_search(embedding)
    return results
```

**Cost Tracking:**
- Automatico per OpenAI calls (drop-in replacement)
- Manual tracking per embedding tokens
- Usage details: `input_tokens`, `output_tokens`, `cached_tokens`
- Cost details: `USD` per tipo (input/output/cached)

### 1.3 TDD Best Practices (da pytest, testdriven.io, DataCamp)

**Struttura Test Rigorosa:**
```
tests/
├── __init__.py
├── conftest.py           # Fixtures condivisi
├── unit/
│   ├── __init__.py
│   ├── test_rag_service.py
│   ├── test_embedder.py
│   ├── test_chunker.py
│   └── test_mcp_tools.py
├── integration/
│   ├── __init__.py
│   ├── test_mcp_server.py
│   ├── test_api_endpoints.py
│   └── test_langfuse_integration.py
├── e2e/
│   ├── __init__.py
│   └── test_rag_workflow.py
└── fixtures/
    ├── __init__.py
    ├── test_data.json
    └── golden_dataset.json
```

**TDD Workflow:**
1. **Red**: Scrivere test che fallisce
2. **Green**: Implementare minimo codice per passare
3. **Refactor**: Migliorare codice mantenendo test verde

**PydanticAI TestModel:**
```python
from pydantic_ai.models.test import TestModel

async def test_query_knowledge_base():
    agent = Agent('test-model', system_prompt='...')
    test_model = TestModel()
    
    with agent.override(model=test_model):
        result = await agent.run('test query')
        assert result.output is not None
```

**RAGAS Evaluation:**
- Golden dataset: 20+ query-answer pairs
- Metriche: Faithfulness > 0.85, Relevancy > 0.80
- Integrazione con LangFuse per tracking

---

## 2. File Sparsi da Riorganizzare/Rimuovere

### 2.1 File da Rimuovere (tracce inutili)

**Root Directory:**
- `debug_mcp_tools.py` → Spostare in `scripts/debug/` o rimuovere
- `temp_query.py` → Rimuovere (file temporaneo)
- `T/` → Rimuovere se vuoto o spostare contenuto

**Documentazione Sparsa:**
- `flusso-mcp-tool.md` → Integrare in `docs/development-guide.md` o rimuovere
- `mat-FastMCP-e-architecture.md` → Integrare in `docs/architecture.md` o rimuovere
- `MCP_TROUBLESHOOTING.md` → Integrare in `docs/mcp-troubleshooting-overview.md`
- `pydantic_ai_testing_reference.md` → Integrare in `docs/development-guide.md` o `tests/README.md`
- `walkthrough.md` → Integrare in `docs/development-guide.md` o rimuovere

### 2.2 File da Riorganizzare

**Scripts:**
- `scripts/verify_*.py` → Riorganizzare in `scripts/verification/`
- `scripts/test_mcp_performance.py` → Spostare in `tests/performance/`

**Client:**
- `client/api_client.py` → **CRITICO**: Eliminare dipendenza, usare direttamente `core/rag_service.py` nel MCP server

---

## 3. Struttura Rigorosa Proposta

### 3.1 Directory Structure (Finale)

```
docling-rag-agent/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .cursor/
│   └── rules/
├── .bmad/
├── api/                          # FastAPI service (se necessario)
│   ├── __init__.py
│   ├── main.py
│   └── models.py
├── core/                         # Core business logic
│   ├── __init__.py
│   ├── rag_service.py
│   └── agent.py
├── ingestion/                    # Document ingestion pipeline
│   ├── __init__.py
│   ├── ingest.py
│   ├── chunker.py
│   └── embedder.py
├── mcp/                          # MCP Server (NUOVO - non root)
│   ├── __init__.py
│   ├── server.py                 # FastMCP instance
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── search.py             # query_knowledge_base, ask_knowledge_base
│   │   ├── documents.py          # list_knowledge_base_documents, get_knowledge_base_document
│   │   └── overview.py            # get_knowledge_base_overview
│   └── lifespan.py               # Server lifecycle management
├── tests/                        # Test suite TDD
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_rag_service.py
│   │   ├── test_embedder.py
│   │   ├── test_chunker.py
│   │   └── test_mcp_tools.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_mcp_server.py
│   │   └── test_langfuse_integration.py
│   ├── e2e/
│   │   ├── __init__.py
│   │   └── test_rag_workflow.py
│   └── fixtures/
│       ├── __init__.py
│       ├── test_data.json
│       └── golden_dataset.json
├── utils/                        # Shared utilities
│   ├── __init__.py
│   ├── db_utils.py
│   ├── models.py
│   └── providers.py
├── scripts/                      # Utility scripts
│   ├── __init__.py
│   ├── optimize_database.py
│   ├── verification/
│   │   ├── __init__.py
│   │   ├── verify_api.py
│   │   └── verify_mcp_setup.py
│   └── debug/
│       └── debug_mcp_tools.py
├── sql/                          # Database scripts
│   ├── schema.sql
│   ├── optimize_index.sql
│   └── removeDocuments.sql
├── docs/                         # Documentation
│   ├── index.md
│   ├── architecture.md
│   ├── prd.md
│   ├── development-guide.md
│   └── ...
├── app.py                        # Streamlit UI (entry point)
├── pyproject.toml                # Project configuration
├── README.md
└── docker-compose.yml
```

### 3.2 Principi Strutturali

**1. Separazione Responsabilità:**
- `mcp/` → MCP server logic (no business logic)
- `core/` → Business logic pura (no MCP dependencies)
- `api/` → FastAPI service (opzionale, per scaling futuro)
- `tests/` → Test organizzati per tipo (unit/integration/e2e)

**2. Eliminazione Dipendenze Esterne:**
- **RIMUOVERE**: `client/api_client.py` e dipendenza HTTP da MCP server
- **USARE**: Chiamate dirette a `core/rag_service.py` nel MCP server
- **RISULTATO**: MCP server standalone, no API server esterno richiesto

**3. TDD Rigoroso:**
- Test prima del codice (Red-Green-Refactor)
- Coverage > 70% per core modules
- PydanticAI TestModel per mock LLM
- RAGAS per evaluation qualità RAG

**4. Documentazione Centralizzata:**
- Tutti i `.md` in `docs/` (eccetto README.md root)
- Nessun file markdown sparso in root
- Integrazione documentazione sparsa in guide esistenti

---

## 4. Requisiti Tecnici per PRD Update

### 4.1 MCP Server Fix (CRITICO)

**FR-MCP-FIX1:** Il MCP server DEVE usare direttamente `core/rag_service.py` senza dipendenza da API server esterno  
**FR-MCP-FIX2:** Il MCP server DEVE essere standalone e funzionare senza `api/main.py` in esecuzione  
**FR-MCP-FIX3:** Il MCP server DEVE essere organizzato in modulo `mcp/` con tools separati per dominio  
**FR-MCP-FIX4:** Il MCP server DEVE implementare pattern FastMCP nativi (lifespan, context injection)

### 4.2 Struttura Rigorosa

**FR-STRUCT1:** Il progetto DEVE seguire struttura directory rigorosa senza file sparsi in root  
**FR-STRUCT2:** Tutti i file markdown DEVE essere in `docs/` (eccetto README.md)  
**FR-STRUCT3:** Tutti gli script DEVE essere organizzati in `scripts/` con sottodirectory per categoria  
**FR-STRUCT4:** Il codice DEVE essere organizzato per responsabilità (mcp/, core/, ingestion/, utils/)

### 4.3 TDD Framework

**FR-TDD-STRUCT1:** Test suite DEVE essere organizzata in `tests/unit/`, `tests/integration/`, `tests/e2e/`  
**FR-TDD-STRUCT2:** Test fixtures DEVE essere in `tests/fixtures/` con golden dataset per RAGAS  
**FR-TDD-STRUCT3:** Test DEVE seguire pattern Red-Green-Refactor rigoroso  
**FR-TDD-STRUCT4:** Coverage report DEVE essere generato automaticamente in CI/CD

### 4.4 LangFuse Integration

**FR-LF-STRUCT1:** LangFuse client DEVE essere inizializzato via environment variables  
**FR-LF-STRUCT2:** LangFuse tracing DEVE usare decorator `@observe()` per auto-tracing  
**FR-LF-STRUCT3:** LangFuse cost tracking DEVE essere automatico per OpenAI calls  
**FR-LF-STRUCT4:** LangFuse DEVE avere graceful degradation se non disponibile

---

## 5. Piano di Refactoring

### Fase 1: Cleanup File Sparsi (Immediato)
1. Rimuovere `temp_query.py`, `T/` (se vuoto)
2. Integrare documentazione sparsa in `docs/`
3. Riorganizzare scripts in sottodirectory

### Fase 2: Refactoring MCP Server (Priorità Alta)
1. Creare `mcp/` directory
2. Spostare `mcp_server.py` → `mcp/server.py`
3. Creare `mcp/tools/` con tools separati
4. Eliminare dipendenza da `client/api_client.py`
5. Usare direttamente `core/rag_service.py`

### Fase 3: Struttura Test TDD (Priorità Alta)
1. Riorganizzare `tests/` in unit/integration/e2e
2. Creare `tests/fixtures/` con golden dataset
3. Implementare PydanticAI TestModel fixtures
4. Setup RAGAS evaluation suite

### Fase 4: LangFuse Integration (Priorità Media)
1. Setup LangFuse client con environment variables
2. Implementare `@observe()` decorator su funzioni critiche
3. Configurare cost tracking automatico
4. Test graceful degradation

---

## 6. Success Criteria

### Struttura
- ✅ Zero file markdown in root (eccetto README.md)
- ✅ Zero file Python temporanei in root
- ✅ MCP server in `mcp/` module
- ✅ Test organizzati per tipo (unit/integration/e2e)

### Funzionalità
- ✅ MCP server funziona senza API server esterno
- ✅ Tutti i tools MCP funzionano correttamente
- ✅ LangFuse tracing completo
- ✅ Test coverage > 70%

### Qualità
- ✅ Zero file sparsi o temporanei
- ✅ Struttura rigorosa e mantenibile
- ✅ TDD workflow implementato
- ✅ Documentazione centralizzata

---

## 7. Riferimenti Tecnici

- [FastMCP Documentation](https://gofastmcp.com/servers/server)
- [FastMCP Templates](https://github.com/JoshuaWink/fastmcp-templates)
- [LangFuse Python SDK Setup](https://langfuse.com/docs/observability/sdk/python/setup)
- [LangFuse MCP Server](https://langfuse.com/docs/docs-mcp)
- [PydanticAI Testing](https://ai.pydantic.dev/testing/)
- [RAGAS Documentation](https://docs.ragas.io/)
- [TDD Best Practices](https://testdriven.io/blog/modern-tdd/)

---

_Questo documento definisce i requisiti tecnici per trasformare docling-rag-agent in un sistema production-ready con struttura rigorosa e TDD completo._

