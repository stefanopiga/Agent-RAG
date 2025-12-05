# Changelog - docling-rag-agent

## [2.1.0] - 2025-12-05

### Changed

- **Dockerfile Optimization (Story 6-2)**
  - Renamed `Dockerfile` → `Dockerfile.streamlit` for naming consistency
  - Converted to multi-stage build (builder + runtime stages)
  - Replaced `COPY . .` with explicit COPY commands for minimal images
  - Added non-root user for security
  - Updated docker-compose.yml to reference new Dockerfile name

- **Project Structure Validation**
  - Added `mcp_server.py` and `prometheus.yml` to authorized root files
  - Updated validation script to accept new file naming convention
  - All validation scripts pass (structure + imports)

- **Documentation Updates**
  - Updated `docs/unified-project-structure.md` with current file list
  - Updated `docs/architecture.md` Project Structure section
  - Updated `.github/workflows/ci.yml` to use `Dockerfile.streamlit`
  - Updated `.github/workflows/README.md` with correct Dockerfile references

- **Docker Ignore Improvements**
  - Added `.bmad/`, `.agent/`, `.cursor/`, `.vscode/` to exclusions
  - Added `sql/`, `prometheus.yml`, `metrics` to exclusions
  - Ensures Docker images contain only runtime-required files

## [2.0.0] - 2025-11-24

### 🚀 Major Performance Optimizations

**Summary:** 61-76% latency reduction achieved through comprehensive optimization of MCP server, database indexes, and caching strategy.

### Added

- **MCP Server** (`mcp_server.py`)
  - FastMCP-based Model Context Protocol server for Cursor IDE integration
  - Global embedder instance with persistent caching
  - Lifecycle management with proper startup/shutdown
  - Detailed performance timing instrumentation
  
- **Optimization Tools**
  - `scripts/optimize_database.py` - Automated database index management
  - `scripts/test_mcp_performance.py` - Comprehensive performance test suite
  
- **Documentation**
  - `docs/performance-optimization-guide.md` - Complete technical guide
  - `docs/optimization-summary.md` - Performance analysis and results
  - `docs/optimization-deployment.md` - Deployment guide
  - `CHANGELOG.md` - This file

- **SQL Schema**
  - `sql/optimize_index.sql` - Complete optimized schema with HNSW index
  - Includes fresh install and upgrade paths
  - Diagnostic queries and verification

### Changed

- **Database Index: IVFFlat → HNSW** 
  - Upgraded from `IVFFlat (lists=1)` to optimized HNSW index
  - 10-100x faster vector similarity searches
  - Performance impact: -50-80% query latency
  - Consistent performance regardless of dataset size

- **Embedder Architecture**
  - Refactored to global singleton pattern
  - Persistent cache across requests (was per-request)
  - Eliminated 300-500ms overhead per query
  - Enhanced cache from 1000 to 2000 entries

- **Connection Pool Configuration** (`utils/db_utils.py`)
  - `min_size`: 5 → 2 (reduced idle overhead)
  - `max_size`: 20 → 10 (right-sized for MCP workload)
  - `statement_cache_size`: 0 → 100 (enabled prepared statements)
  - Added connection recycling (`max_queries=50000`)

- **Core RAG Service** (`core/rag_service.py`)
  - Added global embedder management functions
  - Implemented timing breakdown instrumentation
  - Enhanced error logging with performance metrics
  - Decoupled from PydanticAI for reusability

- **README.md**
  - Updated database setup instructions
  - Added MCP server configuration section
  - Added performance optimization section with metrics
  - Updated project structure to reflect new architecture

### Removed

- **`sql/schema.sql`** - Obsolete (replaced by `optimize_index.sql`)
  - Old file used inefficient IVFFlat index (lists=1)
  - New file includes complete schema + optimized HNSW index
  - Provides both fresh install and upgrade paths

### Performance Improvements

