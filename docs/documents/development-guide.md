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
# Run MCP server
uv run python mcp_server.py

# Configure in Cursor/Claude Desktop:
# Settings → MCP → Add Server
# Type: stdio
# Command: uv run python mcp_server.py
# Working Directory: /path/to/docling-rag-agent
```

## Development Workflow

### Project Structure

```
docling-rag-agent/
├── core/           # Business logic (agent + RAG service)
├── ingestion/      # Document processing pipeline
├── utils/          # Database & configuration utilities
├── sql/            # Database schema
├── documents/      # Documents to ingest
├── app.py          # Streamlit entry point
└── mcp_server.py   # MCP server entry point
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

**Build & Run:**

```bash
# Build image
docker-compose build

# Start Streamlit UI service
docker-compose up -d rag-agent

# Check logs
docker-compose logs -f rag-agent

# Stop services
docker-compose down
```

**Run Ingestion:**

```bash
# Default: CLEANS database first
docker-compose --profile ingestion up ingestion

# Keep existing data
docker-compose run --rm ingestion uv run python -m ingestion.ingest \
  --documents /app/documents \
  --no-clean
```

**Docker Configuration:**

- **Base Image:** `python:3.11-slim`
- **System Dependencies:** ffmpeg, gcc, postgresql-client, libpq-dev
- **Package Manager:** UV
- **Port:** 8501 (Streamlit)
- **Health Check:** `/_stcore/health` endpoint
- **Volumes:** `./documents:/app/documents`

### Environment Variables in Docker

```yaml
# docker-compose.yml
environment:
  DATABASE_URL: ${DATABASE_URL}
  OPENAI_API_KEY: ${OPENAI_API_KEY}
  LLM_CHOICE: ${LLM_CHOICE:-gpt-4o-mini}
  LOG_LEVEL: INFO
```

Uses `.env` file in project root.

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
