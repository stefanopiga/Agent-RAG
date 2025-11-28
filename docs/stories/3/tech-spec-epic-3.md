# Epic Technical Specification: Streamlit UI Observability

Date: 2025-01-27
Author: Stefano
Epic ID: 3
Status: Draft

---

## Overview

Epic 3 estende il monitoring LangFuse implementato in Epic 2 alla Streamlit UI, fornendo session tracking completo e cost visibility per utenti. Questo epic trasforma l'interfaccia Streamlit da sistema senza visibilità a sistema production-ready con tracciamento completo di ogni sessione utente, calcolo accurato dei costi per sessione, e visualizzazione real-time delle statistiche nella sidebar. L'implementazione si basa sul pattern LangFuse decorator-based già stabilito in Epic 2, riutilizzando la logica di cost tracking e integrando session management tramite `st.session_state` di Streamlit. Epic 3 completa l'observability del sistema RAG fornendo visibilità sia per MCP server (Epic 2) che per Streamlit UI, abilitando analisi comparative delle performance e dei costi tra le due interfacce.

## Objectives and Scope

**In-Scope:**

- Generazione session_id univoco per ogni sessione Streamlit tramite `st.session_state`
- Logging di ogni query utente con session_id, timestamp, e costo calcolato
- Visualizzazione statistiche sessione nella sidebar (query count, total cost, avg latency)
- Integrazione LangFuse tracing per query Streamlit con metadata `source: streamlit`
- Tagging trace LangFuse con session_id per analisi comportamentale
- Separazione query MCP vs Streamlit nel dashboard LangFuse tramite filtro `source`
- Storage session data in PostgreSQL per persistenza e analisi storica
- Calcolo costi cumulativi per sessione riutilizzando logica Epic 2
- Context injection LangFuse con session_id metadata (user_agent non disponibile in Streamlit)

**Out-of-Scope:**

- Autenticazione utenti o multi-tenancy (sistema single-user)
- Export report costi per sessione (Epic 2 già fornisce export generale)
- Dashboard Streamlit avanzata con grafici (LangFuse dashboard è sufficiente)
- Notifiche real-time o alerting (monitoring passivo)
- Modifiche al core RAG logic (solo integrazione observability)

**Security Hardening (Documentato Separatamente):**

- Cost protection e enforcement (cost monitoring con threshold) - Documentato in `epic-3-security-hardening-guide.md`
- Rate limiting Streamlit (prevenzione abuse) - Documentato in `epic-3-security-hardening-guide.md`
- Network security (VPN/IP whitelist) - Documentato in `epic-3-security-hardening-guide.md`
- Streamlit authentication opzionale - Documentato in `epic-3-security-hardening-guide.md`

**Nota:** Epic 3 include cost tracking e session monitoring, ma le protezioni di sicurezza avanzate (cost enforcement, rate limiting, network security) sono documentate nella Security Hardening Guide per uso privato. Implementazione opzionale ma fortemente raccomandata per deployment pubblico o condiviso.

## System Architecture Alignment

Epic 3 si allinea all'architettura esistente seguendo il pattern **Agent Wrapper Integration** già definito per Streamlit → Core Agent. L'implementazione estende `app.py` con session tracking e LangFuse integration senza modificare `core/rag_service.py` o `core/agent.py`. Il sistema riutilizza:

- **LangFuse Integration Pattern** (ADR-001): Decorator `@observe()` già implementato in Epic 2 per funzioni RAG, Epic 3 aggiunge `langfuse.start_as_current_observation()` con `propagate_attributes()` per trace root Streamlit
- **Cost Tracking Pattern**: Logica cost tracking Epic 2 riutilizzata tramite `langfuse.openai` wrapper
- **Session Management Pattern**: `st.session_state` per session_id persistence (già documentato in architecture.md)
- **Database Storage**: PostgreSQL esistente utilizzato per session data storage (tabella `sessions` da creare)

Componenti coinvolti:

- `app.py`: Entry point Streamlit, esteso con session tracking e LangFuse tracing
- `core/agent.py`: PydanticAI agent wrapper, già esistente, nessuna modifica richiesta
- `core/rag_service.py`: Core RAG logic, già tracciato in Epic 2, riutilizzato
- `utils/db_utils.py`: Connection pool PostgreSQL, riutilizzato per session storage
- LangFuse SDK: Client già inizializzato in Epic 2, riutilizzato con context injection