**Metrics (Dataset: 6,260 chunks, 410 documents):**

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Average Query Latency | 3563ms | **1395ms** | **-61%** |
| Max Query Latency | 8613ms | **2097ms** | **-76%** |
| Cached Query | 298ms | **237ms** | **-20%** |
| DB Vector Search | 100-300ms | **20-60ms** | **-75%** |
| Cache Hit Rate | 63.5% | **66.4%** | +3% |

**Component Breakdown:**

- **OpenAI Embedding API**: 500-800ms (external, unavoidable)
- **DB Vector Search (HNSW)**: 20-60ms (was 100-300ms)
- **Embedder Overhead**: <1ms (was 300-500ms)
- **Connection Pool**: 5-15ms (was 10-50ms)

**Total End-to-End:** 670-1150ms (was 1500-3000ms)

### Technical Details

**HNSW Index Configuration:**
```sql
CREATE INDEX idx_chunks_embedding_hnsw ON chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

- `m=16`: Balanced connectivity (16 connections per layer)
- `ef_construction=64`: Build quality parameter
- Query-time `ef_search=40` (default, good balance)

**Global Embedder:**
```python
# Initialized once at server startup
_global_embedder = create_embedder(use_cache=True, batch_size=100)

# Reused across all requests
embedder = get_global_embedder()  # <1ms
```

### Migration Guide

**For existing installations:**

1. **Backup database** (recommended but optional)
   ```bash
   pg_dump $DATABASE_URL > backup.sql
   ```

2. **Apply index optimization:**
   ```bash
   # Automated (recommended)
   python scripts/optimize_database.py --apply
   
   # Manual
   psql $DATABASE_URL < sql/optimize_index.sql
   ```

3. **Restart MCP server** (if using Cursor)
   - Close and reopen Cursor, or
   - `Cmd/Ctrl+Shift+P` → "MCP: Restart Servers"

4. **Verify optimization:**
   ```bash
   python scripts/optimize_database.py --check
   # Should show: ✓ Using optimized HNSW index
   ```

**For fresh installations:**
- Simply use `sql/optimize_index.sql` for complete setup
- No migration needed

### Breaking Changes

None. All changes are backward compatible.

- Database schema unchanged (tables, columns, functions)
- API unchanged (Streamlit app, MCP tool, ingestion)
- Only internal optimization (index type, caching strategy)

### Known Issues & Limitations

1. **Startup Time: 15-18s**
   - Global embedder initialization takes time
   - One-time cost, acceptable for MCP server
   - Not user-facing (happens at server start)

2. **OpenAI API Latency: 500-800ms**
   - Geographic distance (EU → US)
   - External dependency, cannot be optimized
   - Mitigation: Local embedding model (future consideration)

3. **First Query Slower: ~2s**
   - OpenAI connection warm-up
   - Subsequent queries much faster (600-1200ms)
   - Cached queries: <300ms

### Future Optimizations (Planned)

1. **Local Embedding Model** (Optional)
   - Replace OpenAI with `sentence-transformers`
   - Expected: 10-30ms embedding (vs 500-800ms)
   - Trade-off: -3-5% quality for 20x speed

2. **Redis Cache Layer**
   - Distributed cache for query embeddings
   - Expected: 50-70% cache hit rate improvement

3. **Vector Quantization**
   - Store int8 quantized vectors
   - Expected: 75% storage reduction, 30-50% faster searches

### Credits

Performance optimization research and implementation based on:
- [PGVector HNSW Documentation](https://github.com/pgvector/pgvector#hnsw)
- [FastMCP Performance Patterns](https://github.com/jlowin/fastmcp)
- MCP best practices analysis (Cursor community)

---

## [1.0.0] - Previous Version

Initial release with:
- Streamlit UI
- PydanticAI agent
- PostgreSQL/PGVector integration
- Docling document processing
- Audio transcription (Whisper)
- IVFFlat index (lists=1)

