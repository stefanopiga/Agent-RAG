# API & Services Analysis

## Core Services

### RAG Service (`core/rag_service.py`)

**Servizio principale per ricerca semantica nella knowledge base**

**Funzioni:**

- `search_knowledge_base(query, limit, source_filter)` - Ricerca semantica con filtering opzionale

**Caratteristiche:**

- Vector search usando PGVector (cosine similarity)
- Embedding generation via OpenAI
- Source filtering (ILIKE pattern matching)
- Connection pooling con AsyncPG
- Error handling e logging

**Query SQL:**

```sql
SELECT c.content, d.title, d.source,
       1 - (c.embedding <=> $1::vector) AS similarity
FROM chunks c
JOIN documents d ON c.document_id = d.id
WHERE c.embedding IS NOT NULL
  AND d.source ILIKE $3  -- Optional filter
ORDER BY c.embedding <=> $1::vector
LIMIT $2
```

### PydanticAI Agent (`core/agent.py`)

**Wrapper agent che espone RAG service come tool**

**Tool registrato:**

- `search_knowledge_base` - Delega a core service

**System Prompt:**

- Assistente con accesso knowledge base
- Deve queryare KB prima di rispondere
- Supporto filtering per fonte specifica
- Source attribution obbligatoria

**Database Management:**

- `initialize_db()` - Setup connection pool
- `close_db()` - Cleanup connections

## Pattern Architetturale

- **Separation of Concerns:** Core logic decoupled da agent framework
- **Service Layer:** `rag_service.py` può essere usato standalone
- **Agent Layer:** `agent.py` wraps service per PydanticAI
- **Riutilizzabilità:** Core service usato da MCP server

## Integration Points

- **Streamlit UI** → `core.agent` (PydanticAI)
- **MCP Server** → `core.rag_service` (diretto)
- **Database** → `utils.db_utils` (connection pool)
- **Embeddings** → `ingestion.embedder`

---

# Ingestion Pipeline Analysis

## Document Ingestion (`ingestion/ingest.py`)

**Pipeline completa per processamento documenti**

### DocumentIngestionPipeline

**Classe principale per ingestione documenti nella knowledge base**

**Features:**

- Multi-format support via Docling (PDF, Office, HTML, audio)
- Batch processing con progress tracking
- Database cleanup automatico (default: cancella prima di ingerire)
- Error handling robusto per file

**Formati supportati:**

- Text: `.md`, `.markdown`, `.txt`
- PDF: `.pdf`
- Office: `.docx`, `.doc`, `.pptx`, `.ppt`, `.xlsx`, `.xls`
- Web: `.html`, `.htm`

**Workflow Pipeline:**

1. Clean database (opzionale, default ON)
2. Find documents (recursive scan con glob patterns)
3. Per ogni documento:
   - Leggi contenuto (Docling converter o raw text)
   - Estrai metadata (YAML frontmatter, file info)
   - Chunk document (HybridChunker)
   - Genera embeddings (batch processing)
   - Salva a PostgreSQL (transaction)
4. Log summary (chunks, errori, tempo)

**CLI Arguments:**

- `--documents`: Cartella documenti (default: "documents")
- `--no-clean`: Skip cleanup DB (default: clean automatico)
- `--chunk-size`: Dimensione chunk (default: 1000)
- `--chunk-overlap`: Overlap (default: 200)
- `--no-semantic`: Disable semantic chunking
- `--verbose`: Debug logging

## Embedding Generation (`ingestion/embedder.py`)

**Generazione embeddings OpenAI con batching e caching**

### EmbeddingGenerator

**Genera embeddings vettoriali per chunk e query**

**Caratteristiche:**

- Batch processing (100 texts per batch)
- Retry logic con exponential backoff
- Rate limit handling
- Fallback individuale su batch failure
- Model-specific configs (dimensions, max_tokens)

**Modelli supportati:**

