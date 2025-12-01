# Development Guide - docling-rag-agent

## Prerequisites

### System Requirements

- **Python:** 3.10 o successivo (3.11 raccomandato)
- **PostgreSQL:** Database con estensione PGVector
  - Supabase (cloud, recommended)
  - Neon (cloud)
  - Self-hosted PostgreSQL + PGVector extension
- **Package Manager:** UV (raccomandato) o pip
- **Docker:** (opzionale) Per deployment containerizzato

### API Keys Required

- **OpenAI API Key:** https://platform.openai.com/api-keys
  - Usato per: LLM + embeddings

## Quick Start

### 1. Clone & Setup

```bash
# Clone repository
git clone <repository-url>
cd docling-rag-agent

# Install UV package manager (se non installato)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### 2. Environment Configuration

Crea file `.env` nella root del progetto:

```bash
# Database Configuration
DATABASE_URL="postgresql://user:password@host:5432/dbname"

# OpenAI Configuration
OPENAI_API_KEY="sk-proj-..."

# Model Selection (optional - defaults shown)
LLM_CHOICE="gpt-4o-mini"
EMBEDDING_MODEL="text-embedding-3-small"

# Development Settings (optional)
LOG_LEVEL="INFO"
DEBUG_MODE="false"
```

**Database URL Examples:**

- **Supabase:** `postgresql://postgres.[project]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres`
- **Neon:** `postgresql://[user]:[password]@[endpoint].neon.tech/[dbname]`
- **Local:** `postgresql://localhost:5432/docling_rag`

### 3. Database Setup

```bash
# Connect to your PostgreSQL database and run schema
psql $DATABASE_URL < sql/schema.sql

# Or using Supabase/Neon SQL editor:
# Copy/paste contents of sql/schema.sql
```

**Schema crea:**

- Extension: `vector`, `uuid-ossp`
- Tables: `documents`, `chunks`
- Function: `match_chunks()` per vector search
- Indexes: IVFFlat (vectors), GIN (metadata), B-tree (FK)

**Epic 3 - Session Tracking (Opzionale):**

Per abilitare session tracking Streamlit UI:

```bash
# Esegui schema Epic 3
psql $DATABASE_URL < sql/epic-3-sessions-schema.sql
```

Crea tabelle:

- `sessions`: Session statistics (query_count, total_cost, avg_latency)
- `query_logs`: Query logging con costi e timing
- RLS policies `service_role` only (protezione completa)

### 4. Ingest Documents

```bash
# Add documents to the documents/ folder
# Supported: .pdf, .docx, .pptx, .xlsx, .html, .md, .txt

# Run ingestion (CLEANS database first by default)
uv run python -m ingestion.ingest --documents documents/

# Options:
# --no-clean          Keep existing documents (may create duplicates)
# --chunk-size 800    Custom chunk size (default: 1000)
# --chunk-overlap 150 Custom overlap (default: 200)
# --no-semantic       Disable HybridChunker (use SimpleChunker)
# --verbose           Debug logging
```

**⚠️ Important:** Default behavior **DELETES all existing documents** before ingestion to prevent duplicates.

### 5. Run Application

**Option A: Streamlit UI**

```bash
# Start web interface
uv run streamlit run app.py

# Opens browser at http://localhost:8501
```

**Option B: MCP Server (Cursor/Claude Desktop)**

```bash
# Run MCP server (stdio mode for Cursor/Claude Desktop)
uv run python mcp_server.py

# Configure in Cursor/Claude Desktop:
# Settings → MCP → Add Server
# Type: stdio
# Command: uv run python mcp_server.py
# Working Directory: /path/to/docling-rag-agent
```

**Option C: MCP HTTP Server (Observability Endpoints)**

```bash
# Start MCP HTTP server for metrics and health checks (porta 8080)
uv run python -m docling_mcp.http_server

# Server disponibile su http://localhost:8080
# Endpoints disponibili:
# - GET /health - Health check endpoint
# - GET /metrics - Prometheus metrics endpoint
# - GET /docs - API documentation (Swagger UI)

# Con porta personalizzata
METRICS_PORT=9090 uv run python -m docling_mcp.http_server
```

