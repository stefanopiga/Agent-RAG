# Docker Image Optimization Guide

> Story 4.3 Implementation - 2025-11-30

## Overview

Questo documento descrive le ottimizzazioni applicate alle immagini Docker del progetto docling-rag-agent per ridurre le dimensioni e migliorare i tempi di build.

## Risultati Ottenuti

| Immagine      | Prima      | Dopo       | Riduzione   |
| ------------- | ---------- | ---------- | ----------- |
| **Streamlit** | 17.4GB     | **1.1GB**  | **-94%**    |
| **API**       | 32GB (bug) | **16.1GB** | **-50%**    |
| **MCP**       | 16.5GB     | **16.2GB** | Multi-stage |

## 1. Separazione Dipendenze (pyproject.toml)

**Prima:** Dipendenze monolitiche - tutti i servizi installavano docling[vlm] + PyTorch (~10GB)

**Dopo:** Gruppi opzionali separati:

```toml
[project.optional-dependencies]
streamlit = ["streamlit>=1.41", "pydantic-ai", "tenacity", "pydantic", ...]  # Leggero
api = ["fastapi", "uvicorn", "docling[vlm]", ...]                            # Con ML
mcp = ["fastmcp", "fastapi", "docling[vlm]", "prometheus_client", ...]       # Con ML
dev = ["pytest", "ruff", "mypy", ...]                                        # Solo dev
```

**Uso nei Dockerfile:**

```dockerfile
# Streamlit - dipendenze leggere
RUN uv sync --frozen --no-install-project --extra streamlit

# API - include ML
RUN uv sync --frozen --no-install-project --extra api

# MCP - include ML
RUN uv sync --frozen --no-install-project --extra mcp
```

## 2. Multi-Stage Build Pattern

Pattern applicato a tutti e tre i Dockerfile:

```dockerfile
# ============================================================
# BUILDER STAGE - dipendenze build-time
# ============================================================
FROM python:3.11-slim AS builder

# Build tools (NON presenti nello stage finale)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# UV per gestione dipendenze
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies con cache
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --extra <gruppo>

# Copy application code
COPY <app_files> .

# Install project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra <gruppo>

# ============================================================
# RUNTIME STAGE - solo runtime
# ============================================================
FROM python:3.11-slim AS runtime

# Solo runtime dependencies (curl per healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy SOLO virtual environment compilato
COPY --from=builder /app/.venv /app/.venv

# Copy SOLO file applicazione necessari
COPY --from=builder /app/<files> ./<files>

# NO build-essential, NO gcc, NO build tools
```

## 3. Fix Dockerfile Streamlit

**Modifiche principali:**

1. `COPY . .` → `COPY app.py client/ utils/` (solo file necessari)
2. `COPY --from=builder /app /app` → COPY selettivo
3. Rimosso `ffmpeg` (-470MB) - non utilizzato da Streamlit
4. Rimosso `postgresql-client` - non necessario
5. Aggiunto `--extra streamlit` per dipendenze leggere

## 4. Fix Dockerfile.api - Bug Critico

**Bug identificato:**

```dockerfile
# PRIMA (32GB!)
RUN useradd -m appuser && chown -R appuser /app
# ↑ Questo comando duplica TUTTO /app (incluso .venv da 16GB) in un nuovo layer
```

**Fix applicato:**

```dockerfile
# DOPO (16.1GB)
# Crea utente PRIMA del COPY
RUN useradd -m -u 1000 appuser

# Usa --chown nel COPY per settare ownership senza creare layer aggiuntivi
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/api ./api/
# etc...
```

**Spiegazione:**
- `chown -R` crea un nuovo layer Docker che duplica tutti i file modificati
- Con file da 16GB, questo raddoppia la dimensione dell'immagine
- `COPY --chown` setta l'ownership durante il copy senza layer aggiuntivi

## 5. Ottimizzazione Dockerfile.mcp

Convertito da single-stage a multi-stage:

- Builder stage con `build-essential` per compilazione native extensions
- Runtime stage con solo `curl` per healthcheck
- COPY selettivo delle directory necessarie

## 6. .dockerignore Aggiornato

Aggiunte esclusioni per ridurre build context:

```dockerignore
# Development directories
documents_copy_cooleman/
site/
tests/
docs/
scripts/
sql/

# Build artifacts
Dockerfile*
*.md
!README.md
```

## 7. CI/CD Aggiornato

In `.github/workflows/ci.yml`:

- Build step per `Dockerfile.mcp`
- Size check per tutte e tre le immagini
- Threshold 500MB configurato (warning, non hard fail per API/MCP)

## Note Tecniche Importanti

### Target <500MB non raggiunto per API/MCP

`docling[vlm]` richiede:
- PyTorch: ~2GB
- Transformers: ~500MB
- Modelli VLM: ~10GB

Queste dipendenze sono **necessarie** per la funzionalità di document processing con ML. Non è possibile ridurre ulteriormente senza rimuovere funzionalità core.

### Streamlit ottimizzato a 1.1GB

Streamlit non utilizza `docling[vlm]` direttamente - usa solo il client per chiamare l'API. Quindi può installare solo le dipendenze leggere.

### Cache UV

La cache UV è preservata tra build usando mount cache:

```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --extra streamlit
```

Questo velocizza significativamente i rebuild successivi.

### Layer Docker ottimizzati

Evitare sempre `chown -R` dopo COPY. Usare invece `COPY --chown`:

```dockerfile
# ❌ EVITARE
COPY --from=builder /app/.venv /app/.venv
RUN chown -R appuser:appuser /app

# ✅ CORRETTO
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
```

## Comandi Utili

### Build e verifica dimensione

```bash
# Build singola immagine
docker build -t docling-rag-agent:test -f Dockerfile .

# Verifica dimensione
docker images docling-rag-agent:test --format "{{.Size}}"

# Analisi layer
docker image history docling-rag-agent:test
```

### Build tutte le immagini

```bash
docker build -t docling-rag-agent:test -f Dockerfile .
docker build -t docling-rag-agent-api:test -f Dockerfile.api .
docker build -t docling-rag-agent-mcp:test -f Dockerfile.mcp .

# Verifica dimensioni
docker images | grep docling-rag-agent
```

## File Modificati (Story 4.3)

1. `pyproject.toml` - Gruppi dipendenze opzionali
2. `Dockerfile` - Multi-stage, COPY selettivo, rimosso ffmpeg
3. `Dockerfile.api` - Fix chown, COPY --chown pattern
4. `Dockerfile.mcp` - Convertito a multi-stage
5. `.dockerignore` - Esclusioni aggiuntive
6. `.github/workflows/ci.yml` - Build e size check MCP
7. `uv.lock` - Rigenerato con nuovi gruppi

