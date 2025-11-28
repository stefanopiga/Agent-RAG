# Epic 3 - Analisi Lacune Documentazione e Fonti Esterne Verificate

**Data:** 2025-01-27  
**Epic:** Epic 3 - Streamlit UI Observability  
**Status:** Analisi completata con verifica fonti esterne

---

## Riepilogo

Analisi delle lacune tecniche e di documentazione ufficiale per Epic 3, con verifica delle fonti esterne tramite strumenti MCP (brave-search, fetch, langfuse-docs).

---

## 1. LangFuse Context Injection - VERIFICATO ✅

### Informazioni Recuperate

**Documentazione Ufficiale:** https://langfuse.com/docs/observability/sdk/python/instrumentation#propagating-trace-attributes

**Metodo Corretto:** `propagate_attributes()` context manager

**Esempio di Codice Verificato:**

```python
from langfuse import get_client, propagate_attributes

langfuse = get_client()

with langfuse.start_as_current_observation(
    as_type="span",
    name="streamlit_query",
    input={"query": query_text}
) as root_span:
    # Propagate session_id to all child observations
    with propagate_attributes(
        session_id=str(session_id),
        user_id=None,  # Single-user system
        metadata={"source": "streamlit"}
    ):
        # All nested observations automatically inherit session_id
        result = await run_agent(query_text)
        # embedding-generation, vector-search, llm-generation spans
        # all automatically have session_id attribute
```

**Note Importanti:**

- `propagate_attributes()` è un context manager che propaga automaticamente attributi a tutti i child observations
- Attributi supportati: `user_id`, `session_id`, `metadata`, `version`, `tags`
- Valori devono essere stringhe ≤200 caratteri
- Chiavi metadata: solo caratteri alfanumerici (no spazi o caratteri speciali)
- Chiamare **early in the trace** per garantire copertura completa

**Riferimento:** https://langfuse.com/docs/observability/sdk/python/instrumentation#propagating-trace-attributes

---

## 2. Estrazione Costi da Trace LangFuse - VERIFICATO ✅

### Informazioni Recuperate

**Documentazione Ufficiale:** https://langfuse.com/guides/cookbook/example_query_data_via_sdk

**Metodo Corretto:** Accesso via API SDK o `cost_details` nelle observations

**Opzione A: Durante Esecuzione (Non Disponibile Direttamente)**

⚠️ **Limitazione:** Non esiste `get_current_trace()` nel Python SDK v3 per recuperare `total_cost` durante l'esecuzione.

**Riferimento GitHub Discussion:** https://github.com/orgs/langfuse/discussions/8280

**Opzione B: Via API SDK (Post-Esecuzione)**

```python
from langfuse import get_client

langfuse = get_client()

# Fetch trace dopo l'esecuzione
trace = langfuse.api.trace.get(trace_id)

# Accesso costi via observations
for obs in trace.observations:
    if obs.cost_details:
        total_cost = obs.cost_details.get('total', 0.0)
        # oppure
        calculated_total_cost = obs.calculated_total_cost
```

**Opzione C: Estrazione da Observation Object (Durante Esecuzione)**

```python
from langfuse import get_client

langfuse = get_client()

with langfuse.start_as_current_observation(
    as_type="span",
    name="streamlit_query"
) as span:
    # ... esecuzione query ...
    
    # Dopo il completamento, recupera costi dai nested spans
    # Nota: Richiede accesso al trace_id per query API
    trace_id = span.trace_id
    
    # Query API per ottenere costi (async, post-execution)
    trace = langfuse.api.trace.get(trace_id)
    total_cost = sum(
        obs.calculated_total_cost or 0.0 
        for obs in trace.observations 
        if obs.type == "GENERATION"
    )
```

**Raccomandazione per Epic 3:**

1. **Durante esecuzione:** Usare `langfuse.openai` wrapper che calcola automaticamente costi
2. **Post-esecuzione:** Query API SDK per recuperare costi aggregati dal trace
3. **Storage:** Salvare `trace_id` in `query_logs` per query successiva dei costi

**Riferimenti:**
- https://langfuse.com/guides/cookbook/example_query_data_via_sdk
- https://langfuse.com/docs/observability/features/token-and-cost-tracking

---

## 3. User Agent in Streamlit - NON DISPONIBILE ❌

### Informazioni Recuperate

**Risultato Ricerca:** Streamlit non espone direttamente `user_agent` nel browser.

**Discussione Streamlit:** https://discuss.streamlit.io/t/getting-the-user-agent-of-the-current-session/25627

**Soluzioni Alternative:**