Vincoli architetturali:

- Nessuna modifica a `core/rag_service.py` (solo integrazione observability)
- Pattern LangFuse context injection (`propagate_attributes()`) per consistenza con Epic 2, trace root Streamlit separato da nested spans RAG
- Graceful degradation se LangFuse non disponibile (sistema continua a funzionare)

## Detailed Design

### Services and Modules

| Service/Module                          | Responsibility                                     | Inputs                       | Outputs                      | Owner             |
| --------------------------------------- | -------------------------------------------------- | ---------------------------- | ---------------------------- | ----------------- |
| `app.py` (Streamlit UI)                 | Session management, UI rendering, LangFuse tracing | User queries, session state  | RAG responses, sidebar stats | Epic 3            |
| `core/agent.py`                         | PydanticAI agent wrapper (no changes)              | Query text                   | Agent response               | Epic 1 (baseline) |
| `core/rag_service.py`                   | Core RAG logic (no changes, already traced)        | Query, limit                 | Search results               | Epic 2            |
| `utils/session_manager.py` (NEW)        | Session ID generation, session data persistence    | Session state                | session_id, session stats    | Epic 3            |
| `utils/langfuse_streamlit.py` (NEW)     | LangFuse context injection per Streamlit           | session_id, query            | LangFuse trace               | Epic 3            |
| `utils/cost_monitor.py` (NEW, Optional) | Cost monitoring e enforcement threshold            | session_id, cost             | allowed/blocked, alert       | Epic 3 (Security) |
| `utils/rate_limiter.py` (NEW, Optional) | Rate limiting per prevenzione abuse                | session_id, request          | allowed/blocked              | Epic 3 (Security) |
| PostgreSQL `sessions` table (NEW)       | Session data storage                               | session_id, query_log, costs | Session statistics           | Epic 3            |

**Module Details:**

**`app.py` (Extended):**

- Initialize session_id in `st.session_state` se non esiste
- Wrap `run_agent()` con LangFuse tracing e context injection
- Update sidebar con statistiche sessione (query count, total cost, avg latency)
- Log ogni query con session_id, timestamp, costo

**`utils/session_manager.py` (NEW):**

- `generate_session_id()`: Genera UUID v4 per session_id
- `get_session_stats(session_id)`: Recupera statistiche da PostgreSQL
- `log_query(session_id, query, cost, latency)`: Persiste query log in DB
- `calculate_session_cost(session_id)`: Aggrega costi per sessione

**`utils/langfuse_streamlit.py` (NEW):**

- `with_streamlit_context(session_id, query)`: Context manager per LangFuse context injection usando `propagate_attributes()`
- `trace_streamlit_query(query, session_id)`: Wrapper per tracing query Streamlit
- Metadata: `source: streamlit`, `session_id` (user_agent non disponibile in Streamlit)
- **Riferimento:** https://langfuse.com/docs/observability/sdk/python/instrumentation#propagating-trace-attributes

**`utils/cost_monitor.py` (NEW, Optional - Security Hardening):**

- `CostMonitor`: Classe per monitoring costi con threshold enforcement
- `check_daily_cost(session_id)`: Verifica limite giornaliero
- `check_hourly_cost(session_id)`: Verifica limite orario
- `enforce_cost_limits(session_id)`: Blocca query se threshold superato
- Configurazione via env: `COST_DAILY_LIMIT`, `COST_HOURLY_LIMIT`, `COST_ALERT_THRESHOLD`

**`utils/rate_limiter.py` (NEW, Optional - Security Hardening):**

- `RateLimiter`: Classe per rate limiting in-memory o Redis-based
- `check_rate_limit(identifier)`: Verifica limite richieste per sessione/IP
- Decorator `@rate_limit_decorator`: Applicabile a funzioni Streamlit
- Configurazione: max_requests per window_seconds (default: 20/minuto)

### Data Models and Contracts

**PostgreSQL Schema (NEW):**

