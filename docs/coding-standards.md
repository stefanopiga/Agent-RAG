# Coding Standards - docling-rag-agent

**Version:** 1.0  
**Last Updated:** 2025-01-27  
**Python Version:** >=3.10

## Overview

Questo documento definisce gli standard di codice per il progetto `docling-rag-agent`. Gli standard riflettono le pratiche consolidate nel codice esistente e garantiscono coerenza, manutenibilità e qualità del codice.

**Principi Fondamentali:**

- **Type Safety**: Type hints obbligatori per tutte le funzioni pubbliche
- **Documentation First**: Docstrings completi con formato standardizzato
- **Graceful Degradation**: Gestione robusta di dipendenze opzionali
- **Observability**: Logging strutturato e tracing integrato
- **Test-Driven**: Coverage minimo 70% con test organizzati rigorosamente

---

## 1. Python Style Guide

### 1.1 Formattazione

**Line Length:**

- Massimo 100 caratteri per riga (configurato in `pyproject.toml`)
- Usare parentesi per continuare su più righe quando necessario

**Indentazione:**

- 4 spazi (no tab)
- Allineamento per parametri multipli quando necessario

**Esempio:**

```python
# ✅ Corretto
async def search_knowledge_base(
    query: str,
    limit: int = 5,
    source_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search knowledge base with optional source filtering."""
    pass

# ❌ Errato
async def search_knowledge_base(query: str, limit: int = 5, source_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    pass
```

### 1.2 Import Organization

**Ordine degli import:**

1. Standard library
2. Third-party packages
3. Local application imports

**Separazione:**

- Una riga vuota tra ogni gruppo
- Import assoluti preferiti (no relative imports)

**Esempio:**

```python
# Standard library
import logging
import time
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

# Third-party
from fastmcp import FastMCP
from langfuse import observe

# Local imports
from core.rag_service import search_knowledge_base_structured
from docling_mcp.metrics import record_request_start, record_request_end
```

### 1.3 Type Hints

**Obbligatori per:**

- Tutte le funzioni pubbliche (non private)
- Parametri di funzione
- Valori di ritorno
- Variabili di classe pubbliche

**Optional e Union:**

- Usare `Optional[T]` invece di `Union[T, None]`
- Usare `Literal` per valori fissi (es. status codes)

**Esempio:**

```python
from typing import List, Dict, Any, Optional, Literal

# ✅ Corretto
async def check_database() -> ServiceStatus:
    """Check database connectivity."""
    pass

@dataclass
class HealthResponse:
    status: Literal["ok", "degraded", "down"]
    timestamp: float
    services: Dict[str, Dict[str, Any]]

# ❌ Errato
async def check_database():
    pass
```

---

## 2. Naming Conventions

### 2.1 File e Directory

**File Python:**

- `snake_case.py` (es. `rag_service.py`, `mcp_server.py`)
- Test files: `test_*.py` o `*_test.py` (es. `test_rag_service.py`)

**Directory:**

- `snake_case/` (es. `docling_mcp/`, `core/`, `ingestion/`)

**Esempio:**

```
docling_mcp/
├── server.py
├── metrics.py
├── health.py
└── tools/
    ├── search.py
    └── documents.py
```

### 2.2 Codice

**Classi:**

- `PascalCase` (es. `EmbeddingGenerator`, `DatabasePool`, `ServiceStatus`)

**Funzioni e Variabili:**

- `snake_case` (es. `query_knowledge_base`, `search_results`, `embedding_time`)

**Costanti:**

- `UPPER_SNAKE_CASE` (es. `MAX_RETRIES`, `DEFAULT_LIMIT`, `CACHE_SIZE`)

**Private/Internal:**

- Prefisso `_` per funzioni/variabili private (es. `_global_embedder`, `_initialize_metrics()`)

**Esempio:**

```python
# Costanti
MAX_RETRIES = 3
DEFAULT_BATCH_SIZE = 100

# Classe pubblica
class EmbeddingGenerator:
    # Variabile privata
    _cache: Dict[str, List[float]]

    # Metodo pubblico
    async def embed_query(self, text: str) -> List[float]:
        pass

    # Metodo privato
    def _get_from_cache(self, text: str) -> Optional[List[float]]:
        pass
```