**Opzione A: Rimuovere user_agent dai metadata**

```python
# Epic 3 tech spec richiede user_agent, ma non è disponibile
# Soluzione: Rimuovere o usare placeholder

with propagate_attributes(
    session_id=str(session_id),
    metadata={
        "source": "streamlit",
        # "user_agent": "N/A"  # Non disponibile in Streamlit
    }
):
    pass
```

**Opzione B: Usare JavaScript Custom Component (Complesso)**

Richiede creazione custom component Streamlit con JavaScript per accedere `navigator.userAgent`. Non raccomandato per MVP.

**Raccomandazione:**

- **Rimuovere `user_agent` dai metadata** nella tech spec Epic 3
- **Aggiornare AC3.2.4** per non richiedere `user_agent`
- **Documentare** che Streamlit non espone user_agent nativamente

---

## 4. Versioni Dipendenze - VERIFICATE ✅

### LangFuse Python SDK

**Versione Minima:** 3.0.0+ ✅ **VERIFICATA**

**Documentazione:** https://langfuse.com/docs/observability/sdk/python/overview

**Note:** SDK v3 è generalmente disponibile (GA) da giugno 2025. Basato su OpenTelemetry.

### Streamlit

**Versione Minima:** 1.31+ ⚠️ **DA VERIFICARE**

**Risultato Ricerca:** Nessuna informazione specifica su versione 1.31 o API `st.session_state` changes.

**Documentazione:** https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state

**Note:** `st.session_state` è disponibile da versioni precedenti. Versione 1.31+ potrebbe essere conservativa. Verificare con versione minima funzionante.

**Raccomandazione:** Testare con Streamlit 1.28+ (versione più recente verificata).

### PostgreSQL

**Versione Minima:** 16+ ✅ **VERIFICATA**

**PGVector Support:** pgvector 0.8.0+ supporta PostgreSQL 9.5-18

**Riferimento:** https://github.com/pgvector/pgvector

**Note:** PostgreSQL 16+ è supportato. Versione minima conservativa.

### AsyncPG

**Versione Minima:** Non specificata ⚠️

**Requisiti Python:** Python 3.9+ (verificato)

**Riferimento:** https://pypi.org/project/asyncpg/

**Note:** AsyncPG richiede Python 3.9+. Compatibile con PostgreSQL 9.5-18.

**Raccomandazione:** Specificare versione minima AsyncPG (es. 0.29.0+) basata su test.

---

## 5. Moduli Non Implementati - DA IMPLEMENTARE

### `utils/session_manager.py`

**Funzioni Richieste:**

```python
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from utils.models import SessionStats, QueryLog

def generate_session_id() -> UUID:
    """Genera UUID v4 per session_id."""
    from uuid import uuid4
    return uuid4()

async def create_session(session_id: UUID) -> None:
    """Crea nuovo record in sessions table."""
    # Implementazione con AsyncPG

async def get_session_stats(session_id: UUID) -> SessionStats:
    """Recupera statistiche da PostgreSQL."""
    # Implementazione con AsyncPG

async def log_query(
    session_id: UUID,
    query_text: str,
    cost: Decimal,
    latency_ms: Decimal,
    langfuse_trace_id: str | None = None
) -> None:
    """Persiste query log in DB."""
    # Implementazione con AsyncPG

async def update_session_stats(
    session_id: UUID,
    cost: Decimal,
    latency_ms: Decimal
) -> None:
    """Aggiorna statistiche sessione."""
    # Implementazione con AsyncPG
```

### `utils/langfuse_streamlit.py`

**Funzioni Richieste (Aggiornate con Informazioni Verificate):**

```python
from contextlib import contextmanager
from uuid import UUID
from langfuse import get_client, propagate_attributes

langfuse = get_client()

@contextmanager
def with_streamlit_context(session_id: UUID, query: str):
    """
    Context manager per LangFuse context injection.
    
    Propaga session_id a tutti i nested spans usando propagate_attributes().
    """
    with langfuse.start_as_current_observation(
        as_type="span",
        name="streamlit_query",
        input={"query": query}
    ) as span:
        with propagate_attributes(
            session_id=str(session_id),
            metadata={"source": "streamlit"}
        ):
            yield span

async def trace_streamlit_query(query: str, session_id: UUID):
    """
    Wrapper per tracing query Streamlit.
    
    Returns: trace_id per query successiva costi
    """
    with with_streamlit_context(session_id, query) as span:
        # Esecuzione query avviene qui
        trace_id = span.trace_id
        return trace_id
```

---

