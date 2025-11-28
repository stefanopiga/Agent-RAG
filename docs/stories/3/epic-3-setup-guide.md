# Epic 3 - Setup Guide Supabase

**Data:** 2025-01-27  
**Epic:** Epic 3 - Streamlit UI Observability  
**Status:** Setup completato ✅

---

## Panoramica

Questa guida documenta il setup Supabase per Epic 3, inclusa la creazione delle tabelle `sessions` e `query_logs`, configurazione RLS, e verifica delle variabili d'ambiente.

**Riferimenti:**
- SQL Script: `sql/epic-3-sessions-schema.sql`
- Tech Spec: `docs/stories/3/tech-spec-epic-3.md`
- Security Guide: `docs/stories/3/epic-3-security-hardening-guide.md`
- Documentation Gaps Analysis: `docs/stories/3/epic-3-documentation-gaps-analysis.md`

---

## Setup Database

### 1. Creare Tabelle Session

**Passo 1:** Aprire SQL Editor in Supabase Dashboard

**Passo 2:** Eseguire script `sql/epic-3-sessions-schema.sql`

Lo script crea:
- Tabelle `sessions` e `query_logs`
- Indexes per performance
- RLS abilitato automaticamente
- Policies `service_role` only (protezione completa)

**SQL Manuale (se necessario):**

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

-- Indexes per performance
CREATE INDEX IF NOT EXISTS idx_query_logs_session_id ON query_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
```

**Passo 3:** Verificare creazione tabelle

```sql
-- Verifica tabelle create
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('sessions', 'query_logs');
```

**Risultato atteso:**
```
table_name
-----------
sessions
query_logs
```

### 2. Verificare RLS Policies

Dopo creazione tabelle, verificare nella pagina **Authentication > Policies**:

- ✅ `sessions` appare nella lista
- ✅ RLS enabled (automatico)
- ✅ "No policies created yet" (corretto - protezione completa)
- ✅ `query_logs` appare nella lista
- ✅ RLS enabled (automatico)
- ✅ "No policies created yet" (corretto - protezione completa)

**Messaggio atteso:**
> "No data will be selectable via Supabase APIs because RLS is enabled but no policies have been created yet."

**Questo è corretto:** Nessun accesso via Data API pubblica, solo backend con `service_role`.

**Se RLS non è abilitato automaticamente:**

```sql
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_logs ENABLE ROW LEVEL SECURITY;
```

### 3. Verifica Finale Dashboard

Dopo setup, la dashboard dovrebbe mostrare:

- ✅ `chunks` - RLS enabled, No policies
- ✅ `documents` - RLS enabled, No policies  
- ✅ `sessions` - RLS enabled, No policies
- ✅ `query_logs` - RLS enabled, No policies

Tutte le tabelle protette, accessibili solo via backend con `service_role` key.

### 4. Verificare SSL Enforcement (Opzionale)

**Se deployment pubblico:**

1. Aprire **Settings > Database**
2. Verificare **SSL Configuration**
3. Abilitare **"Enforce SSL on incoming connections"** se necessario

**Nota:** Per sviluppo locale, SSL enforcement non necessario.

---

## Variabili d'Ambiente

### Variabili Necessarie per Epic 3

```env
# ✅ NECESSARIA - Database Configuration SUPABASE
# PostgreSQL with PGVector extension
# Connection string includes credentials (user/password) - no separate API keys needed
DATABASE_URL="postgresql://postgres.[user]:[password]@aws-1-eu-north-1.pooler.supabase.com:5432/postgres"

# ✅ NECESSARIA - OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key

# ⚠️ OPZIONALE - Model Selection
LLM_CHOICE=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# ⚠️ OPZIONALE - LangFuse Configuration (solo se usi LangFuse)
LANGFUSE_PUBLIC_KEY=your-langfuse-public-api-key
LANGFUSE_SECRET_KEY=your-langfuse-secret-api-key
LANGFUSE_BASE_URL=https://cloud.langfuse.com