```sql
-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    query_count INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0.0,
    total_latency_ms DECIMAL(10, 2) DEFAULT 0.0
);

-- Query logs table
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    response_text TEXT,
    cost DECIMAL(10, 6) NOT NULL,
    latency_ms DECIMAL(10, 2) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    langfuse_trace_id VARCHAR(255)
);

-- Indexes
CREATE INDEX idx_query_logs_session_id ON query_logs(session_id);
CREATE INDEX idx_query_logs_timestamp ON query_logs(timestamp);
CREATE INDEX idx_sessions_last_activity ON sessions(last_activity);
```

**Pydantic Models (`utils/models.py` - Extended):**

```python
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from uuid import UUID

class SessionStats(BaseModel):
    session_id: UUID
    query_count: int
    total_cost: Decimal
    avg_latency_ms: Decimal
    created_at: datetime
    last_activity: datetime

class QueryLog(BaseModel):
    session_id: UUID
    query_text: str
    response_text: str | None
    cost: Decimal
    latency_ms: Decimal
    timestamp: datetime
    langfuse_trace_id: str | None
```

### APIs and Interfaces

**Streamlit UI Interface:**

- **Session Initialization**: Automatico al primo accesso a `app.py`

  - Genera `session_id` se `st.session_state.session_id` non esiste
  - Crea record in `sessions` table PostgreSQL

- **Query Processing**: Wrapper `run_agent()` con LangFuse tracing

  - Input: `query: str` (da chat input)
  - Output: `response_text: str` (risposta agent)
  - Side effects: Log query in `query_logs`, update `sessions` stats

- **Sidebar Statistics**: Visualizzazione real-time
  - Query count: `session_stats.query_count`
  - Total cost: `session_stats.total_cost` (formattato come "$0.00XX")
  - Avg latency: `session_stats.avg_latency_ms` (formattato come "XXXms")

**LangFuse Integration Interface:**

- **Context Injection**: `with_streamlit_context(session_id, query)`

  - Sets LangFuse trace attributes: `session_id`, `source: streamlit` (user_agent non disponibile in Streamlit)
  - Propagates attributes to child observations (embedding, DB, LLM spans) usando `propagate_attributes()` context manager
  - **Riferimento:** https://langfuse.com/docs/observability/sdk/python/instrumentation#propagating-trace-attributes

  **Esempio implementativo (basato su documentazione ufficiale LangFuse):**

  ```python
  from langfuse import get_client, propagate_attributes
  from uuid import UUID

  langfuse = get_client()
  session_id = UUID("...")
  query = "What is the main topic?"

  with langfuse.start_as_current_observation(
      as_type="span",
      name="streamlit_query",
      input={"query": query}
  ) as root_span:
      # Propagate session_id to all child observations
      with propagate_attributes(
          session_id=str(session_id),
          metadata={"source": "streamlit"}
      ):
          # All nested observations automatically inherit session_id
          result = await run_agent(query)
          # embedding-generation, vector-search, llm-generation spans
          # all automatically have session_id attribute
          trace_id = root_span.trace_id  # Per estrazione costi post-esecuzione
  ```

  **Nota:** `with_streamlit_context()` wrapper implementa questo pattern internamente (vedi `utils/langfuse_streamlit.py`).

- **Trace Creation**: Automatico tramite `langfuse.start_as_current_observation()` con `propagate_attributes()`
  - Trace name: `streamlit_query`
  - Metadata: `{"source": "streamlit", "session_id": "..."}` (user_agent non disponibile in Streamlit)
  - Nested spans: `embedding-generation`, `vector-search`, `llm-generation` (da Epic 2)
  - **Riferimento:** https://langfuse.com/docs/observability/sdk/python/instrumentation#propagating-trace-attributes

**Database Interface:**

- **Session Storage**: `utils/session_manager.py`
  - `create_session(session_id: UUID)`: Crea nuovo record in `sessions`
  - `update_session_stats(session_id: UUID, cost: Decimal, latency_ms: Decimal)`: Aggiorna statistiche
  - `get_session_stats(session_id: UUID) -> SessionStats`: Recupera statistiche

### Workflows and Sequencing

**Session Lifecycle:**

