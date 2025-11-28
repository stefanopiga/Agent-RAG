# Epic 3 - Analisi Dubbi Architetturali

**Data:** 2025-01-27  
**Epic:** Epic 3 - Streamlit UI Observability  
**Status:** Pre-Implementation Review

---

## 1. Storage: Supabase vs Locale vs Redis

### Contesto Attuale

- **Database esistente:** Supabase (PostgreSQL cloud) già configurato per `documents` e `chunks`
- **Connection pool:** Già implementato in `utils/db_utils.py` con AsyncPG
- **Redis:** Non presente nel progetto

### Opzioni di Storage

#### Opzione A: PostgreSQL Supabase (Attuale Tech Spec)

**Vantaggi:**

- Zero setup aggiuntivo (riutilizza connessione esistente)
- Persistenza garantita (dati non si perdono)
- Query SQL complesse per analisi storica (`query_logs` table)
- Consistenza transazionale (ACID)
- Backup automatico Supabase
- Analisi aggregazioni efficienti (es. costi per periodo)

**Svantaggi:**

- Latency network: 50-200ms per query (Supabase cloud)
- Costi Supabase: Storage growth → costi incrementali
- Overhead connessione: Ogni query Streamlit → DB roundtrip
- Scalabilità: Connection pool limitato (max 10 connessioni)

**Costi Stimati Supabase:**

- Free tier: 500MB storage, 2GB bandwidth/mese
- Pro tier ($25/mese): 8GB storage, 50GB bandwidth
- **Rischio:** `query_logs` può crescere rapidamente (ogni query = ~500 bytes)
  - 1000 query/giorno = ~15MB/mese
  - 10.000 query/giorno = ~150MB/mese
  - **Conclusione:** Free tier sufficiente per MVP, monitorare crescita

#### Opzione B: PostgreSQL Locale (Docker)

**Vantaggi:**

- Latency < 1ms (localhost)
- Zero costi cloud
- Controllo completo (backup, retention policy)
- Performance ottimale per sviluppo locale

**Svantaggi:**

- Setup aggiuntivo richiesto (Docker compose già presente)
- Persistenza locale (dati persi se container eliminato)
- Non disponibile in produzione cloud (se deploy su Vercel/Railway)
- Sincronizzazione dev/prod diversa (complessità)

**Quando Usare:**

- Solo sviluppo locale
- Deployment self-hosted con DB dedicato
- Non adatto per deployment cloud serverless

#### Opzione C: Redis

**Vantaggi:**

- Latency < 5ms (in-memory)
- TTL automatico per cleanup sessioni
- Performance ottimale per session stats (read-heavy)
- Pattern standard per session management

**Svantaggi:**

- **Setup aggiuntivo:** Nuova dipendenza infrastrutturale
- **Persistenza limitata:** Redis può perdere dati (RDB/AOF opzionali)
- **Query complesse:** No JOIN, no aggregazioni SQL native
- **Costi:** Redis cloud (Upstash/Redis Cloud) o self-hosted
- **Complessità:** Due storage systems (PostgreSQL + Redis)

**Implementazione Redis:**

```python
# Pattern tipico Redis session storage
import redis.asyncio as redis

redis_client = redis.from_url(REDIS_URL)

# Session stats (TTL 24h)
await redis_client.hset(
    f"session:{session_id}",
    mapping={
        "query_count": query_count,
        "total_cost": str(total_cost),
        "last_activity": timestamp
    }
)
await redis_client.expire(f"session:{session_id}", 86400)

# Query logs (List con TTL)
await redis_client.lpush(f"session:{session_id}:queries", json.dumps(query_log))
await redis_client.expire(f"session:{session_id}:queries", 86400)
```

**Problemi Redis per Epic 3:**

- **Query logs storici:** Redis non adatto per analisi storica (no aggregazioni)
- **Analisi costi:** Richiede export a PostgreSQL per analisi complesse
- **Dual storage:** Session stats in Redis, query logs in PostgreSQL (complessità)

### Raccomandazione: PostgreSQL Supabase (Opzione A)

**Motivazione:**