# ⚠️ OPZIONALE - Cost Protection (Epic 3 Security Hardening)
COST_DAILY_LIMIT=10.00      # Limite giornaliero $10
COST_HOURLY_LIMIT=2.00      # Limite orario $2
COST_ALERT_THRESHOLD=5.00   # Alert a $5/giorno
```

### Variabili Supabase: NON Necessarie per Epic 3

**Epic 3 usa direct PostgreSQL connection via `DATABASE_URL` (AsyncPG), non Supabase client Python.**

**Variabili NON necessarie:**
- ❌ `SUPABASE_ANON_KEY` - Solo se si usa Data API pubblica (non il caso Epic 3)
- ❌ `SUPABASE_SERVICE_ROLE_KEY` - Non necessaria se si usa solo `DATABASE_URL`
- ❌ `SUPABASE_SECRET_KEY` - Non standard Supabase
- ❌ `SUPABASE_PUBLISHABLE_KEY` - Non standard Supabase

**Motivo:**
- Epic 3 usa **direct PostgreSQL connection** via `DATABASE_URL` (AsyncPG)
- Non usa Supabase client Python (non necessario)
- Connection pool già configurato in `utils/db_utils.py` con `DATABASE_URL`
- Credenziali già incluse in `DATABASE_URL`

### Variabili Supabase: Quando Necessarie (Futuro)

**Se in futuro si vuole usare Supabase Client Python:**

```python
from supabase import create_client

supabase = create_client(
    supabase_url="https://your-project.supabase.co",
    supabase_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Backend only
)
```

**Variabili necessarie:**
- `SUPABASE_URL`: URL progetto (es. `https://xxx.supabase.co`)
- `SUPABASE_SERVICE_ROLE_KEY`: Per backend access (bypassa RLS)

---

## Verifica Setup

### Test Connessione PostgreSQL

```bash
# Test connessione con DATABASE_URL
psql $DATABASE_URL -c "SELECT version();"
```

### Test Protezione RLS

```sql
-- Test: Tentativo accesso via anon role (dovrebbe fallire)
SET ROLE anon;
SELECT * FROM sessions;  -- Dovrebbe restituire 0 righe (RLS protegge)
SELECT * FROM query_logs;  -- Dovrebbe restituire 0 righe (RLS protegge)
RESET ROLE;

-- Test: Accesso via service_role (dovrebbe funzionare)
SET ROLE service_role;
SELECT COUNT(*) FROM sessions;  -- Dovrebbe funzionare
SELECT COUNT(*) FROM query_logs;  -- Dovrebbe funzionare
RESET ROLE;
```

### Verifica Accesso Backend

Verificare che tabelle `sessions` e `query_logs` siano accessibili solo via backend:

- ✅ Connessione diretta PostgreSQL con `DATABASE_URL` funziona
- ✅ Data API pubblica non può accedere (test con anon key dovrebbe fallire)
- ✅ RLS protegge completamente le tabelle

---

## Checklist Completa

### Dashboard Supabase

- [x] Creare tabelle `sessions` e `query_logs` via SQL Editor
- [x] Verificare RLS enabled automaticamente su nuove tabelle
- [x] Verificare "No policies created yet" (protezione completa)
- [ ] (Opzionale) Abilitare SSL enforcement se deployment pubblico

### Variabili d'Ambiente

- [x] `DATABASE_URL` presente e corretto
- [x] `OPENAI_API_KEY` presente
- [x] Variabili Supabase non necessarie rimosse/commentate
- [x] Variabili cost protection aggiunte (opzionali)

### Verifica Setup

- [x] Testare connessione PostgreSQL con `DATABASE_URL`
- [x] Verificare che tabelle `sessions` e `query_logs` siano accessibili solo via backend
- [x] Verificare che Data API pubblica non possa accedere (test con anon key)

---

## Note Importanti

1. **RLS senza policies = protezione massima:** Nessun accesso via Data API, solo backend
2. **Direct PostgreSQL connection:** Epic 3 usa AsyncPG, non Supabase client
3. **Service role key:** Non necessaria se si usa solo `DATABASE_URL` (già contiene credenziali)
4. **Future enhancement:** Se si vuole usare Supabase client in futuro, aggiungere `SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`

---

## Risultato Atteso

Dopo completamento setup:

1. **Dashboard:** 4 tabelle con RLS enabled, no policies (protezione completa)
   - `chunks` - RLS enabled, No policies
   - `documents` - RLS enabled, No policies
   - `sessions` - RLS enabled, No policies
   - `query_logs` - RLS enabled, No policies

2. **Variabili:** Solo `DATABASE_URL` necessario, altre opzionali

3. **Sicurezza:** Tutte le tabelle protette, accessibili solo backend

**Epic 3 pronto per implementazione!**

---

---

## LangFuse Dashboard Filtering (Story 3.2)

### Panoramica