1. **User opens Streamlit app** (`app.py` loads)

   - Check `st.session_state.session_id`
   - If missing: Generate UUID v4 → Store in `st.session_state.session_id`
   - Create record in `sessions` table PostgreSQL (async)

2. **User submits query** (chat input)

   - Capture query text
   - **Security Check (Optional):** Rate limiting check (`rate_limiter.check_rate_limit()`)
   - **Security Check (Optional):** Cost limit check (`cost_monitor.enforce_cost_limits()`)
   - Start timing: `start_time = time.time()`
   - Initialize LangFuse context: `with_streamlit_context(session_id, query)`
   - Call `run_agent(query)` (già tracciato con `@observe()` da Epic 2, session_id propagato automaticamente)
   - Calculate latency: `latency_ms = (time.time() - start_time) * 1000`
   - Extract cost from LangFuse trace via API SDK post-esecuzione (`langfuse.api.trace.get(trace_id)`, somma `calculated_total_cost` da observations tipo GENERATION)
   - Log query: `log_query(session_id, query, cost, latency_ms)`
   - Update session stats: `update_session_stats(session_id, cost, latency_ms)`
   - Display response in chat

3. **Sidebar refresh** (on every rerun)
   - Query `get_session_stats(session_id)` from PostgreSQL
   - Display: query count, total cost, avg latency
   - Format: Human-readable (cost as "$0.00XX", latency as "XXXms")

**LangFuse Trace Flow:**

```
User Query (Streamlit)
  └─> langfuse.start_as_current_observation(name="streamlit_query") [Trace Root]
      ├─> propagate_attributes(session_id="...", metadata={"source": "streamlit"})
      └─> run_agent(query)
          └─> @observe(name="search_knowledge_base") [Nested Span]
              ├─> embedding-generation span (cost tracked, session_id propagato)
              ├─> vector-search span (timing tracked, session_id propagato)
              └─> llm-generation span (cost tracked, session_id propagato)
```

**Error Handling:**

- LangFuse unavailable: Graceful degradation, sistema continua senza tracing
- PostgreSQL unavailable: Fallback a in-memory storage (`st.session_state` only)
- Session creation failure: Log warning, continue senza persistenza

## Non-Functional Requirements

### Performance

- **Session ID Generation**: < 1ms (UUID v4 generation)
- **Session Stats Query**: < 50ms (PostgreSQL query con index su `session_id`)
- **Query Logging**: < 10ms (async insert, non-blocking)
- **Sidebar Refresh**: < 100ms (cached stats in `st.session_state`, refresh ogni 5s)
- **LangFuse Context Injection**: < 5ms overhead (`propagate_attributes()` context manager, minimal overhead)

**Targets Alignment:**

- Epic 3 non impatta latency query RAG (solo observability overhead)
- Overhead totale < 100ms per query (accettabile per UI)

### Security

- **Session ID**: UUID v4 (non-guessable, sufficiente per single-user system)
- **Query Logs**: No PII in logs (solo query text, no user identification)
- **Database Access**: Connection pool riutilizzato da `utils/db_utils.py` (già sicuro)
- **LangFuse Keys**: Environment variables (già configurato in Epic 2)
- **RLS Supabase**: Row Level Security abilitato su tabelle `sessions` e `query_logs` (policies `service_role` only)

**Security Hardening (Opzionale ma Raccomandato):**

- **Cost Protection**: Cost monitoring con threshold enforcement (`utils/cost_monitor.py`)

  - Limite giornaliero configurabile (default: $10/giorno)
  - Limite orario configurabile (default: $2/ora)
  - Blocco automatico query se threshold superato
  - Alert logging su costi anomali
  - Variabili env: `COST_DAILY_LIMIT`, `COST_HOURLY_LIMIT`, `COST_ALERT_THRESHOLD`

- **Rate Limiting**: Prevenzione abuse/DDoS (`utils/rate_limiter.py`)

  - Limite richieste per sessione/IP (default: 20/minuto)
  - In-memory (semplice) o Redis-based (persistente)
  - Decorator pattern per integrazione trasparente

- **Network Security**: Protezione a livello network (documentato in Security Hardening Guide)

  - VPN only access (raccomandato per uso privato)
  - IP whitelist via reverse proxy (Nginx)
  - Firewall rules per porta 8501
  - Streamlit config: `address = "127.0.0.1"` per localhost-only

