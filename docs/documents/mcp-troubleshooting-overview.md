# Troubleshooting: get_knowledge_base_overview

## Problema

Quando si usa il tool `get_knowledge_base_overview` tramite MCP, si riceve il messaggio:

```
⚠️ RAG API Service is unavailable. Please check if the service is running at the configured endpoint.
```

## Cause Possibili

### 1. Servizio API non in esecuzione

Il servizio RAG API deve essere in esecuzione su `http://localhost:8000` per funzionare.

**Soluzione:**

```bash
# Avvia il servizio API
cd C:/Users/user/Desktop/Claude-Code/ottomator-agents/docling-rag-agent
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 2. Servizio API non riavviato dopo aggiornamenti

Se hai appena aggiunto il nuovo endpoint `/v1/overview`, il servizio deve essere riavviato per caricare le modifiche.

**Soluzione:**

1. Ferma il servizio API (Ctrl+C nel terminale dove è in esecuzione)
2. Riavvia il servizio:

```bash
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 3. Endpoint non disponibile

Verifica che l'endpoint `/v1/overview` sia disponibile.

**Soluzione:**

```bash
# Testa l'endpoint direttamente
curl http://localhost:8000/v1/overview

# Oppure usa lo script di verifica
uv run python scripts/verify_api_endpoints.py
```

## Verifica Rapida

### Step 1: Verifica Health Check

```bash
curl http://localhost:8000/health
```

Deve restituire: `{"status":"ok","timestamp":...}`

### Step 2: Verifica Overview Endpoint

```bash
curl http://localhost:8000/v1/overview
```

Deve restituire un JSON con statistiche della knowledge base.

### Step 3: Usa Script di Verifica

```bash
uv run python scripts/verify_api_endpoints.py
```

## Configurazione MCP

Assicurati che il server MCP sia configurato correttamente in Cursor:

```json
{
  "mcpServers": {
    "docling-rag": {
      "command": "uv",
      "args": ["run", "python", "mcp_server.py"],
      "env": {
        "DATABASE_URL": "...",
        "OPENAI_API_KEY": "..."
      }
    }
  }
}
```

## Note Importanti

- Il servizio API deve rimanere in esecuzione mentre usi il server MCP
- Se modifichi il codice dell'API (`api/main.py`), devi riavviare il servizio
- Il server MCP si connette all'API su `http://localhost:8000` (default)
- Se cambi la porta, aggiorna anche `RAGClient` in `client/api_client.py`


