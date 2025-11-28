-- ============================================================================
-- Optimized Database Schema for docling-rag-agent       FIRST MIGRATION
-- ============================================================================
-- Purpose: Complete database setup with optimized HNSW vector index
-- 
-- This file contains:
-- 1. Complete schema (tables, functions, triggers)
-- 2. Optimized HNSW index (10-100x faster than IVFFlat lists=1)
-- 3. Performance indexes for filtering and queries
--
-- Usage:
--   Fresh install:  psql $DATABASE_URL < sql/optimize_index.sql
--   Upgrade index:  Run sections 2-3 only (skip section 1 if schema exists)
-- ============================================================================

-- ============================================================================
-- SECTION 1: SCHEMA SETUP (Skip if upgrading existing database)
-- ============================================================================

-- Clean slate (USE WITH CAUTION - drops all data)
-- Uncomment only for fresh install:
-- DROP TABLE IF EXISTS chunks CASCADE;
-- DROP TABLE IF EXISTS documents CASCADE;
-- DROP FUNCTION IF EXISTS match_chunks CASCADE;
-- DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create chunks table
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536),
    chunk_index INTEGER NOT NULL,
    metadata JSONB DEFAULT '{}',
    token_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create match_chunks function for vector search
CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding vector(1536),
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    similarity FLOAT,
    metadata JSONB,
    document_title TEXT,
    document_source TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id AS chunk_id,
        c.document_id,
        c.content,
        1 - (c.embedding <=> query_embedding) AS similarity,
        c.metadata,
        d.title AS document_title,
        d.source AS document_source
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE c.embedding IS NOT NULL
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Create trigger for updated_at auto-update
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SECTION 2: INDEX OPTIMIZATION (Run for both fresh install and upgrade)
-- ============================================================================

-- Check current index status (diagnostic)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'chunks' 
        AND indexname LIKE '%embedding%'
    ) THEN
        RAISE NOTICE 'Existing embedding index found - will be replaced with HNSW';
    ELSE
        RAISE NOTICE 'No existing embedding index - creating new HNSW index';
    END IF;
END $$;

-- Drop old inefficient indexes (IVFFlat, old HNSW, etc.)
DROP INDEX IF EXISTS idx_chunks_embedding CASCADE;
DROP INDEX IF EXISTS idx_chunks_embedding_hnsw CASCADE;

-- Create optimized HNSW index
-- m=16: Number of connections per layer (16 is balanced for most use cases)
-- ef_construction=64: Search depth during index build (higher = better quality, slower build)
CREATE INDEX idx_chunks_embedding_hnsw ON chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Note: ef_search is set at session level, not index level
-- Use: SET hnsw.ef_search = 100; before queries for higher accuracy
-- Default ef_search is 40, which provides good balance

-- ============================================================================
-- SECTION 3: ADDITIONAL PERFORMANCE INDEXES
-- ============================================================================

-- Standard indexes for document management
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN (metadata);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks (document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON chunks (document_id, chunk_index);

-- Optimize source filtering queries (used in source_filter parameter)
CREATE INDEX IF NOT EXISTS idx_documents_source_trgm ON documents 
USING gin (source gin_trgm_ops);

-- Composite index for filtered vector searches
-- (Improves performance when source_filter is used)
CREATE INDEX IF NOT EXISTS idx_chunks_doc_embedding ON chunks (document_id)
INCLUDE (embedding, content, metadata);

-- ============================================================================
-- SECTION 4: VERIFICATION & DIAGNOSTICS
-- ============================================================================

-- Verify schema and indexes
DO $$ 
DECLARE
    doc_count INTEGER;
    chunk_count INTEGER;
    index_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO doc_count FROM documents;
    SELECT COUNT(*) INTO chunk_count FROM chunks;
    SELECT COUNT(*) INTO index_count FROM pg_indexes 
        WHERE tablename IN ('chunks', 'documents');
    
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Database Setup Complete';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Documents: %', doc_count;
    RAISE NOTICE 'Chunks: %', chunk_count;
    RAISE NOTICE 'Indexes: %', index_count;
    RAISE NOTICE '==============================================';
END $$;

-- List all indexes (for manual verification)
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
FROM pg_indexes
WHERE tablename IN ('chunks', 'documents')
ORDER BY tablename, indexname;

-- Verify HNSW index exists
SELECT 
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'chunks' 
            AND indexname = 'idx_chunks_embedding_hnsw'
        ) 
        THEN '✓ HNSW index created successfully'
        ELSE '✗ WARNING: HNSW index not found'
    END AS status;

-- ============================================================================
-- OPTIONAL: Performance Testing
-- ============================================================================
-- Uncomment to test vector search performance
-- (Requires existing embeddings in chunks table)

-- EXPLAIN ANALYZE
-- SELECT 
--     c.id AS chunk_id,
--     c.document_id,
--     c.content,
--     1 - (c.embedding <=> (SELECT embedding FROM chunks LIMIT 1)) AS similarity
-- FROM chunks c
-- JOIN documents d ON c.document_id = d.id
-- WHERE c.embedding IS NOT NULL
-- ORDER BY c.embedding <=> (SELECT embedding FROM chunks LIMIT 1)
-- LIMIT 5;

-- ============================================================================
-- Maintenance & Troubleshooting
-- ============================================================================
-- 
-- ANALYZE tables for query planner:
--   ANALYZE documents;
--   ANALYZE chunks;
--
-- Check index usage:
--   SELECT * FROM pg_stat_user_indexes WHERE indexrelname LIKE '%embedding%';
--
-- Rebuild index if performance degrades:
--   DROP INDEX idx_chunks_embedding_hnsw;
--   CREATE INDEX idx_chunks_embedding_hnsw ON chunks 
--     USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
--
-- Tune query-time accuracy (session-level):
--   SET hnsw.ef_search = 100;  -- Higher = better recall, slower query
--
-- Monitor query performance:
--   Target: <100ms for vector searches
--   HNSW typically 10-100x faster than IVFFlat with lists=1
--
-- Index size considerations:
--   - HNSW ≈ 1.5x dataset size
--   - IVFFlat ≈ 1.2x dataset size
--   - Rebuild if dataset grows >10x original size
--
-- ============================================================================