- **Streamlit Authentication**: Password protection opzionale (`utils/streamlit_auth.py`)
  - Hash SHA256 password (non plaintext)
  - Sufficiente per uso privato, non production-grade
  - Variabile env: `STREAMLIT_PASSWORD_HASH`

**Security Notes:**

- Nessuna autenticazione richiesta per MVP (sistema single-user)
- Session data non contiene informazioni sensibili
- Query logs possono contenere dati documentali (non critico per MVP)
- **Rischio principale**: Cost explosion da attacchi esterni se Streamlit esposto pubblicamente
- **Mitigazione**: Implementare cost protection e network security per deployment pubblico/condiviso

**Riferimenti:**

- Security Hardening Guide: `docs/stories/3/epic-3-security-hardening-guide.md`
- Documentation Gaps Analysis: `docs/stories/3/epic-3-documentation-gaps-analysis.md`
- Supabase RLS Setup: `sql/epic-3-sessions-schema.sql`

### Reliability/Availability

- **Graceful Degradation**: Sistema funziona anche se LangFuse o PostgreSQL non disponibili
- **Session Persistence**: Fallback a `st.session_state` se DB unavailable
- **Error Recovery**: Logging errori senza interrompere user experience
- **Session Cleanup**: TTL opzionale per sessioni inattive (future enhancement)

**Availability Targets:**

- Streamlit UI: 99.5% uptime (allineato Epic 2)
- Session tracking: Degraded mode se DB down (stats solo in-memory)

### Observability

- **LangFuse Tracing**: 100% query Streamlit tracciate con session_id
- **Session Metrics**: Query count, total cost, avg latency per sessione
- **Trace Filtering**: Filtro `source: streamlit` nel dashboard LangFuse
- **Logging**: JSON structured logging per session events (allineato Epic 2)

**Observability Signals:**

- LangFuse traces con metadata `source: streamlit`
- PostgreSQL `query_logs` table per analisi storica
- Sidebar stats per real-time visibility utente

## Dependencies and Integrations

**Dependencies:**

- **Streamlit**: 1.28+ (già installato, `st.session_state` API, versione minima verificata)
- **LangFuse Python SDK**: 3.0.0+ (già installato in Epic 2)
- **PostgreSQL**: 16+ con PGVector (già configurato)
- **AsyncPG**: 0.29.0+ (già installato per connection pooling, versione minima verificata compatibile con PostgreSQL 16+)
- **UUID**: Standard library Python (`uuid.uuid4()`)

**Optional Dependencies (Security Hardening):**

- **Redis**: Opzionale per rate limiting persistente (`redis` package)
  - Solo se si usa `utils/rate_limiter_redis.py` invece di `utils/rate_limiter.py` (in-memory)
  - Variabile env: `REDIS_URL` (default: `redis://localhost:6379`)

**Integrations:**

- **LangFuse Client**: Riutilizzato da Epic 2, nessuna nuova inizializzazione
- **PostgreSQL Connection Pool**: Riutilizzato da `utils/db_utils.py`
- **Core RAG Service**: Nessuna modifica, già tracciato in Epic 2
- **PydanticAI Agent**: Nessuna modifica, wrapper esistente

**Version Constraints:**

- Nessuna nuova dipendenza richiesta (tutte già presenti)
- Compatibilità garantita con Epic 2 (stesso LangFuse SDK version)
- **Nota:** Versioni minime verificate e dettagli implementativi documentati in `docs/stories/3/epic-3-documentation-gaps-analysis.md`

**Riferimenti Documentazione Ufficiale:**

- LangFuse Context Injection: https://langfuse.com/docs/observability/sdk/python/instrumentation#propagating-trace-attributes
- LangFuse Cost Tracking: https://langfuse.com/docs/observability/features/token-and-cost-tracking
- LangFuse Query Data via SDK: https://langfuse.com/guides/cookbook/example_query_data_via_sdk
- Streamlit Session State: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state

## Acceptance Criteria (Authoritative)

