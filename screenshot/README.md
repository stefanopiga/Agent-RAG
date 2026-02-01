# Screenshot - DOCLING-RAG-AGENT

Questa cartella contiene screenshot che illustrano le funzionalità e i componenti principali del progetto **DOCLING-RAG-AGENT**.

## Panoramica

Il progetto DOCLING-RAG-AGENT è un sistema RAG (Retrieval Augmented Generation) che utilizza:
- **Docling** per l'elaborazione di documenti multi-formato
- **PydanticAI** per la gestione dell'agente conversazionale
- **PostgreSQL con PGVector** per lo storage vettoriale e la ricerca semantica
- **Streamlit** per l'interfaccia utente web
- **LangFuse** per l'osservabilità e il tracciamento delle performance

## Screenshot

### 1.png - Interfaccia Streamlit RAG Assistant

**Descrizione:**
Screenshot dell'interfaccia utente principale dell'applicazione Streamlit che mostra:

- **Sidebar sinistra:**
  - Titolo "RAG Assistant" con descrizione tecnologica
  - Sezione "Session Stats" con metriche in tempo reale:
    - Queries: numero di query effettuate
    - Cost: costo totale della sessione
    - Avg Latency: latenza media delle risposte
  - Pulsante "Clear Chat" per resettare la conversazione
  - Sezione "Documents" con istruzioni per l'ingestione
  - Pulsante "Trigger Ingestion (API)" per avviare il processo di ingestione documenti

- **Area principale:**
  - Interfaccia di chat "Knowledge Base Chat"
  - Esempio di interazione: domanda utente in italiano su installazione di PydanticAI su Windows
  - Risposta dell'assistente con istruzioni dettagliate e citazione delle fonti
  - Campo di input per nuove query

**Rilevanza per il progetto:**
Illustra il frontend operativo del sistema, dimostrando l'integrazione di Docling, PydanticAI e PostgreSQL per fornire risposte contestuali basate sulla knowledge base.

---

### 2.png - Dashboard LangFuse - Observations/Tracing

**Descrizione:**
Screenshot del dashboard LangFuse che mostra il tracciamento dettagliato delle operazioni del sistema:

- **Contesto progetto:** "hebly / docling-rag-agent" visibile nel selettore progetto

- **Tab "Observations":**
  - Filtri per tipo di operazione:
    - `OpenAI-generation` (1K eventi): chiamate per generazione testo LLM
    - `OpenAI-embedding` (663 eventi): chiamate per creazione embeddings
    - `streamlit_query` (6 eventi): query dall'interfaccia Streamlit

- **Tabella delle osservazioni** con colonne:
  - **Timestamp:** data/ora dell'evento
  - **Name:** tipo operazione (streamlit_query, OpenAI-generation, OpenAI-embedding)
  - **Input:** testo query o dati di input
  - **Output:** risultati dell'operazione
  - **Latency:** tempo di esecuzione (es. 22.8s, 1.62s, 0.29s)
  - **Tokens:** conteggio token input/output
  - **Total Cost:** costo in dollari per operazione
  - **Environment:** ambiente di esecuzione

- **Paginazione:** "Page 1 of 34" indica volume significativo di dati tracciati

**Rilevanza per il progetto:**
Fornisce visibilità completa sul comportamento del sistema, permettendo l'analisi di:
- Interazioni utente tramite Streamlit
- Operazioni di embedding per indicizzazione documenti
- Generazione risposte tramite LLM
- Metriche critiche: latenza, token count, costi

---

### 3.png - Dashboard LangFuse - Metriche Costi e Utilizzo

**Descrizione:**
Screenshot del dashboard LangFuse focalizzato su metriche di costo e utilizzo:

- **Sezione "Traces":**
  - **1.69K Total traces tracked:** totale interazioni registrate
  - Ripartizione per tipo:
    - `OpenAI-generation` (1.045): chiamate generazione testo
    - `OpenAI-embedding` (543): chiamate creazione embeddings
    - `streamlit_query` (6): query dall'interfaccia Streamlit

- **Sezione "Model costs":**
  - **$0.11665 Total cost:** costo cumulativo
  - Breakdown per modello:
    - `gpt-4o-mini`: 744.07K token, $0.111101
    - `gpt-4o-mini-2024-07-18`: 22.94K token, $0.004344
    - `text-embedding-ada-002-v2`: 6.69K token, $0.000020
    - `text-embedding-3-small`: 1.30K token, $0.000000

- **Grafico "Traces by time":**
  - Andamento attività nel tempo
  - Picco significativo tra 08:00-11:00 AM del 12/2/25

