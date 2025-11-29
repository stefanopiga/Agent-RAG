# Health Check Endpoints

Documentazione degli endpoint health check per monitoraggio e alerting in produzione.

## Panoramica

Il sistema espone tre health check endpoints per monitorare lo stato dei servizi:

| Servizio | Endpoint | Porta | Descrizione |
|----------|----------|-------|-------------|
| MCP Server | `/health` | 8080 | Health check con status dettagliato |
| API Server | `/health` | 8000 | Health check con verifica database |
| Streamlit | `/_stcore/health` | 8501 | Built-in health check |

## Status Logic

Gli endpoint restituiscono uno dei tre stati:

| Status | HTTP Code | Significato |
|--------|-----------|-------------|
| `ok` | 200 | Tutti i servizi operativi |
| `degraded` | 200 | LangFuse non disponibile (non critico) |
| `down` | 503 | Database o embedder non disponibile (critico) |

### Dipendenze Critiche vs Non-Critiche

- **Critiche** (status "down" se non disponibili):
  - Database PostgreSQL
  - Embedder
  
- **Non-Critiche** (status "degraded" se non disponibili):
  - LangFuse (telemetria)

## MCP Server Health Check

**Endpoint**: `GET /health` (porta 8080)

**Response JSON**:

```json
{
  "status": "ok",
  "timestamp": 1706445600.123,
  "services": {
    "database": {
      "status": "up",
      "message": "PostgreSQL connection successful",
      "latency_ms": 5.2
    },
    "langfuse": {
      "status": "up",
      "message": "LangFuse client initialized",
      "latency_ms": 1.0
    },
    "embedder": {
      "status": "up",
      "message": "Embedder initialized and ready",
      "latency_ms": 2.0
    }
  }
}
```

**Esempi curl**:

```bash
# Health check MCP server
curl -sf http://localhost:8080/health | jq

# Verifica status
curl -sf http://localhost:8080/health | jq -r '.status'
```

## API Server Health Check

**Endpoint**: `GET /health` (porta 8000)

**Response JSON**:

```json
{
  "status": "ok",
  "timestamp": 1706445600.123,
  "services": {
    "database": {
      "status": "up",
      "message": "PostgreSQL connection successful"
    }
  }
}
```

**Esempi curl**:

```bash
# Health check API server
curl -sf http://localhost:8000/health | jq

# Verifica status
curl -sf http://localhost:8000/health | jq -r '.status'
```

## Streamlit Health Check

**Endpoint**: `GET /_stcore/health` (porta 8501)

Endpoint built-in di Streamlit. Restituisce HTTP 200 quando l'app è running.

```bash
# Health check Streamlit
curl -sf http://localhost:8501/_stcore/health
```

## Docker HEALTHCHECK

I Dockerfile includono configurazione HEALTHCHECK:

### Streamlit (Dockerfile)

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1
```

### API Server (Dockerfile.api)

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

## Kubernetes Integration

Gli endpoint sono compatibili con Kubernetes liveness/readiness probes:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

## Monitoring e Alerting

Configura alerting basato su:

1. **HTTP Status Code**:
   - Alert se status code != 200 per più di 2 minuti
   
2. **Response Status**:
   - Alert se `status == "down"` per più di 1 minuto
   - Warning se `status == "degraded"` per più di 5 minuti

3. **Latenza**:
   - Warning se `latency_ms > 100ms` per database
   - Alert se `latency_ms > 500ms` per database