### 2.3 Database

**Tabelle:**

- `snake_case`, plurale (es. `documents`, `chunks`)

**Colonne:**

- `snake_case` (es. `document_id`, `chunk_content`, `created_at`)

**Indici:**

- `idx_<table>_<column>_<type>` (es. `idx_chunks_embedding_hnsw`)

---

## 3. Documentation Standards

### 3.1 Module Docstrings

Ogni modulo deve iniziare con un docstring che descrive:

- Scopo del modulo
- Architettura/pattern utilizzati
- Componenti principali

**Esempio:**

```python
"""
MCP Server
==========
Exposes the RAG agent capabilities as a Model Context Protocol (MCP) server.
Compatible with Cursor, Claude Desktop, and other MCP clients.

Architecture:
- Standalone server with direct service integration (no HTTP proxy)
- Uses core/rag_service.py directly for RAG operations
- LangFuse integration for observability tracing (graceful degradation if unavailable)
- Cost tracking via langfuse.openai wrapper in embedder (automatic token/cost calculation)
- Prometheus metrics for performance monitoring (/metrics endpoint)
- Health check endpoint (/health) for service status monitoring
"""
```

### 3.2 Function Docstrings

**Formato standardizzato:**

- Breve descrizione (prima riga)
- Sezione `Args:` per parametri
- Sezione `Returns:` per valore di ritorno
- Sezione `Yields:` per generatori
- Sezione `Raises:` per eccezioni
- Sezione `Note:` per informazioni aggiuntive

**Esempio:**

```python
async def langfuse_span(
    name: str,
    span_type: str = "span",
    metadata: dict = None
) -> AsyncGenerator[Any, None]:
    """
    Create a nested LangFuse span for cost tracking and timing breakdown.

    Args:
        name: Name of the span (e.g., "embedding-generation", "vector-search")
        span_type: Type of span ("span" for general, "generation" for LLM calls)
        metadata: Optional metadata to attach to the span

    Yields:
        A dict with 'span' (LangFuse span or None) and 'start_time' for timing.

    Note:
        - Gracefully degrades to no-op if LangFuse unavailable
        - Always records timing in span metadata (duration_ms)
        - Also records to Prometheus metrics for embedding and db_search spans
    """
    pass
```

### 3.3 Class Docstrings

**Formato:**

- Descrizione della classe
- Sezione `Attributes:` per attributi pubblici importanti
- Sezione `Example:` se utile

**Esempio:**

```python
class EmbeddingGenerator(BaseEmbedder):
    """
    Generates embeddings using OpenAI compatible API.

    Cost Tracking:
        Uses langfuse.openai wrapper when available for automatic cost tracking.
        Falls back to direct OpenAI client if LangFuse unavailable.

    Attributes:
        model_name: OpenAI model name (default: "text-embedding-3-small")
        batch_size: Batch size for embedding generation (default: 100)
        use_cache: Enable in-memory cache for embeddings (default: True)
    """
    pass
```

### 3.4 Inline Comments

**Quando usare:**

- Spiegare "perché" non "cosa" (il codice dovrebbe essere auto-esplicativo)
- Sezioni complesse o ottimizzazioni non ovvie
- Workaround o limitazioni note

**Esempio:**

```python
# OPTIMIZED: Runs in background to prevent blocking server startup (MCP handshake timeout)
async def initialize_global_embedder():
    """Initialize global embedder instance at server startup."""
    # Offload heavy import and creation to thread to avoid blocking asyncio loop
    # This is critical because importing transformers/docling takes ~40s
    _global_embedder = await asyncio.to_thread(_create_embedder_sync)
```

---

## 4. Error Handling

### 4.1 Graceful Degradation

**Pattern obbligatorio per dipendenze opzionali:**

- Try/except per import
- Fallback a implementazione no-op o alternativa
- Logging informativo

**Esempio:**

```python
# LangFuse integration with graceful degradation
try:
    from langfuse import observe, get_client as get_langfuse_client
    _langfuse_available = True
except ImportError:
    _langfuse_available = False
    get_langfuse_client = None
    # Create no-op decorator as fallback
    def observe(name=None, **kwargs):
        def decorator(func):
            return func
        return decorator
    logger.info("LangFuse SDK not installed, tracing disabled")
```