- **Sezione "Model Usage":**
  - Grafico costo nel tempo per modello
  - Filtri: Cost by model, Cost by type, Usage by model, Usage by type

**Rilevanza per il progetto:**
Consente il monitoraggio dei costi operativi del sistema, identificando:
- Modelli che contribuiscono maggiormente ai costi
- Pattern di utilizzo nel tempo
- Distribuzione costi tra embedding e generazione
- Ottimizzazione budget per operazioni RAG

---

### 4.png - Dashboard LangFuse - Metriche Performance e Latenza

**Descrizione:**
Screenshot del dashboard LangFuse focalizzato su metriche di performance:

- **Costo totale:** "$0.11665 Total cost" evidenziato

- **Tabella "Trace latency percentiles":**
  - `OpenAI.generate...`: latenze generazione (p50: 7.232s, p99: 56.923s)
  - `streamlit.query`: latenze query Streamlit
  - `OpenAI.embedding`: latenze embedding (p50: 0.381s, p99: 1.195s)

- **Tabelle aggiuntive:**
  - "Generation latency percentiles": approfondimento latenze generazione
  - "Span latency percentiles": latenze per span (es. streamlit.query)

- **Grafico "Model latencies (seconds) per LLM generation":**
  - Andamento temporale latenze (1 dicembre 2025, 8:00 AM - 8:00 PM)
  - Confronto modelli:
    - `gpt-4o-mini` (viola): picco ~4.00s tra 10:00-12:00 PM
    - `gpt-4o-mini-2024-01-19` (azzurro): picco ~1.00s nello stesso periodo
    - `text-embedding-3-small` e `text-embedding-ada-002-v2`: latenze basse e stabili (~0s)

- **Sezione "Scores Analytics":** "No data" (valutazione non ancora attiva)

**Rilevanza per il progetto:**
Fornisce dati critici per:
- Identificazione bottleneck di performance
- Confronto prestazioni modelli alternativi
- Ottimizzazione latenza embedding vs generazione
- Debug di periodi con latenze elevate
- Analisi distribuzione latenze (percentili)

---

### 5.png - Integrazione MCP Server in Cursor IDE

**Descrizione:**
Screenshot dell'ambiente di sviluppo (IDE, probabilmente Cursor) che mostra l'integrazione del MCP server:

- **File Explorer (sinistra):**
  - Struttura progetto `DOCLING-RAG-AGENT`
  - File `utils/session_manager.py` aperto nell'editor
  - Cartelle tipiche: `api`, `core`, `docling_mcp`, `ingestion`, `utils`, ecc.

- **Editor centrale:**
  - Codice Python: funzioni `create_session()` e `get_session_stats()`
  - Gestione sessioni con logica database e gestione errori

- **Terminale (basso):**
  - Output HTTP: `POST /v1/s` e `GET /health`
  - Indica API/server HTTP attivo

- **Pannello Assistente AI (destra, evidenziato):**
  - **Query utente (italiano):** "usa 'dodling-rag' dimmi come installare pydanticai su windows"
  - **Processo AI:**
    - "Thought for 2s"
    - "Ran ask_knowledge_base"
  - **Risposta AI:**
    - "Found 5 relevant results"
    - Result 1 (63.30% rilevanza) da fonte "Installation (pydantic-docs/docs/install.md)"
    - Istruzioni installazione: `pip install pydantic-ai` o `uv add pydantic-ai`
    - Requisiti: Python 3.10+
    - Opzione versione slim: `pip install pydantic-ai-slim`
    - Menzione integrazione Logfire opzionale

**Rilevanza per il progetto:**
Dimostra l'integrazione del **Model Context Protocol (MCP) server** che permette a Cursor IDE di:
- Accedere alla knowledge base direttamente dall'IDE
- Eseguire query semantiche sui documenti indicizzati
- Ottenere risposte contestuali con citazione fonti
- Supportare sviluppo con informazioni dalla documentazione indicizzata

Il MCP server è un componente chiave che estende le capacità dell'IDE con accesso intelligente alla knowledge base del progetto.

---

## Conclusione

Questi screenshot illustrano l'ecosistema completo del progetto DOCLING-RAG-AGENT:

1. **Frontend Streamlit** - Interfaccia utente per interazione conversazionale
2. **Osservabilità LangFuse** - Tracciamento completo di operazioni, costi e performance
3. **Integrazione IDE** - MCP server per accesso knowledge base da ambiente sviluppo

Il sistema fornisce un workflow completo dalla gestione documenti (Docling) alla ricerca semantica (PGVector), generazione risposte (PydanticAI) e monitoraggio operativo (LangFuse).