Story 3.2 implementa LangFuse tracing per Streamlit queries con separazione da MCP queries. Questa sezione spiega come filtrare i trace nel dashboard LangFuse per visualizzare solo query Streamlit o solo query MCP.

### Metadata Structure

Ogni trace Streamlit include i seguenti metadata:

| Campo | Valore | Descrizione |
|-------|--------|-------------|
| `source` | `"streamlit"` | Identifica origine query (vs `"mcp"` per MCP server) |
| `session_id` | UUID v4 | Sessione Streamlit univoca |
| `query_text` | String | Testo query utente |

**Esempio trace metadata:**
```json
{
  "source": "streamlit",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "query_text": "What is the main topic of the document?"
}
```

### Filtrare Trace nel Dashboard LangFuse

#### 1. Visualizzare Solo Query Streamlit

**Passo 1:** Aprire [LangFuse Dashboard](https://cloud.langfuse.com) > Traces

**Passo 2:** Cliccare su "Filters" (icona filtro)

**Passo 3:** Aggiungere filtro:
- **Field:** `Metadata`
- **Key:** `source`
- **Operator:** `equals`
- **Value:** `streamlit`

**Risultato:** Solo trace con `source: streamlit` visualizzati.

#### 2. Visualizzare Solo Query MCP

**Passo 1:** Aprire LangFuse Dashboard > Traces

**Passo 2:** Aggiungere filtro:
- **Field:** `Metadata`
- **Key:** `source`
- **Operator:** `equals`
- **Value:** `mcp`

**Risultato:** Solo trace con `source: mcp` visualizzati (già implementato Epic 2).

#### 3. Filtrare per Session ID

Per analizzare una sessione specifica:

**Filtro:**
- **Field:** `Session ID` (campo dedicato in LangFuse v3)
- **Operator:** `equals`
- **Value:** `<session-id-uuid>`

**Risultato:** Tutti i trace della sessione specificata.

#### 4. Confrontare Performance MCP vs Streamlit

Per confrontare latenza e costi tra i due canali:

1. **Tab Analytics:** LangFuse Dashboard > Analytics
2. **Group by:** `Metadata.source`
3. **Metrics:** Latency p50, p95, p99, Total Cost

**Oppure:**

1. Esportare trace via API LangFuse
2. Analizzare con tool esterno (Pandas, Excel)

### Trace Hierarchy

Ogni query Streamlit crea una gerarchia di trace:

```
streamlit_query (root span)
├── metadata: {source: "streamlit", session_id: "..."}
├── embedding-generation (nested span) 
│   └── session_id propagated automatically
├── vector-search (nested span)
│   └── session_id propagated automatically
└── llm-generation (nested span)
    └── session_id propagated automatically
```

Il `session_id` è automaticamente propagato a tutti i nested span tramite `propagate_attributes()`.

### Troubleshooting

#### Trace non visibili nel dashboard

1. **Verificare variabili ambiente:**
   ```env
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_BASE_URL=https://cloud.langfuse.com
   ```

2. **Verificare flush:**
   ```python
   # Il context manager chiama flush automaticamente
   # Se problemi, aggiungere flush esplicito
   from langfuse import get_client
   langfuse = get_client()
   langfuse.flush()
   ```

3. **Graceful degradation:** Se LangFuse non disponibile, il sistema continua senza tracing (nessun errore, warning loggato)

#### Metadata source mancante

Se `source` non appare nei metadata:

1. Verificare che `with_streamlit_context()` sia usato in `app.py`
2. Verificare import: `from utils.langfuse_streamlit import with_streamlit_context`
3. Verificare che `propagate_attributes()` sia chiamato correttamente

#### Session ID non propagato a nested spans

1. Verificare uso `propagate_attributes()` context manager
2. Nested spans devono essere creati **dentro** il context manager
3. Verificare che LangFuse SDK versione >= 3.0.0

### Riferimenti

- [LangFuse Python SDK v3 Docs](https://langfuse.com/docs/sdk/python)
- [LangFuse Propagate Attributes](https://langfuse.com/docs/observability/sdk/python/instrumentation#propagating-trace-attributes)
- Tech Spec: `docs/stories/3/tech-spec-epic-3.md#Story-3.2`
- Architecture: `docs/architecture.md#ADR-001`

---

**Documento creato per:** Setup Epic 3  
**Story 3.2 implemented:** LangFuse Tracing for Streamlit with Dashboard Filtering