### 4.2 Exception Handling

**Best Practices:**

- Catturare eccezioni specifiche quando possibile
- Logging con contesto (error message, stack trace se necessario)
- Re-raise dopo logging se necessario
- Usare `ToolError` per errori user-facing in MCP tools

**Esempio:**

```python
from fastmcp import ToolError

async def query_knowledge_base(query: str, limit: int = 5) -> str:
    """Query knowledge base with error handling."""
    try:
        results = await search_knowledge_base_structured(query, limit)
        return format_results(results)
    except ValueError as e:
        logger.error(f"Invalid query parameters: {e}")
        raise ToolError(f"Invalid query: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in query_knowledge_base: {e}", exc_info=True)
        raise ToolError("An error occurred while querying the knowledge base")
```

### 4.3 Retry Logic

**Quando usare:**

- Operazioni di rete (API calls, DB connections)
- Operazioni transient che possono fallire temporaneamente

**Pattern:**

- Usare `tenacity` per retry con exponential backoff
- Configurare max tentativi e delay appropriati

**Esempio:**

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def generate_embedding(text: str) -> List[float]:
    """Generate embedding with retry logic for transient errors."""
    try:
        response = await client.embeddings.create(
            model=self.model_name,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.warning(f"Embedding generation failed (will retry): {e}")
        raise
```

---

## 5. Logging

### 5.1 Logger Setup

**Pattern standard:**

- Un logger per modulo con `__name__`
- Configurazione centralizzata (non per-modulo)

**Esempio:**

```python
import logging

logger = logging.getLogger(__name__)

# Non configurare logging qui - viene fatto a livello applicazione
# logging.basicConfig(level=logging.INFO)  # ❌ Non fare questo
```

### 5.2 Log Levels

**DEBUG:**

- Informazioni dettagliate per debugging
- Non usare in produzione

**INFO:**

- Eventi significativi dell'applicazione (startup, shutdown, operazioni principali)
- Metriche importanti

**WARNING:**

- Situazioni anomale ma non critiche
- Fallback a funzionalità alternative

**ERROR:**

- Errori che impediscono un'operazione ma non crashano l'applicazione
- Include stack trace quando utile

**CRITICAL:**

- Errori critici che possono causare crash
- Raramente usato

**Esempio:**

```python
logger.debug(f"Processing query: {query[:50]}...")  # Debug info
logger.info("Global embedder initialized successfully")  # Significant event
logger.warning("LangFuse unavailable, continuing without tracing")  # Degradation
logger.error(f"Database connection failed: {e}", exc_info=True)  # Error with context
```

### 5.3 Structured Logging

**Quando possibile:**

- Usare formattazione strutturata per parsing automatico
- Includere contesto rilevante (request_id, tool_name, etc.)

**Esempio:**

```python
logger.info(
    "MCP request completed",
    extra={
        "tool_name": "query_knowledge_base",
        "duration_ms": duration_ms,
        "status": "success",
        "results_count": len(results)
    }
)
```

---

## 6. Async/Await Patterns

### 6.1 Async Functions

**Quando usare async:**

- Operazioni I/O (database, API calls, file operations)
- Operazioni che possono essere bloccanti

**Quando NON usare async:**

- Operazioni CPU-bound pure
- Calcoli matematici semplici

**Esempio:**

```python
# ✅ Corretto - I/O operation
async def search_knowledge_base(query: str) -> List[Dict]:
    async with db_pool.acquire() as conn:
        results = await conn.fetch(query)
    return results

# ❌ Errato - CPU-bound operation
async def calculate_embedding_similarity(emb1: List[float], emb2: List[float]) -> float:
    # Non serve async per operazioni CPU-bound
    return cosine_similarity(emb1, emb2)
```

### 6.2 Context Managers

**Per risorse che richiedono cleanup:**

- Database connections
- File handles
- LangFuse spans

**Esempio:**

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def langfuse_span(name: str) -> AsyncGenerator[Any, None]:
    """Create LangFuse span with automatic cleanup."""
    span = create_span(name)
    try:
        yield span
    finally:
        span.end()

# Usage
async with langfuse_span("embedding-generation") as span:
    embedding = await generate_embedding(query)
    span.update(metadata={"tokens": len(query.split())})
```

### 6.3 Background Tasks

**Per operazioni pesanti che non devono bloccare startup:**

- Inizializzazione modelli pesanti
- Pre-warming cache

**Esempio:**

```python
async def initialize_global_embedder():
    """Initialize embedder in background to avoid blocking startup."""
    global _initialization_task

    async def _init_task():
        global _global_embedder
        # Heavy operation offloaded to thread
        _global_embedder = await asyncio.to_thread(_create_embedder_sync)
        _embedder_ready.set()

    # Start background task
    _initialization_task = asyncio.create_task(_init_task())
```

---

## 7. Testing Standards

### 7.1 Test Organization

**Struttura directory:**

```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Unit tests (>70% coverage)
│   ├── test_rag_service.py
│   └── test_embedder.py
├── integration/         # Integration tests
│   ├── test_mcp_server.py
│   └── test_observability_endpoints.py
├── e2e/                # End-to-end tests
│   └── test_streamlit_workflow.py
└── fixtures/           # Test fixtures + golden dataset
    └── golden_dataset.json
```

### 7.2 Test Naming

**File:**

- `test_*.py` o `*_test.py`

**Funzioni:**

- `test_<functionality>_<condition>_<expected_result>`
- Usare nomi descrittivi

**Esempio:**

```python
# ✅ Corretto
def test_query_knowledge_base_with_valid_query_returns_results():
    pass

def test_query_knowledge_base_with_empty_query_raises_error():
    pass

# ❌ Errato
def test_query():
    pass
```

### 7.3 Test Structure

**Pattern AAA (Arrange-Act-Assert):**

- Arrange: Setup test data
- Act: Execute function under test
- Assert: Verify results

**Esempio:**

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_search_knowledge_base_returns_formatted_results():
    # Arrange
    query = "test query"
    limit = 5
    mock_results = [
        {"content": "result 1", "source": "doc1"},
        {"content": "result 2", "source": "doc2"}
    ]

    with patch('core.rag_service.search_knowledge_base_structured') as mock_search:
        mock_search.return_value = mock_results

        # Act
        result = await query_knowledge_base(query, limit)

        # Assert
        assert "result 1" in result
        assert "doc1" in result
        mock_search.assert_called_once_with(query, limit)
```

### 7.4 Coverage Requirements

**Minimo:**

- 70% coverage per moduli core
- 80% coverage per moduli critici (observability, error handling)

**Verifica:**

```bash
pytest --cov=core --cov=docling_mcp --cov-report=term-missing
```

---

## 8. Observability Patterns

### 8.1 LangFuse Integration

**Pattern decorator:**

- Usare `@observe()` per funzioni critiche
- Nested spans per operazioni child

**Esempio:**

```python
from langfuse import observe

@observe(name="query_knowledge_base")
async def query_knowledge_base(query: str, limit: int = 5) -> str:
    """Query knowledge base with LangFuse tracing."""
    # Nested span per embedding
    async with langfuse_span("embedding-generation") as span_ctx:
        embedding = await generate_query_embedding(query)
        span_ctx["span"].update(metadata={"tokens": len(query.split())})

    # Nested span per DB search
    async with langfuse_span("vector-search") as span_ctx:
        results = await search_with_embedding(embedding, limit)
        span_ctx["span"].update(metadata={"results_count": len(results)})

    return format_results(results)
```

### 8.2 Prometheus Metrics

**Pattern:**

- Inizializzazione lazy con graceful degradation
- Recording functions per metriche

**Esempio:**

```python
from docling_mcp.metrics import record_request_start, record_request_end

@mcp.tool()
async def query_knowledge_base(query: str, limit: int = 5) -> str:
    """Query knowledge base with Prometheus metrics."""
    tool_name = "query_knowledge_base"
    start_time = record_request_start(tool_name)
    status = "success"

    try:
        results = await search_knowledge_base_structured(query, limit)
        return format_results(results)
    except Exception as e:
        status = "error"
        raise
    finally:
        record_request_end(tool_name, start_time, status)
```

### 8.3 Health Checks

**Pattern:**

- Status logic chiaro (ok/degraded/down)
- Service checks individuali
- Timing information

**Esempio:**

```python
@dataclass
class HealthResponse:
    status: Literal["ok", "degraded", "down"]
    timestamp: float
    services: Dict[str, Dict[str, Any]]

async def check_health() -> HealthResponse:
    """Check system health with service status."""
    db_status = await check_database()
    langfuse_status = await check_langfuse()
    embedder_status = await check_embedder()

    # Determine overall status
    if db_status.status == "down":
        overall_status = "down"
    elif langfuse_status.status == "down":
        overall_status = "degraded"  # LangFuse optional
    else:
        overall_status = "ok"

    return HealthResponse(
        status=overall_status,
        timestamp=time.time(),
        services={
            "database": asdict(db_status),
            "langfuse": asdict(langfuse_status),
            "embedder": asdict(embedder_status)
        }
    )
```

---

## 9. Code Organization

### 9.1 Module Structure

**Ordine standard:**

1. Module docstring
2. Imports (standard, third-party, local)
3. Constants
4. Global variables (con prefisso `_` se privati)
5. Classes
6. Functions
7. Module-level code (se necessario)

**Esempio:**

```python
"""
Module description.
"""

# Standard library
import logging
from typing import List, Optional

# Third-party
from fastmcp import FastMCP

# Local
from core.rag_service import search_knowledge_base_structured

# Constants
DEFAULT_LIMIT = 5
MAX_RETRIES = 3

# Global variables
logger = logging.getLogger(__name__)
_global_state = None

# Classes
class ServiceClass:
    pass

# Functions
async def public_function():
    pass

def _private_function():
    pass
```

### 9.2 Separation of Concerns

**Principi:**

- Business logic separata da I/O (es. `core/rag_service.py` decoupled)
- Observability separata da business logic (decorators, metrics)
- Configuration separata da implementation

**Esempio:**

```python
# ✅ Corretto - Business logic separata
# core/rag_service.py
async def search_knowledge_base_structured(query: str, limit: int) -> List[Dict]:
    """Pure business logic, no I/O concerns."""
    pass

# docling_mcp/server.py - I/O layer
@mcp.tool()
@observe(name="query_knowledge_base")
async def query_knowledge_base(query: str, limit: int = 5) -> str:
    """MCP tool with observability, calls business logic."""
    results = await search_knowledge_base_structured(query, limit)
    return format_results(results)

# ❌ Errato - Business logic mescolata con I/O
async def query_knowledge_base(query: str, limit: int = 5) -> str:
    # Business logic
    embedding = await generate_embedding(query)
    # I/O operations
    async with db_pool.acquire() as conn:
        results = await conn.fetch(...)
    # Formatting
    return format_results(results)
```

---

## 10. Performance Considerations

### 10.1 Resource Management

**Connection Pools:**

- Inizializzare una volta, riutilizzare
- Configurare size appropriato (min/max)

**Esempio:**

```python
# ✅ Corretto - Global pool
db_pool = DatabasePool()
await db_pool.initialize()  # Once at startup

async def search_db(query: str):
    async with db_pool.acquire() as conn:
        return await conn.fetch(query)

# ❌ Errato - New connection per query
async def search_db(query: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetch(query)
    finally:
        await conn.close()
```

### 10.2 Caching

**Quando usare:**

- Operazioni costose ripetute (embedding generation)
- Dati che cambiano raramente

**Pattern:**

- LRU cache con size limitato
- Cache key basata su input

**Esempio:**

```python
class EmbeddingCache:
    """Simple in-memory cache for embeddings."""
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, List[float]] = {}
        self.max_size = max_size

    def get(self, text: str) -> Optional[List[float]]:
        return self.cache.get(text)

    def set(self, text: str, embedding: List[float]):
        if len(self.cache) >= self.max_size:
            # Simple eviction: remove first key (FIFO-ish)
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        self.cache[text] = embedding
```

### 10.3 Background Initialization

**Per operazioni pesanti:**

- Non bloccare startup
- Pre-warm risorse

**Esempio:**

```python
# Initialize in background to avoid blocking MCP handshake
_initialization_task = asyncio.create_task(initialize_global_embedder())

# Check readiness before use
if not _embedder_ready.is_set():
    await _embedder_ready.wait()
```

---

## 11. Security Best Practices

### 11.1 Secrets Management

**Pattern:**

- Environment variables per secrets
- Mai hardcode secrets nel codice
- Usare `.env` file per sviluppo locale

**Esempio:**

```python
import os
from dotenv import load_dotenv

load_dotenv()

# ✅ Corretto
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

# ❌ Errato
api_key = "sk-..."  # Never hardcode secrets
```

### 11.2 Input Validation

**Pattern:**

- Validare input all'ingresso
- Usare Pydantic models quando possibile
- Sanitizzare user input

**Esempio:**

```python
from pydantic import BaseModel, Field, validator

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=100)

    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()
