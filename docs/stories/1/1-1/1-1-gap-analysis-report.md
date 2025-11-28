# Gap Analysis Report: Architecture Documentation vs Codebase

**Story:** 1-1-document-current-architecture  
**Data:** 2025-11-26  
**Status:** Complete

## Executive Summary

Questo report documenta le discrepanze tra `docs/architecture.md` e il codice effettivo. **NON modifica architecture.md** come richiesto. L'obiettivo è identificare cosa dovrebbe essere aggiornato.

## Severity Legend

- 🔴 **CRITICAL**: Documentazione descrive comportamento diverso dal codice
- 🟠 **MAJOR**: Struttura/pattern diversi da quanto documentato
- 🟡 **MINOR**: File mancanti o extra non documentati
- 🟢 **OK**: Conforme alla documentazione

---

## 1. MCP Server Architecture 🔴 CRITICAL

### Documentazione (architecture.md)

```
mcp/
├── server.py          # FastMCP instance + tool registration
├── lifespan.py        # Server lifecycle (DB init, embedder init)
└── tools/
    ├── search.py      # query_knowledge_base, ask_knowledge_base
    ├── documents.py   # list_knowledge_base_documents, get_knowledge_base_document
    └── overview.py    # get_knowledge_base_overview
```

Pattern: **Direct Service Integration** - `from core.rag_service import search_knowledge_base_structured`

### Codice Effettivo

```
mcp_server.py          # At root level, NOT in mcp/
mcp/
└── tools/
    └── __init__.py    # Empty file!
```

Pattern: **HTTP Proxy** - usa `RAGClient` per chiamate HTTP a API Server

### Discrepanze Specifiche

| Aspetto             | Documentazione             | Codice Effettivo            |
| ------------------- | -------------------------- | --------------------------- |
| Location MCP Server | `mcp/server.py`            | `mcp_server.py` (root)      |
| Lifespan file       | `mcp/lifespan.py`          | Non esiste                  |
| Tools organization  | Files separati per dominio | Inline in `mcp_server.py`   |
| Integration pattern | Direct import da core      | HTTP via `RAGClient`        |
| Dipendenza API      | Nessuna                    | Richiede API Server running |

### Impatto

L'architettura attuale richiede che l'API Server sia in esecuzione per il funzionamento del MCP Server. Questo contraddice il pattern "standalone" documentato.

---

## 2. Integration Patterns 🔴 CRITICAL

### ADR-002: MCP Server Standalone Architecture

**Documentazione dice:**

> MCP server uses direct service integration pattern, no HTTP dependency

```python
# Documented pattern
from core.rag_service import search_knowledge_base_structured

@mcp.tool
async def query_knowledge_base(query: str, limit: int = 5):
    return await search_knowledge_base_structured(query, limit)
```

**Codice effettivo (`mcp_server.py`):**

```python
from client.api_client import RAGClient

client = RAGClient()  # HTTP client

@mcp.tool()
async def query_knowledge_base(query: str, limit: int = 5, source_filter: Optional[str] = None) -> str:
    response = await client.search(query, limit, source_filter)  # HTTP call!
```

### core/agent.py

**Documentazione dice:**

> Pattern: Agent Wrapper Integration - from core.agent import RAGAgent

**Codice effettivo:**

```python
from client.api_client import RAGClient
client = RAGClient()  # HTTP client, not direct import
```

---

## 3. Project Structure Gaps 🟠 MAJOR

### File/Directory Non Documentati (esistono nel codice)

| Path                               | Descrizione                         |
| ---------------------------------- | ----------------------------------- |
| `mcp_server.py`                    | MCP Server entry point (root level) |
| `client/`                          | Directory con `api_client.py`       |
| `client/api_client.py`             | RAGClient HTTP client               |
| `debug_mcp_tools.py`               | Debug utility (root level)          |
| `ingestion/chunker_no_docling.py`  | Alternative chunker senza Docling   |
| `temp_query.py`                    | Temporary query script              |
| `walkthrough.md`                   | Walkthrough doc                     |
| `MCP_TROUBLESHOOTING.md`           | Troubleshooting guide               |
| `pydantic_ai_testing_reference.md` | Testing reference                   |
| `flusso-mcp-tool.md`               | MCP tool flow doc                   |
| `mat-FastMCP-e-architecture.md`    | FastMCP architecture notes          |