1. **Consistenza architetturale:** Database già presente, zero setup
2. **Analisi storica:** `query_logs` table essenziale per analisi costi nel tempo
3. **MVP focus:** Supabase free tier sufficiente per MVP (monitorare crescita)
4. **Fallback già implementato:** Tech spec prevede graceful degradation se DB unavailable

**Ottimizzazioni Performance:**

```python
# Cache session stats in st.session_state (reduce DB queries)
if "session_stats" not in st.session_state:
    st.session_state.session_stats = await get_session_stats(session_id)
    st.session_state.stats_cache_time = time.time()

# Refresh cache ogni 5 secondi (non ogni rerun)
if time.time() - st.session_state.stats_cache_time > 5:
    st.session_state.session_stats = await get_session_stats(session_id)
    st.session_state.stats_cache_time = time.time()
```

**Mitigazione Costi Supabase:**

- **Retention policy:** Cleanup automatico `query_logs` > 30 giorni (cron job)
- **Archivio:** Export mensile a S3/CSV prima di cleanup
- **Monitoring:** Alert se storage > 80% quota

---

## 2. Autenticazione: Rischi e Necessità

### Contesto Attuale

- **Sistema:** Single-user (nessuna autenticazione)
- **Deployment:** Presumibilmente self-hosted o cloud privato
- **Accesso:** Streamlit UI accessibile via URL (pubblico o VPN)
- **Database:** Supabase PostgreSQL con Row Level Security (RLS) disponibile

### Sicurezza Supabase: Protezioni Native Disponibili

**Row Level Security (RLS):**