```

### 11.3 Error Messages

**Pattern:**

- Non esporre informazioni sensibili in errori user-facing
- Log dettagli completi, messaggi user-friendly

**Esempio:**

```python
try:
    result = await process_request(request)
except DatabaseError as e:
    # Log completo per debugging
    logger.error(f"Database error: {e}", exc_info=True)
    # Messaggio user-friendly
    raise ToolError("An error occurred processing your request")
```

---

## 12. Configuration Management

### 12.1 Environment Variables

**Pattern:**

- Usare `python-dotenv` per sviluppo
- Validare variabili richieste all'avvio
- Fornire valori di default quando appropriato

**Esempio:**

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Required variables
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable required")

# Optional variables with defaults
METRICS_PORT = int(os.getenv("METRICS_PORT", "8080"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

### 12.2 Configuration Classes

**Pattern:**

- Usare dataclasses o Pydantic models per config
- Validazione automatica
- Type hints completi

**Esempio:**

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    database_url: str = ""
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None

    def __post_init__(self):
        if not self.database_url:
            raise ValueError("database_url is required")
```

---

## 13. Code Review Checklist

Prima di sottomettere codice per review, verificare:

- [ ] Type hints completi per funzioni pubbliche
- [ ] Docstrings con formato standardizzato
- [ ] Error handling appropriato (graceful degradation se necessario)
- [ ] Logging con livelli corretti
- [ ] Test aggiunti/modificati per nuove funzionalità
- [ ] Coverage mantenuto sopra 70%
- [ ] Nessun secret hardcoded
- [ ] Input validation dove necessario
- [ ] Performance considerations (caching, pooling) se applicabile
- [ ] Observability integrata (LangFuse, Prometheus) per operazioni critiche