### File/Directory Documentati ma Mancanti

| Path Documentato                | Status                                            |
| ------------------------------- | ------------------------------------------------- |
| `mcp/server.py`                 | ❌ Non esiste                                     |
| `mcp/lifespan.py`               | ❌ Non esiste                                     |
| `mcp/tools/search.py`           | ❌ Non esiste                                     |
| `mcp/tools/documents.py`        | ❌ Non esiste                                     |
| `mcp/tools/overview.py`         | ❌ Non esiste                                     |
| `scripts/verification/`         | ❌ Directory non esiste                           |
| `scripts/debug/`                | ❌ Directory non esiste                           |
| `.github/workflows/ci.yml`      | ❌ `.github/` non esiste                          |
| `.github/workflows/release.yml` | ❌ `.github/` non esiste                          |
| `sql/schema.sql`                | ❌ Non esiste (contenuto in `optimize_index.sql`) |

### Scripts Organization

**Documentazione:**

```
scripts/
├── verification/
│   ├── verify_api_endpoints.py
│   ├── verify_mcp_setup.py
│   └── verify_client_integration.py
└── debug/
    └── debug_mcp_tools.py
```

**Codice effettivo:**

```
scripts/
├── optimize_database.py
├── test_mcp_performance.py
├── verify_api_endpoints.py
├── verify_api.py
├── verify_client_integration.py
└── verify_mcp_setup.py

debug_mcp_tools.py  # At root level!
```

---

## 4. Component Responsibilities 🟢 OK (with notes)

### core/rag_service.py ✅

**Status:** Conforme alla documentazione

- Ha `search_knowledge_base_structured` come documentato
- Global embedder pattern implementato
- Pure business logic, decoupled

**Nota:** Non viene usato direttamente da MCP/Streamlit (passa via HTTP)

### core/agent.py 🟡

**Status:** Parzialmente conforme

- PydanticAI Agent presente ✅
- Usa `RAGClient` invece di import diretto da `core.rag_service` ⚠️

### ingestion/ ✅

**Status:** Conforme alla documentazione

- `ingest.py`: DocumentIngestionPipeline ✅
- `chunker.py`: HybridChunker, SimpleChunker ✅
- `embedder.py`: EmbeddingGenerator ✅
- File extra: `chunker_no_docling.py` (non documentato)

### utils/ ✅

**Status:** Conforme alla documentazione

- `db_utils.py`: DatabasePool, connection pooling ✅
- `models.py`: Pydantic models ✅
- `providers.py`: OpenAI provider config ✅

### api/ ✅

**Status:** Conforme alla documentazione

- `main.py`: FastAPI app + endpoints ✅
- `models.py`: API request/response models ✅

---

## 5. Data Flow Diagrams 🟠 MAJOR

### Documentazione: MCP Server Flow

```
MCP Tool → core/rag_service → DB → Response
```

### Codice Effettivo: MCP Server Flow

```
MCP Tool → RAGClient → HTTP → API Server (FastAPI)
                                    ↓
                              core/rag_service
                                    ↓
                                   DB
                                    ↓
                              HTTP Response
                                    ↓
                              MCP Response
```

### Documentazione: Streamlit Flow

```
User Query → PydanticAI Agent → core/rag_service → Response
```

### Codice Effettivo: Streamlit Flow

```
User Query → PydanticAI Agent → RAGClient → HTTP → API Server
                                                       ↓
                                                 core/rag_service
                                                       ↓
                                                 HTTP Response
                                                       ↓
                                               Agent Response
```

---

## 6. LangFuse Integration 🟡 MINOR

### Documentazione

ADR-001 descrive:

- `@observe()` decorator pattern
- `langfuse.openai` wrapper per cost tracking
- Graceful degradation se unavailable

### Codice Effettivo

- Nessuna integrazione LangFuse implementata
- Documentato come Epic 2 (futuro)
- **Status:** Corretto - documentazione descrive stato target, non attuale