1. **AC3.1.1**: Dato una sessione Streamlit, quando l'app viene aperta, allora un `session_id` univoco UUID v4 è generato e memorizzato in `st.session_state.session_id`

2. **AC3.1.2**: Dato un `session_id` generato, quando la sessione viene inizializzata, allora un record è creato nella tabella `sessions` PostgreSQL con `session_id`, `created_at`, `last_activity`

3. **AC3.1.3**: Dato una query utente, quando viene inviata tramite chat input, allora è loggata nella tabella `query_logs` con `session_id`, `query_text`, `timestamp`, `cost`, `latency_ms`

4. **AC3.1.4**: Dato il calcolo del costo query, quando una query viene processata, allora il costo è estratto dal trace LangFuse (nested spans: embedding + LLM) e memorizzato in `query_logs.cost`

5. **AC3.1.5**: Dato l'aggiornamento statistiche sessione, quando una query viene loggata, allora `sessions.query_count`, `sessions.total_cost`, `sessions.total_latency_ms`, `sessions.last_activity` sono aggiornati

6. **AC3.1.6**: Dato la sidebar Streamlit, quando viene visualizzata, allora mostra: query count (`sessions.query_count`), total cost (`sessions.total_cost` formattato come "$0.00XX"), avg latency (`sessions.total_latency_ms / sessions.query_count` formattato come "XXXms")

7. **AC3.2.1**: Dato una query Streamlit, quando viene processata tramite `run_agent()`, allora un trace LangFuse è creato con nome `streamlit_query` e metadata `{"source": "streamlit", "session_id": "..."}` (user_agent non disponibile in Streamlit)

8. **AC3.2.2**: Dato il trace LangFuse, quando viene creato, allora il `session_id` è propagato a tutti i nested spans (embedding-generation, vector-search, llm-generation) tramite LangFuse context injection

9. **AC3.2.3**: Dato il dashboard LangFuse, quando viene filtrato per `source: streamlit`, allora mostra solo query provenienti da Streamlit UI (separate da query MCP)

10. **AC3.2.4**: Dato un trace LangFuse, quando viene visualizzato, allora i metadata mostrano: `session_id` (UUID), `source: streamlit`, `query_text` (testo query) (user_agent non disponibile in Streamlit)

11. **AC3.2.5**: Dato LangFuse non disponibile, quando una query viene processata, allora il sistema continua a funzionare senza tracing (graceful degradation)

12. **AC3.2.6**: Dato PostgreSQL non disponibile, quando una sessione viene inizializzata, allora il sistema usa solo `st.session_state` per storage in-memory (fallback mode)

**Security Acceptance Criteria (Optional - Security Hardening):**

13. **AC3.3.1**: Dato cost monitoring abilitato, quando una query viene processata e il costo giornaliero supera `COST_DAILY_LIMIT`, allora la query è bloccata con messaggio errore e nessun costo è accumulato

14. **AC3.3.2**: Dato cost monitoring abilitato, quando una query viene processata e il costo orario supera `COST_HOURLY_LIMIT`, allora la query è bloccata con messaggio errore e nessun costo è accumulato

15. **AC3.3.3**: Dato cost monitoring abilitato, quando il costo giornaliero raggiunge `COST_ALERT_THRESHOLD`, allora un warning è loggato (non blocca query)

16. **AC3.3.4**: Dato rate limiting abilitato, quando una sessione supera il limite di richieste per finestra temporale, allora le richieste successive sono bloccate con messaggio "Rate limit exceeded"

17. **AC3.3.5**: Dato RLS Supabase abilitato, quando un tentativo di accesso alle tabelle `sessions` o `query_logs` viene fatto con ruolo `anon`, allora nessuna riga è restituita (protezione completa)

## Traceability Mapping