- `text-embedding-3-small` (1536 dim, 8191 tokens)
- `text-embedding-3-large` (3072 dim, 8191 tokens)
- `text-embedding-ada-002` (1536 dim, 8191 tokens)

**API Methods:**

- `generate_embedding(text)` - Embedding singolo
- `generate_embeddings_batch(texts)` - Batch embeddings
- `embed_chunks(chunks)` - Process DocumentChunks
- `embed_query(query)` - Embedding per search query

**Caching:**

- In-memory cache (LRU, max 1000 entries)
- Hash-based lookup (MD5)
- Access time tracking

## Document Chunking (`ingestion/chunker.py`)

**Intelligent document splitting con Docling HybridChunker**

### DoclingHybridChunker

**Token-aware semantic chunking (RACCOMANDATO)**

**Vantaggi:**

- Token-precise (usa tokenizer reale, non stima caratteri)
- Structure-preserving (rispetta heading, section, table)
- Contextualized (chunk include gerarchia heading)
- Fast (no LLM calls)
- Battle-tested (Docling team)

**Funzionamento:**

1. Tokenizer init (`sentence-transformers/all-MiniLM-L6-v2`)
2. HybridChunker con `max_tokens=512`
3. Chunk DoclingDocument
4. Contextualize each chunk (add heading hierarchy)
5. Token count preciso
6. Metadata arricchito

**Output:**

```python
DocumentChunk(
    content="# Section\n\nContext text...",
    index=0,
    token_count=245,  # Actual tokens
    metadata={"has_context": True, ...}
)
```

### SimpleChunker

**Fallback chunker senza Docling (paragraph-based)**

**Quando usato:**

- DoclingDocument non disponibile
- HybridChunker fallisce
- Speed priorità su precision

**Strategia:**

- Split su doppio newline (paragrafi)
- Sliding window con overlap
- Sentence boundary respect
- Character-based (stima token)

## ChunkingConfig

**Configurazione chunking strategy**

```python
ChunkingConfig(
    chunk_size=1000,           # Target chars
    chunk_overlap=200,          # Overlap chars
    max_chunk_size=2000,        # Max chars
    min_chunk_size=100,         # Min chars
    use_semantic_splitting=True, # HybridChunker ON
    preserve_structure=True,    # Keep doc structure
    max_tokens=512              # Embedding model limit
)
```

## Data Flow

```
Document File
    ↓
Docling Converter → DoclingDocument
    ↓
HybridChunker → List[DocumentChunk]
    ↓
EmbeddingGenerator → Chunks with embeddings
    ↓
PostgreSQL (documents + chunks tables)
```

---

# Utilities Analysis

## Database Utilities (`utils/db_utils.py`)

**Connection pooling e operazioni database**

### DatabasePool

**Gestione connection pool AsyncPG per PostgreSQL**

**Configurazione Pool:**

```python
asyncpg.create_pool(
    DATABASE_URL,
    min_size=5,              # Min connessioni attive
    max_size=20,             # Max connessioni
    max_inactive_lifetime=300, # Cleanup idle dopo 5min
    command_timeout=60,       # Timeout query
    statement_cache_size=0    # Disable per pgbouncer
)
```

**API Methods:**

- `initialize()` - Setup connection pool
- `close()` - Chiudi pool
- `acquire()` - Context manager per connessione
- `get_document(id)` - Fetch documento per ID
- `list_documents(limit, offset, filter)` - Lista documenti
- `execute_query(sql, params)` - Query custom
- `test_connection()` - Health check

**Global Instance:**

```python
db_pool = DatabasePool()  # Singleton globale
```

**Usage Pattern:**

```python
async with db_pool.acquire() as conn:
    result = await conn.fetch(query, *params)
```

## Data Models (`utils/models.py`)

**Pydantic models per validazione e serializzazione**

### Request/Response Models

**API contracts per endpoints**

**SearchRequest:**

```python
SearchRequest(
    query: str,
    search_type: SearchType = SEMANTIC,
    limit: int = 10,
    filters: Dict[str, Any] = {}
)
```