---

## 14. Tools and Linting

### 14.1 Ruff

**Configurazione in `pyproject.toml`:**

```toml
[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line too long (handled by formatter)
```

**Uso:**

```bash
ruff check .
ruff check --fix .
```

### 14.2 MyPy

**Configurazione:**

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
```

**Uso:**

```bash
mypy core/ docling_mcp/
```

### 14.3 Black (Optional)

**Configurazione:**

```toml
[tool.black]
line-length = 100
target-version = ["py310", "py311"]
```

**Uso:**

```bash
black .
```

---

## 15. References

### Internal Documentation

- **[Architecture](./architecture.md)**: System architecture, design decisions, and integration patterns
- **[Unified Project Structure](./unified-project-structure.md)**: Standardized directory structure and file organization rules
- **[Testing Strategy](./testing-strategy.md)**: Complete testing strategy with TDD workflow and test organization
- **[Development Guide](./development-guide.md)**: Setup instructions and development workflow
- **[Epic Breakdown](./epics.md)**: Complete epic and story breakdown
- **[Tech Specs](./stories/*/tech-spec-epic-*.md)**: Technical specifications for each epic

### External References

- **Python Style Guide**: PEP 8 (https://pep8.org/)
- **Type Hints**: PEP 484 (https://peps.python.org/pep-0484/)
- **Async/Await**: PEP 492 (https://peps.python.org/pep-0492/)
- **Ruff Documentation**: https://docs.astral.sh/ruff/
- **MyPy Documentation**: https://mypy.readthedocs.io/
- **Black Documentation**: https://black.readthedocs.io/

---

## Changelog

- **2025-01-27**: Initial version based on existing codebase patterns