**Note:** Il MCP HTTP Server è separato dal MCP Server stdio. L'HTTP server espone endpoint di osservabilità (health check, metrics) e può essere utilizzato per monitoring e Kubernetes probes.

## Development Workflow

### Project Structure

```
docling-rag-agent/
├── core/           # Business logic (agent + RAG service)
├── ingestion/      # Document processing pipeline
├── docling_mcp/    # MCP server implementation
│   ├── http_server.py  # HTTP server for observability (porta 8080)
│   ├── health.py       # Health check logic
│   ├── metrics.py      # Prometheus metrics
│   └── server.py       # MCP server stdio implementation
├── api/            # FastAPI REST API service
├── utils/          # Database & configuration utilities
├── client/         # API client utilities
├── sql/            # Database schema
├── documents/      # Documents to ingest
├── app.py          # Streamlit entry point
└── mcp_server.py   # MCP server entry point (stdio)
```

### Running Tests

```bash
# Run pytest (if tests exist)
uv run pytest

# Run specific test file
uv run pytest tests/test_embedder.py

# With coverage
uv run pytest --cov=. --cov-report=html
```

### Code Quality

**Linting & Formatting:**

```bash
# Black formatter (line length: 100)
uv run black . --line-length 100

# Ruff linter
uv run ruff check .

# Type checking with mypy
uv run mypy core/ ingestion/ utils/
```

**Configuration in `pyproject.toml`:**

- Black: line-length 100, target Python 3.10+
- Ruff: E, F, I, N, W rules
- Mypy: Python 3.10, ignore missing imports

### Development Commands

```bash
# Install new dependency
uv add <package-name>

# Install dev dependency
uv add --dev <package-name>

# Update dependencies
uv sync

# Run Python script
uv run python script.py

# Run module
uv run python -m module.name

# Activate virtual environment (optional)
source .venv/bin/activate  # Unix
.venv\Scripts\activate     # Windows
```

### Database Operations

**Reset Database (keep schema):**

```bash
psql $DATABASE_URL < sql/removeDocuments.sql
```

**Recreate Schema (destructive):**

```bash
# In psql or SQL editor
DROP TABLE IF EXISTS chunks CASCADE;
DROP TABLE IF EXISTS documents CASCADE;

# Then run
psql $DATABASE_URL < sql/schema.sql
```

**Check Database Stats:**

```sql
-- Document count
SELECT COUNT(*) FROM documents;

-- Chunk count
SELECT COUNT(*) FROM chunks;

-- Chunks per document
SELECT
    d.title,
    COUNT(c.id) as chunk_count
FROM documents d
LEFT JOIN chunks c ON d.id = c.document_id
GROUP BY d.id, d.title;

-- Average similarity scores (test query)
SELECT
    AVG(1 - (embedding <=> '[...]'::vector)) as avg_similarity
FROM chunks
WHERE embedding IS NOT NULL;
```

## Deployment

### Docker Deployment

Il progetto supporta deployment completo con Docker Compose, includendo tutti i servizi necessari per sviluppo e produzione.

**Servizi Disponibili:**

- **`rag-api`**: FastAPI REST API service (porta 8000)
- **`mcp-server`**: MCP HTTP Server per observability (porta 8080)
- **`streamlit`**: Streamlit web UI (porta 8501)
- **`db`**: PostgreSQL database con PGVector extension (porta 5432)

**Build & Run:**

```bash
# Build tutte le immagini
docker compose build

# Avvia tutti i servizi
docker compose up -d

# Avvia solo servizi specifici
docker compose up -d db rag-api
docker compose up -d db mcp-server streamlit

# Verifica stato servizi
docker compose ps

# Visualizza logs
docker compose logs -f rag-api
docker compose logs -f mcp-server
docker compose logs -f streamlit

# Stop tutti i servizi
docker compose down

# Stop e rimuovi volumi (ATTENZIONE: cancella dati database)
docker compose down -v
```

