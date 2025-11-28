# Deep-Dive: Ingestion Pipeline

**Target:** `ingestion/`
**Generated:** 2025-11-26
**Scope:** `ingest.py`, `chunker.py`, `embedder.py`

## Executive Summary

The Ingestion Pipeline is a robust, asynchronous system designed to process various document formats (PDF, Office, HTML, Markdown) and convert them into vector embeddings for RAG (Retrieval Augmented Generation). It leverages **Docling** for high-fidelity document conversion and structure-aware chunking, ensuring that semantic context is preserved. The pipeline is built on a "clean-slate" default approach (wiping DB before ingest) but supports incremental updates.

## File Inventory

### 1. `ingestion/ingest.py`
- **Purpose:** Main orchestration script. Handles file discovery, document conversion (via Docling), pipeline coordination, and database persistence.
- **Key Class:** `DocumentIngestionPipeline`
- **Exports:** `DocumentIngestionPipeline`, `main`
- **Dependencies:** `chunker`, `embedder`, `utils.db_utils`, `utils.models`, `docling`, `asyncpg`
- **Key Logic:**
    - Recursive file scan for supported extensions.
    - **Docling Integration:** Converts PDF/Office/HTML to Markdown + `DoclingDocument`.
    - **Fast Mode:** Optional flag to disable OCR and table structure analysis for speed.
    - **Database Transaction:** Saves document and chunks atomically.
    - **Error Handling:** Per-file try/catch to ensure pipeline resilience.

### 2. `ingestion/chunker.py`
- **Purpose:** Intelligent document splitting strategies.
- **Key Classes:**
    - `DoclingHybridChunker`: **Primary**. Uses `docling.chunking.HybridChunker`. Token-aware, structure-preserving (keeps headers in context), and semantic.
    - `SimpleChunker`: **Fallback**. Paragraph-based sliding window. Used when Docling fails or for simple text files.
    - `ChunkingConfig`: Configuration dataclass (chunk size, overlap, etc.).
- **Exports:** `create_chunker`, `ChunkingConfig`, `DocumentChunk`
- **Dependencies:** `docling.chunking`, `transformers` (AutoTokenizer), `docling_core`

### 3. `ingestion/embedder.py`
- **Purpose:** Generates vector embeddings for text chunks using OpenAI models.
- **Key Classes:**
    - `EmbeddingGenerator`: Handles batching, retries (exponential backoff), and rate limits.
    - `EmbeddingCache`: In-memory LRU cache to reduce API costs during re-runs.
- **Exports:** `create_embedder`, `EmbeddingGenerator`
- **Dependencies:** `openai`, `utils.providers`

## Data Flow Analysis

1.  **Discovery:** `DocumentIngestionPipeline` scans `documents/` folder.
2.  **Conversion:**
    *   **PDF/Office/HTML:** Passed to `docling.DocumentConverter`. Returns `markdown` string AND `DoclingDocument` object.
    *   **Text/MD:** Read directly as string.
3.  **Chunking:**
    *   Input: `markdown` + `DoclingDocument` (if available).
    *   Process: `DoclingHybridChunker` iterates over `DoclingDocument`, creating `DocumentChunk` objects with `token_count` and `metadata` (including heading hierarchy).
4.  **Embedding:**
    *   Input: List of `DocumentChunk`.
    *   Process: `EmbeddingGenerator` batches chunks (default 100), calls OpenAI API, and assigns vectors.
5.  **Persistence:**
    *   Input: Document metadata + Embedded Chunks.
    *   Process: `_save_to_postgres` writes to `documents` table and `chunks` table (with `vector` type) in a single transaction.

## Integration Points

-   **Docling SDK:** Heavily relied upon for parsing and chunking. Critical dependency.
-   **OpenAI API:** External dependency for embeddings (`text-embedding-3-small` default).
-   **PostgreSQL + PGVector:** Storage backend. Requires `vector` extension.
-   **Utils:** Tightly coupled with `utils.db_utils` for DB connection pooling.

## Key Implementation Details & Patterns

-   **Hybrid Chunking:** The use of `DoclingHybridChunker` is a sophisticated pattern that solves the common RAG problem of "lost context" by embedding header information into every chunk.
-   **Fast Mode:** The `--fast` flag (`ingest.py`) specifically optimizes Docling for speed by disabling expensive OCR and table analysis, useful for digital-native PDFs.
-   **Batching & Resilience:** `embedder.py` implements robust error handling for API flakes, ensuring long ingestion jobs don't fail midway.
-   **Clean-Slate Default:** The pipeline defaults to `clean_before_ingest=True`, which simplifies state management but makes incremental updates harder.

## Risks & Recommendations

-   **Memory Usage:** Loading large PDFs into memory (Docling object) and processing all chunks in memory before DB write could be an issue for massive files.
    *   *Recommendation:* Consider streaming or processing chunks in smaller groups for very large files.
-   **Docling Dependency:** Strong coupling with Docling's internal data structures.
    *   *Recommendation:* Maintain the `SimpleChunker` fallback as a safety net.
-   **Incremental Ingestion:** Currently deletes all data by default.
    *   *Recommendation:* Implement a checksum-based or timestamp-based incremental ingestion to only process new/modified files.