| AC      | Spec Section                       | Component/API                                          | Test Idea                                                        |
| ------- | ---------------------------------- | ------------------------------------------------------ | ---------------------------------------------------------------- |
| AC3.1.1 | Services and Modules → app.py      | `st.session_state.session_id` initialization           | Unit test: Verify UUID v4 generation on first access             |
| AC3.1.2 | Data Models → Sessions table       | `utils/session_manager.py::create_session()`           | Integration test: Verify DB record creation                      |
| AC3.1.3 | Workflows → Query Processing       | `utils/session_manager.py::log_query()`                | Integration test: Verify query log insert                        |
| AC3.1.4 | Workflows → LangFuse Trace Flow    | Cost extraction from LangFuse trace                    | Integration test: Mock LangFuse trace, verify cost extraction    |
| AC3.1.5 | Workflows → Session Lifecycle      | `utils/session_manager.py::update_session_stats()`     | Integration test: Verify stats update after query                |
| AC3.1.6 | APIs → Sidebar Statistics          | Sidebar rendering in `app.py`                          | E2E test: Playwright verifica visualizzazione stats              |
| AC3.2.1 | Workflows → LangFuse Trace Flow    | `utils/langfuse_streamlit.py::trace_streamlit_query()` | Integration test: Verify trace creation con metadata             |
| AC3.2.2 | APIs → LangFuse Integration        | Context injection `with_streamlit_context()`           | Integration test: Verify session_id propagation to nested spans  |
| AC3.2.3 | Observability → LangFuse Tracing   | LangFuse dashboard filtering                           | Manual test: Verifica filtro `source: streamlit`                 |
| AC3.2.4 | APIs → LangFuse Integration        | Trace metadata structure                               | Integration test: Verify metadata fields presenti                |
| AC3.2.5 | Reliability → Graceful Degradation | LangFuse error handling                                | Integration test: Mock LangFuse failure, verify system continua  |
| AC3.2.6 | Reliability → Graceful Degradation | PostgreSQL fallback                                    | Integration test: Mock DB failure, verify in-memory fallback     |
| AC3.3.1 | Security → Cost Protection         | `utils/cost_monitor.py::enforce_cost_limits()`         | Integration test: Mock daily cost > limit, verify query blocked  |
| AC3.3.2 | Security → Cost Protection         | `utils/cost_monitor.py::check_hourly_cost()`           | Integration test: Mock hourly cost > limit, verify query blocked |
| AC3.3.3 | Security → Cost Protection         | `utils/cost_monitor.py::check_daily_cost()`            | Integration test: Mock cost = threshold, verify warning logged   |
| AC3.3.4 | Security → Rate Limiting           | `utils/rate_limiter.py::check_rate_limit()`            | Integration test: Mock 21 requests in 60s, verify 21st blocked   |
| AC3.3.5 | Security → RLS Supabase            | PostgreSQL RLS policies                                | Integration test: SET ROLE anon, verify 0 rows returned          |

## Risks, Assumptions, Open Questions

**Risks:**

1. **Risk: PostgreSQL Connection Overhead**

   - **Mitigation**: Async inserts non-blocking, connection pool riutilizzato
   - **Impact**: Basso (connection pool già ottimizzato Epic 2)

2. **Risk: LangFuse Trace Overhead**

   - **Mitigation**: Decorator pattern minimale overhead (< 5ms), async HTTP
   - **Impact**: Basso (già validato Epic 2)

3. **Risk: Session Data Growth**

   - **Mitigation**: TTL opzionale per cleanup sessioni inattive (future enhancement)
   - **Impact**: Medio (non critico per MVP, single-user system)

4. **Risk: Cost Explosion da Attacchi Esterni** ⚠️ **CRITICO**

   - **Scenario**: Streamlit esposto pubblicamente senza protezioni → attaccante fa migliaia di query → costi OpenAI esplosivi ($100+/giorno)
   - **Mitigation**:
     - Cost monitoring con enforcement (`utils/cost_monitor.py`) - **PRIORITÀ ALTA**
     - Rate limiting (`utils/rate_limiter.py`) - **PRIORITÀ MEDIA**
     - Network security (VPN/IP whitelist) - **PRIORITÀ ALTA**
     - Streamlit authentication opzionale se network security non sufficiente
   - **Impact**: **ALTO** se Streamlit esposto pubblicamente senza protezioni
   - **Documentazione**: `docs/stories/3/epic-3-security-hardening-guide.md`

5. **Risk: Abuse/DDoS senza Rate Limiting**

   - **Scenario**: Attaccante satura sistema con richieste massive → degradazione performance + costi elevati
   - **Mitigation**: Rate limiting in-memory o Redis-based (`utils/rate_limiter.py`)
   - **Impact**: Medio (mitigato con rate limiting)

