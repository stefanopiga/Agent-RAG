# Docling RAG Agent

[![Build Status](https://img.shields.io/github/actions/workflow/status/stefanopiga/Agent-RAG/ci.yml?branch=main&label=build)](https://github.com/stefanopiga/Agent-RAG/actions)
[![Coverage](https://img.shields.io/codecov/c/github/stefanopiga/Agent-RAG?label=coverage)](https://codecov.io/gh/stefanopiga/Agent-RAG)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/stefanopiga/Agent-RAG/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen)](https://www.python.org/)

Un agente intelligente basato su Streamlit che fornisce accesso conversazionale a una knowledge base archiviata in PostgreSQL con PGVector. Utilizza RAG (Retrieval Augmented Generation) per cercare nei documenti embedded e fornire risposte contestuali e accurate con citazioni delle fonti. Supporta molteplici formati di documenti.

## 🎓 Nuovo a Docling?

**Inizia dai tutorial!** Consulta la cartella [`docling_basics/`](./docling_basics/) per esempi progressivi che insegnano i fondamenti di Docling:

1. **Conversione PDF Semplice** - Elaborazione base dei documenti
2. **Supporto Formati Multipli** - Gestione PDF, Word, PowerPoint
3. **Chunking Ibrido** - Chunking intelligente per sistemi RAG

Questi tutorial forniscono le basi per comprendere come funziona questo agente RAG completo. [**→ Vai a Docling Basics**](./docling_basics/)

## Funzionalità

- 💬 Interfaccia chat web interattiva con Streamlit
- 🔍 Ricerca semantica attraverso documenti vettoriali embedded
- 📚 Risposte context-aware usando pipeline RAG
- 🎯 Citazione delle fonti per tutte le informazioni fornite
- 🔄 Output di testo in streaming real-time mentre arrivano i token
- 💾 PostgreSQL/PGVector per storage scalabile della conoscenza
- 🧠 Cronologia conversazione mantenuta tra i turni

## Prerequisiti

| Tool           | Versione                      | Link Installazione                                                           |
| -------------- | ----------------------------- | ---------------------------------------------------------------------------- |
| **Python**     | 3.10+ (3.11 raccomandato)     | [python.org/downloads](https://www.python.org/downloads/)                    |
| **UV**         | 0.9.13+ (latest raccomandato) | [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |
| **PostgreSQL** | 16+ con PGVector              | [postgresql.org](https://www.postgresql.org/download/)                       |
| **Docker**     | latest (opzionale)            | [docker.com](https://www.docker.com/products/docker-desktop/)                |

**API Keys richieste:**

- `OPENAI_API_KEY` - OpenAI API key per embeddings e LLM ([ottienila qui](https://platform.openai.com/api-keys))

**Provider Database supportati:**

- PostgreSQL self-hosted con estensione PGVector
- Supabase (managed PostgreSQL)
- Neon (serverless PostgreSQL)

## Quick Start

> **Tempo totale stimato: ~3-4 minuti** (esclusa installazione prerequisiti)

### 1. Clona e Installa Dipendenze (~30 secondi)

```bash
# Clona il repository
git clone https://github.com/stefanopiga/Agent-RAG.git
cd Agent-RAG

# Installa le dipendenze usando UV
uv sync
```

### 2. Configura le Variabili d'Ambiente (~30 secondi)

```bash
cp .env.example .env
```

Modifica `.env` con le tue credenziali:

```env
# RICHIESTO: Connessione database PostgreSQL con PGVector
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# RICHIESTO: OpenAI API key
OPENAI_API_KEY=sk-...

# OPZIONALE: Modello LLM (default: gpt-4o-mini)
LLM_CHOICE=gpt-4o-mini

# OPZIONALE: Modello embedding (default: text-embedding-3-small)
EMBEDDING_MODEL=text-embedding-3-small

# OPZIONALE: LangFuse per observability/tracing (MCP server)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

**Esempi DATABASE_URL per provider:**

- **Self-hosted**: `postgresql://user:password@localhost:5432/dbname`
- **Supabase**: `postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres`
- **Neon**: `postgresql://[user]:[password]@[endpoint].neon.tech/[dbname]`

### 3. Configura il Database (~1 minuto)

**Fresh install:**

```bash
# Esegui lo schema completo (include HNSW index ottimizzato)
psql $DATABASE_URL < sql/optimize_index.sql
```

**Per Supabase/Neon:** Usa l'editor SQL integrato e incolla il contenuto di `sql/optimize_index.sql`.

**Upgrade database esistente:**

```bash
python scripts/optimize_database.py --apply
```

Il file SQL (`sql/optimize_index.sql`) crea:

- ✅ Estensioni richieste (`vector`, `uuid-ossp`, `pg_trgm`)
- ✅ Tabella `documents` per memorizzare documenti originali con metadati
- ✅ Tabella `chunks` per chunk di testo con embeddings a 1536 dimensioni
- ✅ Funzione `match_chunks()` per ricerca di similarità vettoriale
- ✅ **HNSW index ottimizzato** (10-100x più veloce del vecchio IVFFlat)
- ✅ Performance indexes per filtering e source queries

**Epic 3 - Session Tracking (Opzionale):**

Per abilitare session tracking e cost visibility nella Streamlit UI:

```bash
# Esegui schema Epic 3 (crea tabelle sessions e query_logs)
# Per Supabase: Usa SQL Editor e incolla contenuto di sql/epic-3-sessions-schema.sql
psql $DATABASE_URL < sql/epic-3-sessions-schema.sql
```

Questo crea:

- ✅ Tabella `sessions` per session tracking con statistiche (query_count, total_cost, avg_latency)
- ✅ Tabella `query_logs` per logging query con costi e timing
- ✅ RLS policies `service_role` only (protezione completa)
- ✅ Indexes per performance (session_id, timestamp lookups)

**Vantaggi HNSW:**

- 🚀 50-80% più veloce nelle ricerche vettoriali
- 📈 Performance consistente al crescere del dataset
- 🎯 Ottimale per <1M vectors (case d'uso RAG tipici)

### 4. Ingerisci i Documenti (~1-2 minuti per setup iniziale)

Aggiungi i tuoi documenti nella cartella `documents/`. **Supportati molteplici formati tramite Docling**:

**Formati Supportati:**

- 📄 **PDF** (`.pdf`)
- 📝 **Word** (`.docx`, `.doc`)
- 📊 **PowerPoint** (`.pptx`, `.ppt`)
- 📈 **Excel** (`.xlsx`, `.xls`)
- 🌐 **HTML** (`.html`, `.htm`)
- 📋 **Markdown** (`.md`, `.markdown`)
- 📃 **Testo** (`.txt`)

```bash
# Ingerisci tutti i documenti supportati nella cartella documents/
# NOTA: Di default, questo CANCELLA i dati esistenti prima dell'ingestione
uv run python -m ingestion.ingest --documents documents/

# Regola la dimensione dei chunk (default: 1000)
uv run python -m ingestion.ingest --documents documents/ --chunk-size 800
```

**⚠️ Importante:** Il processo di ingestione **cancella automaticamente tutti i documenti e chunk esistenti** dal database prima di aggiungere nuovi documenti. Questo assicura uno stato pulito e previene duplicati.

La pipeline di ingestione:

1. **Auto-rileva il tipo di file** e usa Docling per PDF, documenti Office e HTML
2. **Converte in Markdown** per elaborazione consistente
3. **Divide in chunk semantici** con dimensione configurabile
4. **Genera embeddings** usando OpenAI
5. **Memorizza in PostgreSQL** con PGVector per ricerca di similarità

**💡 Best Practice - Organizzazione Documenti:**

Organizza i documenti in sottocartelle per sfruttare il filtraggio per fonte:

```
documents/
├── docling/
│   ├── docs/
│   │   ├── getting-started.md
│   │   └── architecture.md
│   └── README.md
├── langfuse-docs/
│   ├── deployment/
│   │   ├── cloud.md
│   │   └── docker.md
│   ├── api/
│   │   └── tracing.md
│   └── guides/
└── company-docs/
    ├── policies.pdf
    └── procedures.docx
```

**Vantaggi:**

- ✅ Citazioni precise con percorso completo
- ✅ Filtraggio per documentazione specifica ("cerca solo in Docling docs")
- ✅ Facile manutenzione e aggiornamenti
- ✅ Separazione logica tra diverse fonti di conoscenza

### 5. Esegui l'Applicazione (~10 secondi)

```bash
streamlit run app.py
```

L'applicazione si aprirà automaticamente nel browser: `http://localhost:8501`

**Funzionalità:**

- 💬 **Interfaccia chat** con cronologia messaggi
- 📊 **Pulsante cancella chat** per resettare la conversazione
- 🎨 **UI moderna** costruita con Streamlit
- 🔍 **Streaming real-time** delle risposte
- 📚 **Stato della knowledge base** nella sidebar

**Esempio di interazione:**

```
Tu: Quali argomenti sono trattati nella knowledge base?
Assistant: Sulla base della knowledge base, gli argomenti principali includono...

[Fonte: company-overview.md]
Contenuto dal documento...
```

## Architettura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Streamlit  │────▶│  RAG Agent   │────▶│ PostgreSQL  │
│     UI      │     │ (PydanticAI) │     │  PGVector   │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
              ┌─────▼────┐  ┌────▼─────┐
              │  OpenAI  │  │  OpenAI  │
              │   LLM    │  │Embeddings│
              └──────────┘  └──────────┘
```

## Componenti Chiave

### RAG Agent

L'agente principale (`rag_agent.py`) che:

- Gestisce le connessioni al database con connection pooling
- Fornisce il tool search_knowledge_base per operazioni RAG
- Si integra con l'interfaccia Streamlit tramite app.py
- Traccia la cronologia della conversazione per il contesto

### Tool search_knowledge_base

Funzione tool registrata con l'agente che:

- Genera query embeddings usando OpenAI
- Effettua ricerche usando similarità coseno PGVector
- Restituisce i top-k chunk più rilevanti
- Formatta i risultati con citazioni delle fonti
- **Supporta filtraggio per fonte** per ricerche mirate in documentazioni specifiche

**Capacità di Filtraggio Avanzato:**
L'agente può filtrare automaticamente le ricerche per fonte specifica quando richiesto dall'utente.

Esempi di query con filtraggio:

- "Come fare il deploy di Docling usando solo la documentazione Docling?"
- "Spiega il tracing secondo Langfuse docs, non guardare altre fonti"
- "Deployment in Langfuse" → filtra automaticamente su `langfuse-docs`

Esempio definizione tool:

```python
async def search_knowledge_base(
    ctx: RunContext[None],
    query: str,
    limit: int = 5,
    source_filter: str | None = None  # Filtro opzionale per fonte
) -> str:
    """Cerca nella knowledge base usando similarità semantica.

    Args:
        query: Query di ricerca
        limit: Numero massimo risultati
        source_filter: Filtro opzionale (es: "docling", "langfuse-docs")
    """
    # Genera embedding per la query
    # Cerca in PostgreSQL con PGVector
    # Applica filtro fonte se specificato
    # Formatta e restituisce i risultati
```

### Schema Database

- `documents`: Memorizza documenti originali con metadati

  - `id`, `title`, `source`, `content`, `metadata`, `created_at`, `updated_at`

- `chunks`: Memorizza chunk di testo con embeddings vettoriali

  - `id`, `document_id`, `content`, `embedding` (vector(1536)), `chunk_index`, `metadata`, `token_count`

- `match_chunks()`: Funzione PostgreSQL per ricerca similarità vettoriale
  - Usa similarità coseno (`1 - (embedding <=> query_embedding)`)
  - Restituisce chunk con punteggi di similarità sopra la soglia

## 🚀 MCP Server per Cursor IDE

Il progetto include un **Model Context Protocol (MCP) server** ottimizzato per integrazione con Cursor IDE.

**Setup MCP:**

1. **Configura `.cursor/mcp.json`:**

```json
{
  "mcpServers": {
    "docling-rag": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/path/to/docling-rag-agent",
        "python",
        "-m",
        "docling_mcp.server"
      ],
      "env": {
        "PYTHONPATH": "/path/to/docling-rag-agent"
      }
    }
  }
}
```

2. **Restart Cursor** - MCP server si avvia automaticamente

3. **Usa il tool** in Cursor:

```
Chiedi: "What is Docling?"
Il MCP tool cercherà nella knowledge base e risponderà con context
```

**Performance MCP:**

- ✅ Global embedder instance: -70% latency (eliminato overhead 300-500ms)
- ✅ HNSW index: -61% query time (1395ms avg, 237ms con cache)
- ✅ Connection pool ottimizzato: -20% overhead
- ✅ Timing instrumentation per monitoring

### MCP HTTP Server (Observability Endpoints)

Il progetto include anche un **MCP HTTP Server** separato che espone endpoint di osservabilità per monitoring e health checks.

**Avvio locale:**

```bash
# Avvia il server HTTP per metriche e health check (porta 8080)
uv run python -m docling_mcp.http_server

# Oppure con porta personalizzata
METRICS_PORT=9090 uv run python -m docling_mcp.http_server
```

**Endpoints disponibili:**

- `GET /health` - Health check endpoint con status dettagliato (database, LangFuse, embedder)
- `GET /metrics` - Prometheus metrics endpoint
- `GET /docs` - API documentation (Swagger UI)

**Differenza tra MCP Server stdio e HTTP Server:**

- **MCP Server stdio** (`docling_mcp.server`): Usato da Cursor/Claude Desktop per tool integration
- **MCP HTTP Server** (`docling_mcp.http_server`): Usato per observability, monitoring, Kubernetes probes

**Documentazione completa:**

- `docs/performance-optimization-guide.md` - Guida tecnica dettagliata
- `docs/optimization-summary.md` - Analisi risultati
- `docs/optimization-deployment.md` - Deploy guide
- `docs/health-check-endpoints.md` - Documentazione completa health checks

## 🤖 Code Quality & CI/CD

### GitHub MCP Server (Development Standard)

Il progetto utilizza il **GitHub MCP Server** come standard per operazioni GitHub automatizzate in Cursor IDE.

**Configurazione `.cursor/mcp.json`:**

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-token>"
      }
    }
  }
}
```

**Funzionalità disponibili:**
- Branch management: `create_branch`, `list_branches`
- File operations: `push_files`, `create_or_update_file`
- Pull requests: `create_pull_request`, `merge_pull_request`
- Issues: `list_issues`, `issue_write`, `add_issue_comment`
- Code search: `search_code`, `search_repositories`

### CodeRabbit Integration

Il repository utilizza [CodeRabbit](https://coderabbit.ai) per code review AI-powered automatica su ogni pull request.

**Funzionalità:**
- ✅ Review automatica su ogni PR
- 📝 Suggerimenti inline e best practices
- 🔒 Security analysis automatica
- 📊 High-level summary delle modifiche

### CI/CD Pipeline

GitHub Actions esegue automaticamente su ogni PR e push a `main`/`develop`:

| Job | Descrizione | Tool |
|-----|-------------|------|
| **lint** | Linting e format check | Ruff |
| **type-check** | Type checking statico | Mypy |
| **test** | Unit/integration tests con coverage >70% | Pytest |
| **build** | Docker image build validation (<500MB) | Docker Buildx |
| **health-check** | Health check validation per tutti i servizi | Docker Compose + curl |
| **secret-scan** | Secret scanning preventivo | TruffleHog OSS |

## 📚 Developer Resources

### Documentation

- **[Architecture](./docs/architecture.md)**: Complete system architecture, design decisions, and component descriptions
- **[Coding Standards](./docs/coding-standards.md)**: Code style guide, naming conventions, documentation standards, and best practices
- **[Testing Strategy](./docs/testing-strategy.md)**: TDD workflow, test organization, RAGAS evaluation, and CI/CD integration
- **[Development Guide](./docs/development-guide.md)**: Setup instructions, development workflow, and troubleshooting
- **[Documentation Index](./docs/index.md)**: Complete documentation index with quick links and navigation

### Quick Links

- **Code Style**: See [Coding Standards](./docs/coding-standards.md) for Python style guide, type hints, error handling patterns
- **Writing Tests**: See [Testing Strategy](./docs/testing-strategy.md) for TDD approach, test organization, coverage requirements
- **Project Structure**: See [Unified Project Structure](./docs/unified-project-structure.md) for directory organization, file placement rules, epic mapping
- **Architecture Patterns**: See [Architecture](./docs/architecture.md) for design decisions, integration patterns, observability

---

## 📊 LangFuse Observability

Il MCP server include integrazione con **LangFuse** per tracciamento e osservabilità delle chiamate AI.

### Setup LangFuse

1. **Crea un account LangFuse:**

   - Cloud: [cloud.langfuse.com](https://cloud.langfuse.com)
   - Self-hosted: [docs.langfuse.com/self-hosting](https://langfuse.com/self-hosting)

2. **Configura le variabili d'ambiente:**

```env
# LangFuse Configuration (opzionale)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com  # Default, oppure URL self-hosted
```

3. **Restart il server MCP** - Le tracce appariranno automaticamente in LangFuse

### Funzionalità Tracing

- 🔍 **Tracciamento automatico** di tutte le chiamate MCP tools
- 📊 **Metadata dettagliati**: tool_name, query, limit, source
- ⏱️ **Timing e performance** per ogni operazione
- 🔄 **Graceful degradation**: il sistema funziona anche senza LangFuse

### Cost Tracking (Story 2.2)

Il sistema traccia automaticamente i costi di utilizzo API OpenAI:

- 💰 **Embedding cost tracking**: Costo per generazione embedding via `langfuse.openai` wrapper
- 📈 **Token counting automatico**: Input tokens per embedding, input/output tokens per LLM
- 💵 **Pricing aggiornato**: LangFuse SDK aggiorna automaticamente i prezzi OpenAI
- 📊 **Cost breakdown**: Visualizzazione costi separati per embedding e LLM generation

**Modelli e Pricing Tracciati:**

| Modello                  | Tipo         | Costo              |
| ------------------------ | ------------ | ------------------ |
| `text-embedding-3-small` | Embedding    | $0.00002/1K tokens |
| `gpt-4o-mini`            | LLM (input)  | $0.00015/1K tokens |
| `gpt-4o-mini`            | LLM (output) | $0.0006/1K tokens  |

**Come funziona:**

1. Il wrapper `langfuse.openai` sostituisce il client OpenAI diretto
2. Ogni chiamata API viene automaticamente tracciata con token count
3. I costi vengono calcolati usando i prezzi OpenAI correnti
4. Il cost breakdown è visibile nel dashboard LangFuse per ogni trace

**Nota:** Il cost tracking è automatico e non richiede codice aggiuntivo. Se LangFuse non è configurato, il sistema funziona normalmente senza tracking (graceful degradation).

### Performance Metrics (Story 2.3)

Il sistema espone metriche Prometheus per il monitoraggio delle performance tramite un server HTTP dedicato.

**Endpoint disponibili:**

| Endpoint   | Formato    | Descrizione                                        |
| ---------- | ---------- | -------------------------------------------------- |
| `/metrics` | Prometheus | Metriche in formato OpenMetrics (text/plain)       |
| `/health`  | JSON       | Health check con status servizi (ok/degraded/down) |

**Metriche Prometheus:**

| Metrica                           | Tipo      | Descrizione                                |
| --------------------------------- | --------- | ------------------------------------------ |
| `mcp_requests_total`              | Counter   | Totale richieste MCP (label: tool, status) |
| `mcp_request_duration_seconds`    | Histogram | Latenza richieste (buckets SLO-aligned)    |
| `rag_embedding_time_seconds`      | Histogram | Tempo generazione embedding                |
| `rag_db_search_time_seconds`      | Histogram | Tempo ricerca database                     |
| `rag_llm_generation_time_seconds` | Histogram | Tempo generazione LLM                      |
| `mcp_active_requests`             | Gauge     | Richieste attive concorrenti               |

**Configurazione Prometheus (`prometheus.yml`):**

```yaml
scrape_configs:
  - job_name: "docling-rag-agent"
    scrape_interval: 15s # Default raccomandato (60s per cost-sensitive)
    static_configs:
      - targets: ["localhost:8080"]
```

**Avvio server metriche:**

```bash
# Avvia il server HTTP per metriche e health check (porta 8080)
uv run python -m docling_mcp.http_server

# Oppure con porta personalizzata
METRICS_PORT=9090 uv run python -m docling_mcp.http_server
```

**Health Check Response:**

```json
{
  "status": "ok",
  "timestamp": 1732700400.123,
  "services": {
    "database": {
      "status": "up",
      "message": "PostgreSQL connection successful",
      "latency_ms": 5.2
    },
    "langfuse": {
      "status": "up",
      "message": "LangFuse client initialized",
      "latency_ms": 0.1
    },
    "embedder": {
      "status": "up",
      "message": "Embedder initialized and ready",
      "latency_ms": 0.5
    }
  }
}
```

**Status Logic:**

- `ok`: Tutti i servizi operativi
- `degraded`: LangFuse non disponibile (graceful degradation, MCP funziona)
- `down`: Database o embedder non disponibili (servizi critici)

### Visualizzazione Tracce

Nel dashboard LangFuse vedrai tracce per ogni chiamata tool:

| Tool                            | Metadata Tracciati                        |
| ------------------------------- | ----------------------------------------- |
| `query_knowledge_base`          | query, limit, source_filter, source="mcp" |
| `ask_knowledge_base`            | question, limit, source="mcp"             |
| `list_knowledge_base_documents` | limit, offset, source="mcp"               |
| `get_knowledge_base_document`   | document_id, source="mcp"                 |
| `get_knowledge_base_overview`   | source="mcp"                              |

**Nota:** Se le variabili LangFuse non sono configurate, il server funziona normalmente senza tracing (graceful degradation).

### LangFuse Dashboard (Story 2.4)

Il dashboard LangFuse fornisce una visualizzazione real-time delle performance e dei costi del MCP server.

**Metriche Dashboard:**

| Metrica       | Descrizione                    | Fonte                  |
| ------------- | ------------------------------ | ---------------------- |
| Total Queries | Numero totale richieste        | Conteggio trace        |
| Avg Latency   | Latenza media                  | Campo `latency` trace  |
| Total Cost    | Costo totale (embedding + LLM) | Token usage automatico |

**Visualizzazioni Disponibili:**

- **Cost Trends**: Grafico costi nel tempo (daily/weekly/monthly)
- **Latency Distribution**: Distribuzione latenza per tool
- **Trace Detail View**: Input, output, cost breakdown, timing breakdown, nested spans

**Trace Detail View:**

Ogni trace mostra:

- Input query text
- Output response
- Cost breakdown: `embedding_cost` + `llm_generation_cost`
- Timing breakdown: `embedding_time`, `db_search_time`, `llm_generation_time`
- Nested spans: `embedding-generation`, `vector-search`, `llm-generation`

**Custom Charts:**

LangFuse supporta chart personalizzati configurabili con:

- Dimensioni: `time`, `tool_name`, `metadata.source`
- Metriche: `count`, `totalCost`, `avgLatency`, `p95Latency`

**Guida Completa:** Consulta [docs/langfuse-dashboard-guide.md](./docs/langfuse-dashboard-guide.md) per la configurazione dettagliata del dashboard.

## Ottimizzazione delle Prestazioni

### 🎯 Performance Optimizations (2025-11)

Il sistema è stato ottimizzato per performance reattive:

**Ottimizzazioni Applicate:**

1. **HNSW Vector Index** (Critical)
   - Upgrade da IVFFlat (`lists=1`) a HNSW
   - 10-100x più veloce per ricerche vettoriali
   - Performance consistente al crescere del dataset
2. **Global Embedder Instance**

   - Embedder singleton con cache persistente
   - Eliminato overhead 300-500ms per query
   - Cache hit rate: 66%

3. **Connection Pool Ottimizzato**

   ```python
   db_pool = await asyncpg.create_pool(
       DATABASE_URL,
       min_size=2,              # Ottimizzato per MCP burst traffic
       max_size=10,             # Sufficient per concurrent queries
       statement_cache_size=100 # Prepared statements abilitati
   )
   ```

4. **Performance Instrumentation**
   - Timing breakdown dettagliato per componente
   - Monitoring logs: `embedding_ms | db_ms | total_ms`

**Performance Baseline:**

| Metrica      | Before    | After   | Improvement |
| ------------ | --------- | ------- | ----------- |
| Avg Query    | 3563ms    | 1395ms  | **-61%**    |
| Cached Query | 298ms     | 237ms   | **-20%**    |
| DB Search    | 100-300ms | 20-60ms | **-75%**    |

**Performance Tools:**

```bash
# Verifica status DB index
python scripts/optimize_database.py --check

# Applica ottimizzazioni (upgrade HNSW index)
python scripts/optimize_database.py --apply

# Test performance
python scripts/test_mcp_performance.py
```

### Cache Embedding

L'embedder include caching LRU (2000 entries) per query frequenti, riducendo chiamate OpenAI API del 60-70%.

### Risposte in Streaming

Lo streaming token-per-token fornisce feedback immediato:

```python
async with agent.run_stream(user_input, message_history=history) as result:
    async for text in result.stream_text(delta=False):
        print(f"\rAssistant: {text}", end="", flush=True)
```

## Funzionalità Avanzate

### Filtraggio per Fonte Documentale

L'agente supporta il **filtraggio intelligente** delle ricerche per fonte specifica, permettendo di isolare documentazioni diverse.

**Come funziona:**
L'utente può richiedere informazioni da fonti specifiche e l'agente applica automaticamente il filtro appropriato.

**Esempi di query:**

| Query Utente                                               | Comportamento Agente                                 |
| ---------------------------------------------------------- | ---------------------------------------------------- |
| "Come fare il deploy?"                                     | Cerca in tutta la knowledge base                     |
| "Come fare il deploy di Docling usando solo Docling docs?" | Filtra automaticamente su `source_filter="docling"`  |
| "Spiega il tracing in Langfuse, non guardare altre fonti"  | Filtra su `source_filter="langfuse-docs"`            |
| "Deployment secondo Langfuse deployment docs"              | Filtra su `source_filter="langfuse-docs/deployment"` |

**Vantaggi:**

- 🎯 **Risposte precise** da fonti specifiche
- 🚫 **Zero contaminazione** tra documentazioni diverse
- 🤖 **Completamente automatico** - l'agente riconosce l'intento
- 📁 **Pattern flessibile** - supporta percorsi parziali

**Query SQL con filtro:**

```sql
SELECT c.content, d.title, d.source
FROM chunks c
JOIN documents d ON c.document_id = d.id
WHERE d.source ILIKE '%docling%'  -- Filtro applicato
ORDER BY c.embedding <=> query_embedding
```

## Deploy Docker

### Prerequisiti Docker

- Docker Desktop 24.0+ ([download](https://www.docker.com/products/docker-desktop/))
- Docker Compose v2.0+ (incluso in Docker Desktop)

### Quick Start Docker (~2 minuti)

**Avviare l'applicazione completa:**

```bash
# Build e avvia tutti i servizi
docker compose build
docker compose up -d

# Visualizza i log dei servizi
docker compose logs -f rag-api      # API Server (porta 8000)
docker compose logs -f mcp-server  # MCP HTTP Server (porta 8080)
docker compose logs -f streamlit    # Streamlit UI (porta 8501)
docker compose logs -f db           # Database PostgreSQL

# Verifica stato di tutti i servizi
docker compose ps
```

**Servizi disponibili:**

- **Streamlit UI**: `http://localhost:8501`
- **API Server**: `http://localhost:8000` (health: `/health`)
- **MCP HTTP Server**: `http://localhost:8080` (health: `/health`, metrics: `/metrics`)
- **Database**: `localhost:5432`

**Verifica Health Checks:**

```bash
# API Server
curl http://localhost:8000/health

# MCP Server
curl http://localhost:8080/health

# Streamlit
curl http://localhost:8501/_stcore/health
```

**Ingestione documenti con Docker:**

```bash
# Default: CANCELLA il DB e reingerisce tutto (raccomandato)
docker-compose --profile ingestion up ingestion

# AGGIUNGERE documenti senza cancellare (può creare duplicati)
# Usa il doppio slash per Windows + Git Bash
docker-compose run --rm ingestion uv run python -m ingestion.ingest --documents //app/documents --no-clean

# Con opzioni personalizzate
docker-compose run --rm ingestion uv run python -m ingestion.ingest \
  --documents /app/documents \
  --chunk-size 800 \
  --verbose
```

**⚠️ Nota:** Il comando default **cancella automaticamente** tutti i dati esistenti prima dell'ingestione per evitare duplicati. Usa `--no-clean` solo se vuoi aggiungere nuovi documenti senza toccare quelli esistenti.

**Comandi utili:**

```bash
# Ferma tutti i servizi
docker compose down

# Ferma e rimuovi volumi (ATTENZIONE: cancella dati database)
docker compose down -v

# Ricostruisci le immagini dopo modifiche al codice
docker compose build

# Ricostruisci solo un servizio specifico
docker compose build mcp-server

# Visualizza i container attivi
docker compose ps

# Accedi al container per debugging
docker compose exec rag-api bash      # API Server
docker compose exec mcp-server bash   # MCP Server
docker compose exec streamlit bash    # Streamlit
docker compose exec db psql -U postgres -d ragdb  # Database
```

## Troubleshooting

### Problemi Comuni

| Problema                       | Causa                      | Soluzione                                                                        |
| ------------------------------ | -------------------------- | -------------------------------------------------------------------------------- |
| `connection refused`           | Database non raggiungibile | Verifica `DATABASE_URL` e che PostgreSQL sia attivo                              |
| `extension "vector" not found` | PGVector non installato    | Esegui `CREATE EXTENSION vector;` o usa immagine Docker `pgvector/pgvector:pg16` |
| `OPENAI_API_KEY not set`       | Variabile mancante         | Aggiungi `OPENAI_API_KEY` nel file `.env`                                        |
| `uv: command not found`        | UV non installato          | Installa: `curl -LsSf https://astral.sh/uv/install.sh \| sh`                     |
| `Python version mismatch`      | Python < 3.10              | Aggiorna Python a 3.10+                                                          |
| `ImportError: docling`         | Dipendenze mancanti        | Esegui `uv sync`                                                                 |

### Connessione Database

```bash
# Verifica connessione
psql $DATABASE_URL -c "SELECT 1"

# Verifica estensione PGVector
psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname = 'vector'"

# Test performance index
python scripts/optimize_database.py --check
```

### Reset Ambiente

```bash
# Rimuovi cache e reinstalla
rm -rf .venv
uv sync

# Reset database (ATTENZIONE: cancella tutti i dati)
psql $DATABASE_URL < sql/optimize_index.sql
```

## Riferimento API

### Tool search_knowledge_base

```python
async def search_knowledge_base(
    ctx: RunContext[None],
    query: str,
    limit: int = 5,
    source_filter: str | None = None
) -> str:
    """
    Cerca nella knowledge base usando similarità semantica.

    Args:
        query: La query di ricerca per trovare informazioni rilevanti
        limit: Numero massimo di risultati da restituire (default: 5)
        source_filter: Filtro opzionale per cercare solo in fonti specifiche
                      Esempi: "docling", "langfuse-docs", "langfuse-docs/deployment"
                      Se fornito, verranno cercati solo documenti il cui percorso
                      sorgente contiene questa stringa

    Returns:
        Risultati di ricerca formattati con citazioni delle fonti
    """
```

**Esempi di utilizzo del filtro:**

```python
# Cerca in tutta la knowledge base
await search_knowledge_base(query="come fare il deploy")

# Cerca solo nella documentazione Docling
await search_knowledge_base(
    query="come fare il deploy",
    source_filter="docling"
)

# Cerca solo nella sezione deployment di Langfuse
await search_knowledge_base(
    query="deployment cloud",
    source_filter="langfuse-docs/deployment"
)
```

**Come funziona il filtro:**

- L'agente riconosce automaticamente quando l'utente specifica una fonte
- Applica il filtro usando pattern matching case-insensitive
- Utile per separare documentazioni diverse (Docling, Langfuse, ecc.)
- Previene contaminazione cross-documentazione nelle risposte

### Funzioni Database

```sql
-- Ricerca similarità vettoriale
SELECT * FROM match_chunks(
    query_embedding::vector(1536),
    match_count INT,
    similarity_threshold FLOAT DEFAULT 0.7
)
```

Restituisce chunk con:

- `id`: UUID del chunk
- `content`: Contenuto testuale
- `embedding`: Embedding vettoriale
- `similarity`: Punteggio similarità coseno (0-1)
- `document_title`: Titolo documento sorgente
- `document_source`: Percorso documento sorgente

## 📚 Documentazione

La documentazione completa del progetto, inclusa l'API reference, è disponibile in `guide/`.

### Visualizzazione Locale

Puoi avviare un server locale per navigare la documentazione:

```bash
# Avvia il server di documentazione
uv run mkdocs serve
```

La documentazione sarà accessibile a `http://127.0.0.1:8000`.

### Generazione Statica

Per generare la documentazione statica (HTML):

```bash
# Genera la documentazione in site/
uv run mkdocs build
```

### GitHub Pages

La documentazione viene automaticamente pubblicata su GitHub Pages ad ogni push sul branch `main`.

## Struttura Progetto

```
docling-rag-agent/
├── app.py                         # Interfaccia web Streamlit
├── docling_mcp/                   # MCP server per Cursor IDE (standalone)
├── core/
│   ├── agent.py                   # PydanticAI agent wrapper
│   └── rag_service.py             # Core RAG logic (decoupled)
├── ingestion/
│   ├── ingest.py                  # Pipeline ingestione documenti
│   ├── embedder.py                # Generazione embedding con caching
│   └── chunker.py                 # Chunking intelligente (Docling HybridChunker)
├── utils/
│   ├── providers.py               # Configurazione modelli/client OpenAI
│   ├── db_utils.py                # Connection pooling ottimizzato
│   └── models.py                  # Modelli Pydantic per validazione
├── sql/
│   └── optimize_index.sql         # Schema completo + HNSW index ottimizzato
├── scripts/
│   ├── optimize_database.py       # Tool gestione index e performance
│   └── test_mcp_performance.py    # Performance test suite
├── docs/
│   ├── optimization-summary.md    # Analisi performance optimization
│   ├── performance-optimization-guide.md
│   └── optimization-deployment.md
├── documents/                     # Documenti per ingestione
├── pyproject.toml                 # Dipendenze progetto (uv)
├── .env.example                   # Template variabili d'ambiente
└── README.md                      # Questo file
```
