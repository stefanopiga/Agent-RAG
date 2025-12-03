# Guida Configurazione LangFuse Dashboard

Questa guida descrive come configurare e utilizzare il dashboard LangFuse per monitorare le performance e i costi del Docling RAG Agent MCP Server.

## Prerequisiti

1. **LangFuse Account**: Cloud (cloud.langfuse.com) o self-hosted
2. **Variabili d'ambiente configurate**:
   ```env
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_BASE_URL=https://cloud.langfuse.com  # opzionale
   ```
3. **MCP Server avviato** con LangFuse abilitato

## Accesso al Dashboard

1. Accedi a [cloud.langfuse.com](https://cloud.langfuse.com) o al tuo server self-hosted
2. Seleziona il progetto "docling-rag-agent"
3. Naviga alla sezione **Dashboard** nel menu laterale

## Task 1: Configurazione Dashboard Views (AC #1)

### Metriche Chiave Disponibili

Il dashboard LangFuse mostra automaticamente le seguenti metriche:

| Metrica           | Descrizione                   | Fonte                      |
| ----------------- | ----------------------------- | -------------------------- |
| **Total Queries** | Numero totale di trace create | Conteggio automatico trace |
| **Avg Latency**   | Latenza media delle richieste | Campo `latency` del trace  |
| **Total Cost**    | Costo totale embedding + LLM  | Calcolato da token usage   |

### Configurazione Time Period Filters

1. Nella barra superiore del dashboard, clicca sul selettore temporale
2. Seleziona il periodo desiderato:
   - **Today**: Ultime 24 ore
   - **Last 7 days**: Ultima settimana
   - **Last 30 days**: Ultimo mese
   - **Custom**: Range personalizzato

### Verifica Metriche

Le metriche sono calcolate automaticamente dai trace creati dal MCP server:

```
Tool chiamato → Trace creato → Metriche aggregate
```

Per ogni tool MCP (`query_knowledge_base`, `ask_knowledge_base`, etc.) viene creato un trace con:

- `name`: Nome del tool (es. "query_knowledge_base")
- `metadata`: { tool_name, query, limit, source_filter, source: "mcp" }
- `latency`: Durata totale in millisecondi
- `cost`: Calcolato automaticamente da token usage

## Task 2: Cost Trends Visualization (AC #2)

### Visualizzazione Trend Costi

1. Vai a **Dashboard** → **Analytics**
2. Seleziona la visualizzazione **Cost over Time**
3. Configura il grafico:
   - **X-axis**: Time (daily/weekly/monthly aggregation)
   - **Y-axis**: Total Cost (USD)
   - **Group by**: Optional (tool_name per breakdown)

### Filtri Data Range

Il filtro data range è disponibile in tutte le visualizzazioni:

1. Clicca sul selettore data in alto a destra
2. Seleziona range predefinito o personalizzato
3. Il grafico si aggiorna automaticamente

### Aggregazione Costi

I costi sono aggregati da:

- **Embedding cost**: Calcolato da `text-embedding-3-small` ($0.00002/1K tokens)
- **LLM generation cost**: Calcolato da `gpt-4o-mini` ($0.00015/1K input, $0.0006/1K output)

Il costo viene tracciato automaticamente tramite il wrapper `langfuse.openai` nell'embedder.

## Task 3: Trace Detail View (AC #3)

### Accesso ai Dettagli Trace

1. Vai a **Traces** nel menu laterale
2. Clicca su un trace per vedere i dettagli

### Informazioni Visualizzate

Ogni trace mostra:

#### Input Query Text

```
metadata.query: "Come configurare LangFuse?"
```

#### Output Response

```
output: "[Source: langfuse-docs/setup]\nPer configurare LangFuse..."
```

#### Cost Breakdown

```
cost:
  embedding_cost: $0.000012  (embedding-generation span)
  llm_generation_cost: $0.000045  (se presente span llm-generation)
  total: $0.000057
```

#### Timing Breakdown

```
latency: 1234ms (totale)
spans:
  - embedding-generation: 234ms (metadata.duration_ms)
  - vector-search: 45ms (metadata.duration_ms)
```

#### Nested Spans

I trace contengono span gerarchici:

```
query_knowledge_base (root trace)
├── embedding-generation (span)
│   ├── duration_ms: 234
│   ├── model: text-embedding-3-small
│   └── embedding_dim: 1536
└── vector-search (span)
    ├── duration_ms: 45
    ├── limit: 5
    └── results_count: 3
```

### Navigazione Spans

1. Nel detail view del trace, scorri verso il basso
2. La sezione **Observations** mostra tutti gli span
3. Clicca su uno span per vedere i dettagli specifici

## Task 4: Custom Charts Configuration (AC #4)

### Creazione Custom Chart

1. Vai a **Dashboard** → clicca **+ Add Chart**
2. Configura i parametri:

#### Chart per Cost Trends (Raccomandato)

| Parametro      | Valore                                       |
| -------------- | -------------------------------------------- |
| **Chart Type** | Line Chart                                   |
| **Metric**     | Total Cost                                   |
| **Dimension**  | Time (day/week/month)                        |
| **Filter**     | Optional: tool_name = "query_knowledge_base" |

#### Chart per Latency Distribution

| Parametro      | Valore          |
| -------------- | --------------- |
| **Chart Type** | Bar Chart       |
| **Metric**     | Average Latency |
| **Dimension**  | tool_name       |
| **Filter**     | Nessuno         |

### Salvataggio Custom Charts

1. Dopo aver configurato il chart, clicca **Save**
2. Il chart viene aggiunto al dashboard
3. I chart sono persistenti e accessibili in tutte le sessioni

### Dimensioni Disponibili

| Dimensione           | Uso                          |
| -------------------- | ---------------------------- |
| `time`               | Aggregazione temporale       |
| `name`               | Nome del trace (tool_name)   |
| `user_id`            | ID utente (se configurato)   |
| `session_id`         | ID sessione (se configurato) |
| `metadata.source`    | Filtro per "mcp"             |
| `metadata.tool_name` | Filtro per tool specifico    |

### Metriche Disponibili

| Metrica      | Descrizione           |
| ------------ | --------------------- |
| `count`      | Numero di trace       |
| `totalCost`  | Costo totale          |
| `avgLatency` | Latenza media         |
| `p50Latency` | Latenza percentile 50 |
| `p95Latency` | Latenza percentile 95 |
| `p99Latency` | Latenza percentile 99 |

## Integrazione con Prometheus

Per un monitoring completo, combina LangFuse con Prometheus:

### LangFuse Dashboard

- Business metrics: costi, query trends, qualità
- Trace details: debugging, analisi

### Prometheus Metrics

- Infrastructure metrics: latenza, throughput, errori
- Alerting: SLO violations

### Endpoint Prometheus

```bash
# Avvia HTTP server per metriche
uv run python -m docling_mcp.http_server

# Scrape metriche
curl http://localhost:8080/metrics
```

### Metriche Prometheus Correlate

| LangFuse       | Prometheus                     |
| -------------- | ------------------------------ |
| Total Cost     | - (solo LangFuse)              |
| Avg Latency    | `mcp_request_duration_seconds` |
| Embedding Time | `rag_embedding_time_seconds`   |
| DB Search Time | `rag_db_search_time_seconds`   |

## Troubleshooting

### Trace Non Visibili

1. Verifica variabili d'ambiente `LANGFUSE_PUBLIC_KEY` e `LANGFUSE_SECRET_KEY`
2. Controlla che il server MCP sia avviato
3. Esegui una query di test e attendi 1-2 minuti per la propagazione

### Costi Non Calcolati

1. Verifica che l'embedder usi `langfuse.openai` wrapper
2. Controlla che il modello sia supportato per il pricing (text-embedding-3-small, gpt-4o-mini)
3. Verifica che i trace abbiano token usage popolato

### Span Timing Non Visibile

1. Verifica che gli span abbiano `metadata.duration_ms` popolato
2. Controlla i log del server MCP per errori span creation
3. Usa LangFuse debug mode per dettagli aggiuntivi

## Riferimenti

- [LangFuse Documentation](https://langfuse.com/docs)
- [LangFuse Custom Dashboards](https://langfuse.com/docs/analytics/custom-dashboards)
- [Architecture ADR-001](./architecture.md#ADR-001)
- [MCP Server Implementation](../docling_mcp/server.py)