- **RLS è obbligatorio** per tabelle nello schema `public` esposte via Data API ([Supabase Docs](https://supabase.com/docs/guides/database/postgres/row-level-security))
- **Protezione defense-in-depth:** RLS protegge i dati anche se accesso tramite tooling di terze parti
- **Policies SQL:** Controllo granulare accesso per riga basato su `auth.uid()` o ruoli (`anon`, `authenticated`)
- **Default:** RLS abilitato automaticamente per tabelle create via Dashboard, **deve essere abilitato manualmente** per tabelle create via SQL

**SSL/TLS Enforcement:**

- **HTTP APIs:** SSL automaticamente enforced su tutte le connessioni HTTP (PostgREST, Storage, Auth) ([Supabase Docs](https://supabase.com/docs/guides/platform/ssl-enforcement))
- **PostgreSQL:** SSL enforcement opzionale (configurabile via Dashboard o CLI)
- **Modo più sicuro:** `verify-full` con CA certificate Supabase per connessioni PostgreSQL

**Encryption:**

- **Data at rest:** Encryption automatica su storage Supabase ([Supabase Security](https://uibakery.io/blog/supabase-security))
- **Data in transit:** SSL/TLS per tutte le connessioni HTTP e PostgreSQL (se SSL enforcement abilitato)
- **Vault:** Secrets storage con Authenticated Encryption ([Supabase Vault](https://supabase.com/docs/guides/database/vault))

**API Keys Security:**

- **Anon key:** Sicura da esporre se RLS abilitato (controllo accesso via policies)
- **Service role key:** **Mai esporre** - bypassa RLS, trattare come secret ([Supabase Docs](https://supabase.com/docs/guides/database/secure-data))

### Rischi Senza Autenticazione

#### Rischio 1: Accesso Non Autorizzato

**Scenario:**

- Streamlit app esposta su internet senza autenticazione
- Chiunque con URL può accedere e fare query
- Costi OpenAI accumulati da utenti non autorizzati

**Impatto:**

- **Alto:** Costi API non controllati (OpenAI può costare $100+/mese)
- **Medio:** Dati documentali esposti (se contenuti sensibili)
- **Basso:** Session tracking compromesso (session_id non identifica utente reale)

**Mitigazione Senza Auth:**

- **Network-level:** VPN, firewall rules, IP whitelist
- **Deployment:** Self-hosted su server privato (non esposto su internet)
- **Monitoring:** Alert su costi anomali (> threshold giornaliero)
- **Supabase RLS:** Abilitare RLS su tabelle `sessions` e `query_logs` per protezione defense-in-depth ([Supabase RLS Guide](https://supabase.com/docs/guides/database/postgres/row-level-security))

**Protezione RLS per Epic 3:**

```sql
-- Abilitare RLS su tabelle session (obbligatorio per sicurezza)
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Solo connessioni service role possono accedere (backend only)
-- Nessun accesso via anon key (protezione da Data API exposure)
CREATE POLICY "Service role only" ON sessions
  FOR ALL
  TO service_role
  USING (true);

CREATE POLICY "Service role only" ON query_logs
  FOR ALL
  TO service_role
  USING (true);
```

**Nota:** Con RLS abilitato e policies restrittive, anche se `anon` key è esposta, le tabelle `sessions` e `query_logs` non sono accessibili via Data API pubblica.

#### Rischio 2: Session Hijacking

**Scenario:**

- Session_id UUID v4 non è segreto (visibile in browser)
- Attaccante può vedere session_id e accedere statistiche sessione altrui

**Impatto:**

- **Basso:** Solo statistiche visibili (query count, costi)
- **Nessuno:** Nessun dato sensibile in session stats
- **Nota:** Session_id non permette di vedere query text (solo aggregazioni)

**Mitigazione:**

- UUID v4 sufficiente per single-user system (non-guessable)
- Session stats non contengono dati sensibili
- Query logs richiedono accesso DB (non esposti via UI)

#### Rischio 3: DDoS / Abuse

**Scenario:**

- Attaccante fa migliaia di query per esaurire quota OpenAI
- Nessuna rate limiting senza autenticazione

**Impatto:**

- **Alto:** Costi API esplosivi
- **Medio:** Degradazione performance sistema

**Mitigazione Senza Auth:**

- **Rate limiting:** Streamlit non supporta nativamente, richiede middleware
- **Monitoring:** Alert costi > threshold
- **Network:** Firewall rules, IP blocking
- **Supabase Pre-Request Function:** Implementare rate limiting a livello database ([Supabase API Security](https://supabase.com/docs/guides/api/securing-your-api))

**Rate Limiting con Supabase:**

```sql
-- Tabella rate limits (schema private = non accessibile via API)
CREATE TABLE private.rate_limits (
  ip inet,
  request_at timestamp
);

CREATE INDEX rate_limits_ip_request_at_idx
  ON private.rate_limits (ip, request_at DESC);

-- Pre-request function per rate limiting
CREATE FUNCTION public.check_request()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  req_ip inet := split_part(
    current_setting('request.headers', true)::json->>'x-forwarded-for',
    ',', 1
  )::inet;
  count_in_five_mins integer;
BEGIN
  SELECT count(*) INTO count_in_five_mins
  FROM private.rate_limits
  WHERE ip = req_ip
    AND request_at BETWEEN now() - interval '5 minutes' AND now();

  IF count_in_five_mins > 100 THEN
    RAISE SQLSTATE 'PGRST'
    USING message = json_build_object(
      'message', 'Rate limit exceeded'
    )::text,
    detail = json_build_object('status', 429)::text;
  END IF;

  INSERT INTO private.rate_limits (ip, request_at)
  VALUES (req_ip, now());
END;
$$;

-- Configurare funzione per esecuzione su ogni request
ALTER ROLE authenticator
  SET pgrst.db_pre_request = 'public.check_request';
NOTIFY pgrst, 'reload config';
```

**Nota:** Rate limiting via Supabase protegge solo Data API, non Streamlit UI direttamente. Per protezione completa Streamlit, richiede middleware o reverse proxy (nginx).

### Quando Autenticazione È Necessaria

**Autenticazione Richiesta Se:**

- ✅ App esposta su internet pubblico (non VPN)
- ✅ Dati documentali sensibili (PII, informazioni riservate)
- ✅ Multi-user system (più utenti con costi separati)
- ✅ Compliance requirements (GDPR, HIPAA)

**Autenticazione Non Necessaria Se:**

- ✅ Self-hosted su server privato
- ✅ Accesso via VPN solo
- ✅ Single-user system (uso personale)
- ✅ Dati non sensibili (documentazione pubblica)

### Opzioni Autenticazione (Se Necessaria)

#### Opzione 1: Streamlit Native Auth (Streamlit-Authenticator)

```python
import streamlit_authenticator as stauth

authenticator = stauth.Authenticate(
    credentials={'usernames': {'user': {'password': 'hash'}}},
    cookie_name='session',
    key='secret_key'
)

name, authentication_status, username = authenticator.login()

if authentication_status == False:
    st.error('Username/password is incorrect')
    st.stop()
elif authentication_status == None:
    st.warning('Please enter your username and password')
    st.stop()
```

**Vantaggi:**

- Setup semplice (5 minuti)
- Integrazione nativa Streamlit
- Session management automatico

**Svantaggi:**

- Password in plaintext (richiede hashing)
- No OAuth/SAML (solo username/password)
- Gestione utenti manuale (no DB)

#### Opzione 2: OAuth (Google/GitHub)

```python
import streamlit_authenticator as stauth

authenticator = stauth.Authenticate(
    credentials={'usernames': {}},
    cookie_name='session',
    key='secret_key',
    oauth_providers=['google', 'github']
)
```

**Vantaggi:**

- No password management
- Single Sign-On (SSO)
- User management esterno (Google/GitHub)

**Svantaggi:**

- Setup OAuth più complesso
- Dipendenza provider esterno
- Costi OAuth provider (se applicabile)

#### Opzione 3: Supabase Auth

```python
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Login
user = supabase.auth.sign_in_with_password({
    "email": email,
    "password": password
})

# Session check
session = supabase.auth.get_session()
if not session:
    st.error("Please login")
    st.stop()
```

**Vantaggi:**

- Integrazione con Supabase esistente
- User management in DB
- JWT tokens automatici
- Row Level Security (RLS) per multi-tenancy

**Svantaggi:**

- Dipendenza Supabase Auth
- Setup più complesso
- Overkill per single-user

### Raccomandazione: No Auth per MVP, ma RLS Obbligatorio

**Motivazione:**

1. **Single-user system:** PRD conferma sistema single-user
2. **Deployment:** Presumibilmente self-hosted o VPN-only
3. **Complessità:** Auth aggiunge overhead senza benefici per MVP
4. **Focus:** Epic 3 è observability, non security
5. **RLS è obbligatorio:** Supabase richiede RLS su tabelle `public` esposte ([Supabase Security](https://supabase.com/docs/guides/api/securing-your-api))

**Mitigazione Rischi:**

- **Network security:** VPN, firewall, IP whitelist
- **Monitoring:** Alert costi anomali (Epic 2 già implementa)
- **Documentation:** Chiarire in README che app non è per uso pubblico
- **RLS Policies:** Abilitare RLS su `sessions` e `query_logs` con policies `service_role` only
- **SSL Enforcement:** Abilitare SSL enforcement PostgreSQL se deployment pubblico ([Supabase SSL](https://supabase.com/docs/guides/platform/ssl-enforcement))
- **API Keys:** Usare `service_role` key solo backend, mai esporre in frontend

**Implementazione RLS per Epic 3:**

```sql
-- Schema: Creare tabelle in schema public (esposto via Data API)
-- IMPORTANTE: Abilitare RLS immediatamente dopo creazione tabelle

-- Sessions table con RLS
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    query_count INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0.0,
    total_latency_ms DECIMAL(10, 2) DEFAULT 0.0
);

ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

-- Policy: Solo service_role può accedere (backend only)
CREATE POLICY "Service role only" ON sessions
  FOR ALL
  TO service_role
  USING (true);

-- Query logs table con RLS
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

ALTER TABLE query_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role only" ON query_logs
  FOR ALL
  TO service_role
  USING (true);
```

**Future Enhancement (Post-MVP):**

- Aggiungere auth se deployment pubblico richiesto (Supabase Auth con RLS policies `authenticated`)
- Implementare rate limiting via Supabase pre-request function se abuse rilevato
- Multi-user support con Supabase Auth + RLS policies per-user isolation

---

## 3. Altri Dubbi Architetturali

### Dubbio: Session Persistence tra Rerun

**Problema:**

- Streamlit `st.session_state` persiste solo per durata browser session
- Se utente chiude browser, session_id perso
- Nuova sessione = nuovo session_id (statistiche perse)

**Analisi:**

- **Comportamento atteso:** Session_id legato a browser session (non utente)
- **Impatto:** Statistiche reset ad ogni nuova sessione browser
- **Mitigazione:** Se necessario, associare session_id a cookie persistente (7 giorni TTL)

**Raccomandazione:**

- Comportamento attuale accettabile per MVP
- Session stats sono per sessione browser (non utente)
- Se necessario persistenza utente, richiede auth (identificazione utente)

### Dubbio: Query Logs Storage Growth

**Problema:**

- `query_logs` table cresce indefinitamente
- Supabase storage limitato (500MB free tier)

**Analisi:**

- **Growth rate:** ~500 bytes per query log entry
- **1000 query/giorno:** ~15MB/mese, ~180MB/anno
- **10.000 query/giorno:** ~150MB/mese, ~1.8GB/anno

**Mitigazione:**

- **Retention policy:** Cleanup automatico query_logs > 30 giorni
- **Archivio:** Export mensile a CSV/S3 prima cleanup
- **Aggregazione:** Mantenere solo aggregazioni mensili per analisi storica

**Implementazione:**

```sql
-- Cleanup cron job (eseguito mensilmente)
DELETE FROM query_logs
WHERE timestamp < NOW() - INTERVAL '30 days';

-- Archivio aggregazioni mensili
CREATE TABLE query_logs_monthly_agg AS
SELECT
    DATE_TRUNC('month', timestamp) as month,
    COUNT(*) as total_queries,
    SUM(cost) as total_cost,
    AVG(latency_ms) as avg_latency
FROM query_logs
GROUP BY DATE_TRUNC('month', timestamp);
```

---

## Conclusioni e Raccomandazioni

### Storage: PostgreSQL Supabase ✅

- **Decisione:** Mantenere PostgreSQL Supabase come storage session
- **Razionale:** Zero setup, analisi storica, consistenza architetturale
- **Ottimizzazioni:** Cache session stats in `st.session_state`, retention policy per query_logs
- **Sicurezza:** RLS obbligatorio su tabelle `sessions` e `query_logs` ([Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security))

### Autenticazione: No Auth per MVP, RLS Obbligatorio ✅

- **Decisione:** Non implementare autenticazione utenti in Epic 3
- **Razionale:** Single-user system, deployment presumibilmente privato
- **Mitigazione:**
  - Network security (VPN), monitoring costi, documentazione chiara
  - **RLS policies `service_role` only** su tabelle session (protezione defense-in-depth)
  - SSL enforcement PostgreSQL se deployment pubblico ([Supabase SSL](https://supabase.com/docs/guides/platform/ssl-enforcement))
  - Rate limiting via Supabase pre-request function se necessario ([Supabase API Security](https://supabase.com/docs/guides/api/securing-your-api))

### Checklist Sicurezza Epic 3

- [ ] Abilitare RLS su `sessions` table con policy `service_role` only
- [ ] Abilitare RLS su `query_logs` table con policy `service_role` only
- [ ] Verificare che `service_role` key non sia esposta in frontend (solo backend)
- [ ] Abilitare SSL enforcement PostgreSQL se deployment pubblico
- [ ] Implementare rate limiting via Supabase pre-request function (opzionale)
- [ ] Documentare in README che app non è per uso pubblico senza auth

### Future Enhancements

- **Post-MVP:** Valutare auth se deployment pubblico richiesto
- **Post-MVP:** Implementare retention policy automatica per query_logs
- **Post-MVP:** Export mensile costi a CSV/S3 per analisi storica

---

**Documento creato per:** Pre-implementation review Epic 3  
**Prossimi passi:** Validare decisioni con team, aggiornare tech spec se necessario

---

## Riferimenti Supabase Security

- [Row Level Security Guide](https://supabase.com/docs/guides/database/postgres/row-level-security) - RLS policies obbligatorie per tabelle public
- [Securing your API](https://supabase.com/docs/guides/api/securing-your-api) - Rate limiting e pre-request functions
- [Securing your data](https://supabase.com/docs/guides/database/secure-data) - Best practices sicurezza dati
- [SSL Enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement) - Configurazione SSL PostgreSQL
- [Session Management Security](https://bootstrapped.app/guide/how-to-manage-user-sessions-securely-in-supabase) - Best practices session management