**Assumptions:**

1. **Assumption: Single-User System**

   - **Rationale**: Nessuna autenticazione richiesta, session_id sufficiente per tracking
   - **Validation**: PRD conferma sistema single-user

2. **Assumption: Streamlit Session State Persistence**

   - **Rationale**: `st.session_state` persiste per durata sessione browser
   - **Validation**: Documentazione Streamlit conferma comportamento

3. **Assumption: LangFuse SDK Compatibility**
   - **Rationale**: Stesso SDK version Epic 2, nessun breaking change atteso
   - **Validation**: LangFuse SDK v3.0.0+ già verificato Epic 2

**Open Questions:**

1. **Question: Session TTL Policy**

   - **Status**: Deferred to future enhancement
   - **Decision**: Nessun TTL per MVP, cleanup manuale se necessario

2. **Question: Query Log Retention**

   - **Status**: Deferred to future enhancement
   - **Decision**: Nessun retention policy per MVP, storage illimitato

3. **Question: Sidebar Stats Refresh Rate**

   - **Status**: To be determined during implementation
   - **Decision**: Refresh on every rerun (Streamlit default), cache in `st.session_state` per performance

4. **Question: Security Hardening Implementation Priority**
   - **Status**: Documentato in Security Hardening Guide
   - **Decision**:
     - **Priorità ALTA**: Network security (VPN/IP whitelist) + Cost monitoring con enforcement
     - **Priorità MEDIA**: Rate limiting
     - **Priorità BASSA**: Streamlit authentication (solo se network security non sufficiente)
   - **Riferimento**: `docs/stories/3/epic-3-security-hardening-guide.md`

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests** (`tests/unit/test_session_manager.py`):

   - `test_generate_session_id()`: Verifica UUID v4 generation
   - `test_create_session()`: Verifica session creation logic
   - `test_calculate_session_cost()`: Verifica cost aggregation

2. **Integration Tests** (`tests/integration/test_streamlit_observability.py`):

   - `test_session_initialization()`: Verifica DB record creation
   - `test_query_logging()`: Verifica query log insert con cost/latency
   - `test_langfuse_trace_creation()`: Verifica trace creation con metadata
   - `test_session_stats_update()`: Verifica stats aggregation
   - `test_graceful_degradation_langfuse()`: Verifica fallback se LangFuse down
   - `test_graceful_degradation_db()`: Verifica fallback se PostgreSQL down

3. **E2E Tests** (`tests/e2e/test_streamlit_ui_observability.py`):

   - `test_sidebar_stats_display()`: Playwright verifica visualizzazione stats
   - `test_session_persistence()`: Verifica session_id persiste tra page reloads
   - `test_query_tracking()`: Verifica query logging end-to-end

4. **Security Tests** (`tests/integration/test_security_hardening.py`):
   - `test_cost_daily_limit_enforcement()`: Verifica AC3.3.1 - blocco query se costo giornaliero supera limite
   - `test_cost_hourly_limit_enforcement()`: Verifica AC3.3.2 - blocco query se costo orario supera limite
   - `test_cost_alert_threshold()`: Verifica AC3.3.3 - warning loggato quando raggiunge threshold
   - `test_rate_limit_enforcement()`: Verifica AC3.3.4 - blocco richieste se rate limit superato
   - `test_rls_supabase_protection()`: Verifica AC3.3.5 - protezione RLS su tabelle sessions e query_logs

**Test Coverage:**

- Target: > 70% coverage per `utils/session_manager.py`, `utils/langfuse_streamlit.py`, `utils/cost_monitor.py`, `utils/rate_limiter.py`
- Critical paths: Session initialization, query logging, stats update, LangFuse tracing, cost enforcement, rate limiting

**Test Data:**

- Mock LangFuse client per unit tests (no real API calls)
- Test database per integration tests (setup/teardown automatico)
- Golden dataset: N/A (Epic 3 non modifica RAG logic)

**CI/CD Integration:**

- Tests eseguiti in GitHub Actions CI (Epic 4)
- Coverage report generato automaticamente
- Fail build se coverage < 70%