## 6. Dettagli Implementativi Mancanti - RISOLTI ✅

### Estrazione Costo da Trace LangFuse

**Soluzione:** Query API SDK post-esecuzione o estrazione da `cost_details` nelle observations.

**Implementazione Raccomandata:**

```python
async def extract_cost_from_trace(trace_id: str) -> Decimal:
    """Estrae costo totale da trace LangFuse."""
    from langfuse import get_client
    from decimal import Decimal
    
    langfuse = get_client()
    trace = langfuse.api.trace.get(trace_id)
    
    total_cost = Decimal("0.0")
    for obs in trace.observations:
        if obs.type == "GENERATION":
            # Usa calculated_total_cost se disponibile
            cost = obs.calculated_total_cost or Decimal("0.0")
            total_cost += Decimal(str(cost))
    
    return total_cost
```

### Propagazione session_id ai Nested Spans

**Soluzione:** Usare `propagate_attributes()` context manager (verificato sopra).

### Gestione Errori PostgreSQL Fallback

**Implementazione Raccomandata:**

```python
async def get_session_stats_with_fallback(session_id: UUID) -> SessionStats:
    """Recupera statistiche con fallback in-memory."""
    try:
        return await get_session_stats(session_id)
    except Exception as e:
        logger.warning(f"DB unavailable, using in-memory fallback: {e}")
        # Fallback a st.session_state
        if 'session_stats' in st.session_state:
            return st.session_state.session_stats
        else:
            # Return default stats
            return SessionStats(
                session_id=session_id,
                query_count=0,
                total_cost=Decimal("0.0"),
                avg_latency_ms=Decimal("0.0"),
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
```

---

## 7. Riferimenti Documentazione Ufficiale

### LangFuse

- **Context Injection:** https://langfuse.com/docs/observability/sdk/python/instrumentation#propagating-trace-attributes
- **Cost Tracking:** https://langfuse.com/docs/observability/features/token-and-cost-tracking
- **Query Data via SDK:** https://langfuse.com/guides/cookbook/example_query_data_via_sdk
- **Python SDK Overview:** https://langfuse.com/docs/observability/sdk/python/overview

### Streamlit

- **Session State:** https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state
- **User Agent Discussion:** https://discuss.streamlit.io/t/getting-the-user-agent-of-the-current-session/25627

### PostgreSQL/AsyncPG

- **AsyncPG PyPI:** https://pypi.org/project/asyncpg/
- **PGVector GitHub:** https://github.com/pgvector/pgvector

---

## 8. Azioni Raccomandate

### Priorità ALTA

1. ✅ **Implementare `utils/langfuse_streamlit.py`** con `propagate_attributes()` verificato
2. ✅ **Implementare `utils/session_manager.py`** con tutte le funzioni documentate
3. ✅ **Rimuovere `user_agent`** dai metadata (non disponibile in Streamlit)
4. ✅ **Aggiornare AC3.2.4** per rimuovere riferimento a `user_agent`

### Priorità MEDIA

5. ✅ **Implementare estrazione costi** via API SDK post-esecuzione
6. ✅ **Documentare fallback PostgreSQL** con esempi codice
7. ⚠️ **Verificare versione Streamlit minima** con test (1.28+ invece di 1.31+)

### Priorità BASSA

8. ⚠️ **Specificare versione AsyncPG minima** dopo test
9. ✅ **Aggiungere link documentazione ufficiale** nel tech spec

---

## 9. Conclusioni

**Lacune Risolte:**

- ✅ LangFuse context injection: Metodo verificato (`propagate_attributes()`)
- ✅ Estrazione costi: Metodo verificato (API SDK post-esecuzione)
- ✅ Versioni dipendenze: Verificate (LangFuse 3.0.0+, PostgreSQL 16+)

**Lacune da Risolvere:**

- ❌ User agent: Non disponibile in Streamlit, rimuovere da tech spec
- ⚠️ Versione Streamlit: Verificare con test (probabilmente 1.28+ sufficiente)
- ⚠️ Versione AsyncPG: Specificare dopo test

**Moduli da Implementare:**

- `utils/session_manager.py`: Tutte le funzioni documentate
- `utils/langfuse_streamlit.py`: Con `propagate_attributes()` verificato

**Documentazione da Aggiornare:**

- Tech spec Epic 3: Rimuovere `user_agent`, aggiungere link documentazione ufficiale
- AC3.2.4: Rimuovere riferimento a `user_agent`

---

**Documento creato:** 2025-01-27  
**Fonti verificate:** LangFuse docs, Streamlit docs, GitHub discussions, PyPI