---

## 7. Tests Structure 🟢 OK

### Documentazione

```
tests/
├── unit/
├── integration/
├── e2e/
└── fixtures/
```

### Codice Effettivo

```
tests/
├── __init__.py
├── conftest.py
├── fixtures/
├── integration/
│   └── test_mcp_server_integration.py
├── unit/
│   ├── test_api_client.py
│   └── test_mcp_server_validation.py
└── README.md
```

**Status:** Conforme, manca solo `e2e/` (pianificato per Epic 5)

---

## 8. utils/models.py 🟡 MINOR

### Discrepanza in IngestionResult

**Documentazione (Project Structure):**

> `entities_extracted`, `relationships_created` per knowledge graph

**Codice effettivo:**

```python
class IngestionResult(BaseModel):
    document_id: str
    title: str
    chunks_created: int
    processing_time_ms: float
    errors: List[str] = Field(default_factory=list)
    # entities_extracted e relationships_created RIMOSSI
```

**Nota:** Graph functionality rimossa, modello semplificato.

---

## 9. CI/CD & Infrastructure 🟡 MINOR

### .github/workflows/

**Documentazione:**

```
.github/
└── workflows/
    ├── ci.yml       # Lint, type-check, test, build
    └── release.yml  # Release automation
```

**Codice Effettivo:**

- Directory `.github/` non esiste
- **Status:** Documentato come target (Epic 4), non ancora implementato

### SQL Files

**Documentazione:**

```
sql/
├── schema.sql          # PostgreSQL + PGVector schema
├── optimize_index.sql
└── removeDocuments.sql
```

**Codice Effettivo:**

```
sql/
├── optimize_index.sql  # Contiene ANCHE lo schema completo
└── removeDocuments.sql
```

**Nota:** `schema.sql` non esiste - lo schema è incluso in `optimize_index.sql`

---

## Action Items Summary

### Da Aggiornare in architecture.md

1. **🔴 CRITICAL: MCP Server Location**

   - Documentare che MCP server è in `mcp_server.py` (root)
   - O refactorare per allinearlo alla documentazione

2. **🔴 CRITICAL: Integration Pattern**

   - Documentare pattern HTTP proxy attuale
   - O implementare Direct Service Integration

3. **🟠 MAJOR: Project Structure**

   - Aggiungere `client/` directory
   - Rimuovere `mcp/lifespan.py`, `mcp/tools/` subdirectories
   - Documentare scripts flat structure

4. **🟠 MAJOR: Data Flow Diagrams**

   - Aggiornare per riflettere HTTP proxy pattern

5. **🟡 MINOR: File Extra**
   - Documentare o rimuovere file root level non necessari

---

## Recommendations

### Opzione A: Allineare Codice alla Documentazione

Refactoring per implementare "Direct Service Integration":

- Spostare `mcp_server.py` → `mcp/server.py`
- Creare `mcp/lifespan.py`
- Separare tools in files distinti
- Rimuovere dipendenza da `RAGClient` nel MCP server

**Pro:** Architettura più pulita, no dipendenza HTTP per MCP
**Contro:** Breaking change, richiede testing estensivo

### Opzione B: Allineare Documentazione al Codice

Aggiornare architecture.md per riflettere stato attuale:

- Documentare HTTP proxy pattern
- Aggiornare project structure
- Aggiornare data flow diagrams

**Pro:** Nessuna modifica al codice
**Contro:** Pattern meno efficiente (HTTP overhead)

### Raccomandazione

**Opzione B** per questa story (documentazione), poi pianificare **Opzione A** come story separata in Epic 2 (già previsto il refactoring MCP standalone).

---

## Validation Checklist

- [x] Scansionato codebase: `core/`, `ingestion/`, `utils/`, `mcp/`, `api/`, `app.py`
- [x] Confrontato project structure documentato vs effettivo
- [x] Verificato integration patterns
- [x] Analizzato data flows
- [x] Identificato file non documentati
- [x] Verificato component responsibilities
- [ ] **Pending:** architecture.md NON modificato (come richiesto)

---

_Report generato da Dev Agent - Story 1.1_
