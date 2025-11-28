# Guida al Troubleshooting

Questa guida fornisce soluzioni per i problemi più comuni nel progetto Docling RAG Agent, con focus particolare sulla configurazione e troubleshooting del server MCP.

## Indice

- [Requisiti Critici](#requisiti-critici)
- [Troubleshooting MCP Server](#troubleshooting-mcp-server)
- [Problemi di Connessione Database](#problemi-di-connessione-database)
- [Problemi di Ambiente](#problemi-di-ambiente)
- [Script di Verifica](#script-di-verifica)
- [Avvio Automatico API (Windows)](#avvio-automatico-api-windows)

---

## Requisiti Critici

### API RAG

**Il server MCP richiede che l'API RAG sia in esecuzione su `http://localhost:8000`.**

#### Avvio API RAG (OBBLIGATORIO)

```bash
cd C:/Users/user/Desktop/Claude-Code/ottomator-agents/docling-rag-agent
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

L'API deve rimanere in esecuzione in un terminale separato mentre usi il server MCP in Cursor.

#### Verifica API Attiva

```bash
curl http://localhost:8000/health
# Deve restituire: {"status":"ok","timestamp":...}
```

---

## Troubleshooting MCP Server

### Problema: Tool Non Disponibile

Il tool `query_knowledge_base` non è disponibile in Cursor, anche se è registrato correttamente nel server.

### Diagnostica

```bash
uv run python debug_mcp_tools.py
```

**Risultato atteso:** Entrambi i tool sono registrati correttamente:

- `query_knowledge_base` ✅
- `list_knowledge_base_documents` ✅

### Step 1: Verifica Configurazione MCP

Il file di configurazione MCP si trova in:

| Sistema Operativo | Percorso                                                                                                   |
| ----------------- | ---------------------------------------------------------------------------------------------------------- |
| **Windows**       | `%APPDATA%\Cursor\User\globalStorage\rooveterinaryinc.roo-cline\settings\cline_mcp_settings.json`         |
| **Mac**           | `~/Library/Application Support/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json` |
| **Linux**         | `~/.config/Cursor/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json`         |

In alternativa, configurazione workspace in `.cursor/mcp.json` (se supportato).

### Step 2: Configurazione Corretta

Per Cursor, la configurazione dovrebbe essere:

```json
{
  "mcpServers": {
    "docling-rag": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "C:/Users/user/Desktop/Claude-Code/ottomator-agents/docling-rag-agent",
        "python",
        "-m", "docling_mcp.server"
      ],
      "cwd": "C:/Users/user/Desktop/Claude-Code/ottomator-agents/docling-rag-agent",
      "env": {
        "PYTHONPATH": "C:/Users/user/Desktop/Claude-Code/ottomator-agents/docling-rag-agent"
      }
    }
  }
}
```

**Nota:** Usa percorsi assoluti per Windows.

### Step 3: Verifica Server Avviato

1. Apri Cursor Settings (`Ctrl+Shift+J` o `Cmd+Shift+J`)
2. Vai a **Features > MCP**
3. Verifica che `docling-rag` sia presente e abbia un indicatore verde (attivo)
4. Se non è presente o è rosso:
   - Controlla i log MCP in Cursor
   - Verifica che il comando `uv run python -m docling_mcp.server` funzioni manualmente

### Step 4: Test Manuale Server

```bash
cd C:/Users/user/Desktop/Claude-Code/ottomator-agents/docling-rag-agent
uv run python -m docling_mcp.server
```

Il server dovrebbe avviarsi senza errori. Premi `Ctrl+C` per fermarlo.

### Step 5: Restart Cursor

Dopo aver configurato correttamente:

1. Chiudi completamente Cursor
2. Riapri Cursor
3. Il server MCP dovrebbe avviarsi automaticamente

### Step 6: Verifica Tool Disponibili

In Cursor, prova a chiamare:

```
Usa il tool mcp_docling-rag_query_knowledge_base per cercare informazioni su Pydantic AI
```

Se il tool non è ancora disponibile, controlla i log MCP per errori.

### Configurazione Alternativa (se stdio non funziona)

Se la configurazione stdio non funziona, prova con percorsi assoluti:

```json
{
  "mcpServers": {
    "docling-rag": {
      "command": "C:/Users/user/.cargo/bin/uv.exe",
      "args": [
        "run",
        "--project",
        "C:/Users/user/Desktop/Claude-Code/ottomator-agents/docling-rag-agent",
        "python",
        "-m", "docling_mcp.server"
      ],
      "cwd": "C:/Users/user/Desktop/Claude-Code/ottomator-agents/docling-rag-agent"
    }
  }
}
```

### Configurazione Cursor - Metodo GUI

1. Apri Cursor Settings:
   - `Ctrl+Shift+J` (Windows/Linux)
   - `Cmd+Shift+J` (Mac)

2. Naviga a **Features > MCP** (o **Tools & Integrations > MCP**)

3. Clicca **"Add Server"** o **"Add Custom MCP"**

4. Configura:
   - **Name:** `docling-rag`
   - **Type:** `stdio`
   - **Command:** `uv`
   - **Args:** `run --project C:/Users/user/Desktop/Claude-Code/ottomator-agents/docling-rag-agent python -m docling_mcp.server`
   - **Working Directory:** `C:/Users/user/Desktop/Claude-Code/ottomator-agents/docling-rag-agent`

5. Salva e riavvia Cursor completamente

### Log per Debug

Se il problema persiste, controlla:

- Log MCP in Cursor: `View > Output > MCP Servers`
- Log del server: esegui manualmente `uv run python -m docling_mcp.server` e verifica errori
- Variabili d'ambiente: verifica che `.env` sia configurato correttamente
- Esegui verifica completa: `uv run python scripts/verify_mcp_setup.py`

### Note Importanti

- Il server MCP deve essere avviato da Cursor, non manualmente
- Assicurati che `uv` sia nel PATH o usa il percorso assoluto
- Verifica che tutte le dipendenze siano installate: `uv sync`
- Il server richiede che l'API RAG sia disponibile (verifica `client.api_client.RAGClient`)

---

## Problemi di Connessione Database

### Problemi Comuni

| Problema                       | Causa                      | Soluzione                                                                        |
| ------------------------------ | -------------------------- | -------------------------------------------------------------------------------- |
| `connection refused`           | Database non raggiungibile | Verifica `DATABASE_URL` e che PostgreSQL sia attivo                              |
| `extension "vector" not found` | PGVector non installato    | Esegui `CREATE EXTENSION vector;` o usa immagine Docker `pgvector/pgvector:pg16` |

### Verifica Connessione

```bash
# Verifica connessione
psql $DATABASE_URL -c "SELECT 1"

# Verifica estensione PGVector
psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname = 'vector'"

# Test performance index
python scripts/optimize_database.py --check
```

---

## Problemi di Ambiente

### Problemi Comuni

| Problema                  | Causa                 | Soluzione                                            |
| ------------------------- | --------------------- | ---------------------------------------------------- |
| `OPENAI_API_KEY not set`  | Variabile mancante    | Aggiungi `OPENAI_API_KEY` nel file `.env`            |
| `uv: command not found`   | UV non installato     | Installa: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `Python version mismatch` | Python < 3.10         | Aggiorna Python a 3.10+                              |
| `ImportError: docling`    | Dipendenze mancanti   | Esegui `uv sync`                                     |

### Reset Ambiente

```bash
# Rimuovi cache e reinstalla
rm -rf .venv
uv sync

# Reset database (ATTENZIONE: cancella tutti i dati)
psql $DATABASE_URL < sql/optimize_index.sql
```

---

## Script di Verifica

### Verifica Completa Setup MCP

```bash
uv run python scripts/verify_mcp_setup.py
```

Lo script verifica:

- ✅ Dipendenze installate
- ✅ Variabili d'ambiente configurate
- ✅ Server MCP inizializzato correttamente
- ✅ Tool registrati (`query_knowledge_base`, `list_knowledge_base_documents`)
- ✅ API RAG disponibile e accessibile
- ⚠️ Configurazione Cursor (se trovata)

### Verifica Tool

Dopo la configurazione, verifica che entrambi i tool siano disponibili:

1. `mcp_docling-rag_query_knowledge_base` - Per ricerche semantiche
2. `mcp_docling-rag_list_knowledge_base_documents` - Per elencare documenti

---

## Avvio Automatico API (Windows)

Script disponibili in `scripts/`:

### Avvio Manuale

```bash
# Con finestra visibile
scripts\start_api.bat

# Oppure da terminale
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Arresto API

```bash
scripts\stop_api.bat
```

### Configurazione Avvio Automatico al Login

1. **Esegui come Amministratore:**

   ```bash
   scripts\install_autostart.bat
   ```

2. L'API si avvierà automaticamente al prossimo login Windows

3. **Per avviare subito (senza riavvio):**

   ```bash
   schtasks /run /tn "DoclingRAG-API"
   ```

### Rimozione Avvio Automatico

```bash
scripts\uninstall_autostart.bat
```

### File Script

| Script                    | Descrizione                       |
| ------------------------- | --------------------------------- |
| `start_api.bat`           | Avvio manuale con finestra        |
| `start_api_hidden.vbs`    | Avvio silenzioso (background)     |
| `stop_api.bat`            | Arresto API                       |
| `install_autostart.bat`   | Installa avvio automatico (Admin) |
| `uninstall_autostart.bat` | Rimuovi avvio automatico          |