**Verifica Health Checks:**

```bash
# API Server health check
curl http://localhost:8000/health

# MCP Server health check
curl http://localhost:8080/health

# Streamlit health check
curl http://localhost:8501/_stcore/health
```

**Run Ingestion:**

```bash
# Default: CLEANS database first
docker-compose --profile ingestion up ingestion

# Keep existing data
docker compose run --rm ingestion uv run python -m ingestion.ingest \
  --documents /app/documents \
  --no-clean
```

**Docker Configuration:**

**Streamlit (`Dockerfile`):**

- **Base Image:** `python:3.11-slim-bookworm`
- **System Dependencies:** ffmpeg, build-essential, postgresql-client, libpq-dev, curl
- **Package Manager:** UV
- **Port:** 8501
- **Health Check:** `/_stcore/health` endpoint
- **Volumes:** `./documents:/app/documents`

**API Server (`Dockerfile.api`):**

- **Base Image:** `python:3.11-slim`
- **System Dependencies:** build-essential, curl
- **Package Manager:** UV
- **Port:** 8000
- **Health Check:** `/health` endpoint

**MCP Server (`Dockerfile.mcp`):**

- **Base Image:** `python:3.11-slim`
- **System Dependencies:** build-essential, curl
- **Package Manager:** UV
- **Port:** 8080
- **Health Check:** `/health` endpoint
- **Environment:** `METRICS_PORT=8080`

**Database (`docker-compose.yml`):**

- **Image:** `pgvector/pgvector:pg16`
- **Port:** 5432
- **Health Check:** `pg_isready -U postgres`
- **Volumes:** `postgres_data` (persistenza dati)

### Environment Variables in Docker

```yaml
# docker-compose.yml
environment:
  DATABASE_URL: postgresql://postgres:postgres@db:5432/ragdb
  OPENAI_API_KEY: ${OPENAI_API_KEY}
  OPENAI_BASE_URL: ${OPENAI_BASE_URL}
  EMBEDDING_MODEL: ${EMBEDDING_MODEL:-text-embedding-3-small}
  LLM_CHOICE: ${LLM_CHOICE:-gpt-4.1-mini}
  METRICS_PORT: 8080 # Solo per mcp-server
```

Le variabili vengono caricate dal file `.env` nella root del progetto.

### Local Development vs Docker

**Sviluppo Locale:**

- Servizi avviati manualmente in terminali separati
- Hot-reload automatico durante sviluppo
- Debug più semplice con breakpoints
- Accesso diretto ai log nel terminale
- Nessuna build Docker necessaria

**Docker Compose:**

- Tutti i servizi orchestati automaticamente
- Ambiente isolato e riproducibile
- Simula ambiente produzione
- Health checks automatici
- Networking tra servizi gestito automaticamente

**Quando Usare:**

- **Locale**: Sviluppo attivo, debugging, testing rapido
- **Docker**: Testing integrazione, CI/CD, deployment, ambiente production-like

### Production Considerations

**Security:**

- ✅ Never commit `.env` file
- ✅ Use secrets management (AWS Secrets Manager, Azure Key Vault)
- ✅ Rotate API keys periodically
- ✅ Restrict database access (IP whitelist, VPC)

**Performance:**

- ✅ Connection pooling: 5-20 connections (adjust based on load)
- ✅ PGVector index tuning: `WITH (lists = N)` where N = rows/1000
- ✅ Batch size tuning: Embedder batch_size (default: 100)
- ✅ Cache frequently queried embeddings

**Monitoring:**

- ✅ Database query performance (slow query log)
- ✅ OpenAI API usage (tokens, rate limits)
- ✅ Connection pool stats (active/idle connections)
- ✅ Streamlit metrics (active users, response times)

**Scalability:**