**ChunkResult:**

```python
ChunkResult(
    chunk_id: str,
    document_id: str,
    content: str,
    score: float,  # 0.0-1.0 normalized
    document_title: str,
    document_source: str,
    metadata: Dict
)
```

**SearchResponse:**

```python
SearchResponse(
    results: List[ChunkResult],
    total_results: int,
    search_type: SearchType,
    query_time_ms: float
)
```

### Database Models

**Schema-mapped models per PostgreSQL**

**Document:**

```python
Document(
    id: Optional[str],
    title: str,
    source: str,
    content: str,
    metadata: Dict,
    created_at: datetime,
    updated_at: datetime
)
```

**Chunk:**

```python
Chunk(
    id: Optional[str],
    document_id: str,
    content: str,
    embedding: Optional[List[float]],  # 1536 dims
    chunk_index: int,
    metadata: Dict,
    token_count: Optional[int]
)
```

**Validation:**

- Embedding dimension check (1536)
- Score normalization (0-1 range)
- Chunk overlap validation

### Ingestion Models

**Configuration per document processing**

**IngestionConfig:**

```python
IngestionConfig(
    chunk_size: int = 1000,        # 100-5000 range
    chunk_overlap: int = 200,       # Must be < chunk_size
    max_chunk_size: int = 2000,     # 500-10000 range
    use_semantic_chunking: bool = True
)
```

**IngestionResult:**

```python
IngestionResult(
    document_id: str,
    title: str,
    chunks_created: int,
    processing_time_ms: float,
    errors: List[str]
)
```

### Agent Models

**PydanticAI agent context**

**AgentContext:**

```python
AgentContext(
    session_id: str,
    messages: List[Message],
    tool_calls: List[ToolCall],
    search_results: List[ChunkResult],
    metadata: Dict
)
```

## Provider Configuration (`utils/providers.py`)

**OpenAI model configuration centralized**

**Functions:**

- `get_llm_model()` - PydanticAI OpenAIModel per agent
- `get_embedding_client()` - AsyncOpenAI client per embeddings
- `get_embedding_model()` - Nome modello embedding
- `validate_configuration()` - Check env vars
- `get_model_info()` - Config info dict

**Environment Variables:**

- `OPENAI_API_KEY` (required)
- `LLM_CHOICE` (default: gpt-4o-mini)
- `EMBEDDING_MODEL` (default: text-embedding-3-small)
- `DATABASE_URL` (required)

**Model Info:**

```python
{
    "llm_provider": "openai",
    "llm_model": "gpt-4o-mini",
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small"
}
```

---

# Database Schema Analysis (`sql/`)

## PostgreSQL Schema (`sql/schema.sql`)

**Schema completo con PGVector per vector similarity search**

### Extensions Required

```sql
CREATE EXTENSION IF NOT EXISTS vector;       -- PGVector per embeddings
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- UUID generation
```

### Table: documents

**Memorizza documenti originali con metadata**

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    source TEXT NOT NULL,              -- Percorso relativo file
    content TEXT NOT NULL,              -- Contenuto completo
    metadata JSONB DEFAULT '{}',        -- Metadata flessibile
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**

- `idx_documents_metadata` - GIN index per query JSONB
- `idx_documents_created_at` - Index su timestamp (DESC order)

**Trigger:**

- `update_documents_updated_at` - Auto-update `updated_at` on UPDATE

### Table: chunks

**Memorizza chunk di testo con vector embeddings**

```sql
CREATE TABLE chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),             -- OpenAI embedding (1536 dims)
    chunk_index INTEGER NOT NULL,       -- Position in document
    metadata JSONB DEFAULT '{}',
    token_count INTEGER,                -- Actual token count
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**

- `idx_chunks_embedding` - IVFFlat index per vector similarity (cosine distance)
  - `USING ivfflat (embedding vector_cosine_ops) WITH (lists = 1)`
- `idx_chunks_document_id` - FK index per JOIN performance
- `idx_chunks_chunk_index` - Composite index (document_id, chunk_index)

**Foreign Key:**

- `document_id` → `documents(id)` ON DELETE CASCADE

### Table: sessions (Epic 3)

**Memorizza statistiche sessione Streamlit per observability**

```sql
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    query_count INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0.0,
    total_latency_ms DECIMAL(10, 2) DEFAULT 0.0
);
```

**Indexes:**

- `idx_sessions_last_activity` - B-tree index per session activity tracking

**RLS:**

- RLS enabled con policy `service_role` only (backend access)

### Table: query_logs (Epic 3)

**Memorizza log query per sessione con costi e timing**

```sql
CREATE TABLE query_logs (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    response_text TEXT,
    cost DECIMAL(10, 6) NOT NULL,
    latency_ms DECIMAL(10, 2) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    langfuse_trace_id VARCHAR(255)
);
```

**Indexes:**

- `idx_query_logs_session_id` - B-tree index per session query lookups
- `idx_query_logs_timestamp` - B-tree index per time-based queries

**Foreign Key:**

- `session_id` → `sessions(session_id)` ON DELETE CASCADE

**RLS:**

- RLS enabled con policy `service_role` only (backend access)

### Function: match_chunks

**Vector similarity search con cosine distance**

```sql
CREATE FUNCTION match_chunks(
    query_embedding vector(1536),
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    similarity FLOAT,               -- 0.0 (dissimilar) to 1.0 (identical)
    metadata JSONB,
    document_title TEXT,
    document_source TEXT
)
```

**Logic:**

- Calcola similarity: `1 - (embedding <=> query_embedding)`
- Operator `<=>`: Cosine distance (PGVector)
- JOIN con documents per metadata
- ORDER BY distance ASC
- LIMIT per performance

**Usage:**

```sql
SELECT * FROM match_chunks(
    '[0.1, 0.2, ..., 0.5]'::vector(1536),  -- Query embedding
    5                                       -- Top 5 results
);
```

### Similarity Score Interpretation

- **1.0** - Identico
- **0.9-1.0** - Molto rilevante
- **0.7-0.9** - Rilevante
- **0.5-0.7** - Parzialmente rilevante
- **< 0.5** - Poco rilevante

## Cleanup Script (`sql/removeDocuments.sql`)

**Reset knowledge base preservando schema**

**Operations:**

```sql
DELETE FROM chunks;      -- Remove tutti i chunks
DELETE FROM documents;   -- Remove tutti i documenti
```

**Post-cleanup (opzionale):**

```sql
VACUUM ANALYZE chunks;      -- Reclaim space
VACUUM ANALYZE documents;   -- Update statistics
```

**Verification Query:**

```sql
SELECT 'Documents remaining:', COUNT(*) FROM documents
UNION ALL
SELECT 'Chunks remaining:', COUNT(*) FROM chunks;
```

**Use Cases:**

- Reset knowledge base prima re-ingestion
- Clean test data
- Prepare for fresh document set

**Schema preservato:**

- Tables
- Indexes
- Functions
- Triggers

## Database Architecture Summary

### Storage Strategy

- **Documents**: Full text storage con JSONB metadata
- **Chunks**: Text fragments con 1536-dim vector embeddings
- **Relationships**: 1-to-many (document → chunks) con CASCADE delete

### Index Strategy

- **Vector Search**: IVFFlat index per fast approximate NN search
- **Metadata**: GIN index per flexible JSONB queries
- **Foreign Keys**: B-tree indexes per JOIN performance
- **Temporal**: Index su created_at per chronological queries

### Query Patterns

1. **Vector Search**: match_chunks() per semantic similarity
2. **Metadata Filtering**: JSONB containment (@>) per source filtering
3. **Document Retrieval**: JOIN chunks+documents per full context
4. **Batch Operations**: CASCADE delete per data consistency