- ✅ Horizontal: Multiple Streamlit instances behind load balancer
- ✅ Database: PostgreSQL read replicas for search queries
- ✅ Caching: Redis for embedding cache
- ✅ CDN: Static assets (if serving files)

## Troubleshooting

### Common Issues

**1. Database Connection Fails**

```
Error: connection to server ... failed
```

**Solution:**

- Verify `DATABASE_URL` in `.env`
- Check database is running
- Verify network access (firewall, VPC)
- Test connection: `psql $DATABASE_URL`

**2. PGVector Extension Missing**

```
ERROR: type "vector" does not exist
```

**Solution:**

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**3. OpenAI Rate Limit**

```
RateLimitError: Rate limit exceeded
```

**Solution:**

- Reduce batch size in embedder
- Add delays between batches
- Upgrade OpenAI tier/quota

**4. Out of Memory during Ingestion**

```
MemoryError: ...
```

**Solution:**

- Reduce chunk_size
- Process fewer documents per batch
- Increase Docker memory limit
- Process documents sequentially

**5. Streamlit Port Already in Use**

```
Address already in use
```

**Solution:**

```bash
# Find process
lsof -i :8501  # Unix
netstat -ano | findstr :8501  # Windows

# Kill process or use different port
streamlit run app.py --server.port 8502
```

**6. MCP HTTP Server Port Already in Use**

```
Address already in use: 8080
```

**Solution:**

```bash
# Find process using port 8080
lsof -i :8080  # Unix
netstat -ano | findstr :8080  # Windows

# Kill process or use different port
METRICS_PORT=9090 uv run python -m docling_mcp.http_server
```

**7. Docker Services Not Starting**

```
Error: service "mcp-server" failed to start
```

**Solution:**

```bash
# Verifica logs del servizio
docker compose logs mcp-server

# Verifica che database sia healthy
docker compose ps db

# Riavvia servizi
docker compose restart mcp-server

# Rebuild se necessario
docker compose build mcp-server
docker compose up -d mcp-server
```

**8. MCP Server Health Check Fails in Docker**

```
ERROR: Health check status is 'down'
```

**Solution:**

```bash
# Verifica che database sia raggiungibile dal container
docker compose exec mcp-server psql $DATABASE_URL -c "SELECT 1"

# Verifica variabili ambiente
docker compose exec mcp-server env | grep DATABASE_URL

# Verifica che API server sia raggiungibile (se necessario)
docker compose exec mcp-server curl -f http://rag-api:8000/health
```

**9. Docker Compose Network Issues**

```
Error: network "docling-rag-agent_rag-network" not found
```

**Solution:**

```bash
# Ricrea network
docker compose down
docker compose up -d

# Verifica network
docker network ls | grep rag-network
```

### Debug Mode

Enable verbose logging:

```bash
# In .env
LOG_LEVEL="DEBUG"
DEBUG_MODE="true"

# Or via command line
LOG_LEVEL=DEBUG uv run streamlit run app.py
```

### Performance Profiling

```python
# Add timing to queries
import time

start = time.time()
result = await db_pool.acquire()
print(f"Query took: {time.time() - start:.2f}s")
```

## Contributing Workflow

1. Fork repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes
4. Run linters: `black .`, `ruff check .`
5. Run tests: `pytest`
6. Commit: `git commit -m "feat: add feature"`
7. Push: `git push origin feature/my-feature`
8. Create Pull Request

## Resources

- **Docling Documentation:** https://github.com/DS4SD/docling
- **PydanticAI Documentation:** https://ai.pydantic.dev
- **PGVector Documentation:** https://github.com/pgvector/pgvector
- **Streamlit Documentation:** https://docs.streamlit.io
- **FastMCP Documentation:** https://github.com/jlowin/fastmcp
- **UV Documentation:** https://github.com/astral-sh/uv
- **Docker Compose Documentation:** https://docs.docker.com/compose/
- **Health Check Endpoints:** Vedi `docs/health-check-endpoints.md` per documentazione completa degli endpoint
