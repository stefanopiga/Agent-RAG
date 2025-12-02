-- ============================================================================
-- Database Initialization Script
-- ============================================================================
-- Purpose: Complete database schema setup for docling-rag-agent
-- 
-- This script is automatically executed by PostgreSQL Docker container
-- on first startup (via /docker-entrypoint-initdb.d/)
-- 
-- Contains:
-- 1. Extensions (vector, uuid-ossp, pg_trgm)
-- 2. Core tables (documents, chunks)
-- 3. Functions (match_chunks, update_updated_at_column)
-- 4. Triggers
-- 5. Optimized HNSW index
-- 6. Session tracking tables (sessions, query_logs)
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================================
-- Core RAG Tables
-- ============================================================================

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

-- ============================================================================
-- Functions
-- ============================================================================

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
-- Indexes
-- ============================================================================

-- Performance indexes for documents
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_documents_source_trgm ON documents USING GIN(source gin_trgm_ops);

-- Performance indexes for chunks
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_index ON chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_embedding ON chunks(document_id) WHERE embedding IS NOT NULL;

-- Optimized HNSW vector index (10-100x faster than IVFFlat)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw ON chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- ============================================================================
-- Session Tracking Tables (Epic 3)
-- ============================================================================
-- 
-- RETENTION STRATEGY:
-- 1. response_text limited to 10KB at application level (truncated before insert)
-- 2. query_logs partitioned by month for efficient archival/deletion
-- 3. pg_cron job deletes data older than 90 days (configurable)
-- 4. Old partitions can be dropped manually for bulk deletion
--
-- Reference: https://supabase.com/docs/guides/database/partitions
-- Reference: https://supabase.com/docs/guides/cron
-- ============================================================================

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    query_count INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0.0,
    total_latency_ms DECIMAL(10, 2) DEFAULT 0.0
);

-- Query logs table with partitioning by timestamp (monthly)
-- NOTE: response_text is limited to 10KB at application level
-- The CHECK constraint provides a DB-level safeguard
CREATE TABLE IF NOT EXISTS query_logs (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    response_text TEXT,  -- Limited to 10KB at app level, see utils/session_manager.py
    cost DECIMAL(10, 6) NOT NULL,
    latency_ms DECIMAL(10, 2) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    langfuse_trace_id VARCHAR(255),
    -- Include timestamp in PK for partitioning requirement
    PRIMARY KEY (timestamp, id),
    -- DB-level safeguard: reject responses > 10KB (10240 bytes)
    CONSTRAINT response_text_max_size CHECK (
        response_text IS NULL OR octet_length(response_text) <= 10240
    )
) PARTITION BY RANGE (timestamp);

-- Create partitions for current and next 3 months
-- Partitions should be created by a scheduled job or manually
-- Example partitions (adjust dates as needed):
DO $$
DECLARE
    start_date DATE := DATE_TRUNC('month', CURRENT_DATE);
    end_date DATE;
    partition_name TEXT;
BEGIN
    -- Create partitions for current month and next 3 months
    FOR i IN 0..3 LOOP
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'query_logs_' || TO_CHAR(start_date, 'YYYY_MM');
        
        -- Check if partition exists before creating
        IF NOT EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = partition_name AND n.nspname = 'public'
        ) THEN
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF query_logs 
                 FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
        END IF;
        
        start_date := end_date;
    END LOOP;
END $$;

-- Default partition for data outside defined ranges
CREATE TABLE IF NOT EXISTS query_logs_default PARTITION OF query_logs DEFAULT;

-- Indexes for session tracking (created on parent table, inherited by partitions)
CREATE INDEX IF NOT EXISTS idx_query_logs_session_id ON query_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);

-- ============================================================================
-- Data Retention Policy (pg_cron)
-- ============================================================================
-- 
-- Enable pg_cron extension (requires superuser on self-hosted, 
-- available by default on Supabase)
-- Reference: https://supabase.com/docs/guides/cron
-- ============================================================================

-- Enable pg_cron extension (comment out if not available)
-- CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Function to delete old query logs (older than retention_days)
CREATE OR REPLACE FUNCTION delete_old_query_logs(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count INTEGER;
    cutoff_date TIMESTAMP WITH TIME ZONE;
BEGIN
    cutoff_date := NOW() - (retention_days || ' days')::INTERVAL;
    
    -- Delete old records
    DELETE FROM query_logs WHERE timestamp < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Log deletion
    RAISE NOTICE 'Deleted % query_logs older than % days (cutoff: %)', 
        deleted_count, retention_days, cutoff_date;
    
    RETURN deleted_count;
END;
$$;

-- Function to delete old sessions (inactive for retention_days)
CREATE OR REPLACE FUNCTION delete_old_sessions(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    deleted_count INTEGER;
    cutoff_date TIMESTAMP WITH TIME ZONE;
BEGIN
    cutoff_date := NOW() - (retention_days || ' days')::INTERVAL;
    
    -- Delete old sessions (CASCADE will delete related query_logs)
    DELETE FROM sessions WHERE last_activity < cutoff_date;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Deleted % sessions inactive for more than % days', 
        deleted_count, retention_days;
    
    RETURN deleted_count;
END;
$$;

-- Function to create future partitions (run monthly)
CREATE OR REPLACE FUNCTION create_future_partitions()
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    start_date DATE := DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month');
    end_date DATE;
    partition_name TEXT;
BEGIN
    -- Create partition for next month if not exists
    FOR i IN 1..3 LOOP
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'query_logs_' || TO_CHAR(start_date, 'YYYY_MM');
        
        IF NOT EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = partition_name AND n.nspname = 'public'
        ) THEN
            EXECUTE format(
                'CREATE TABLE IF NOT EXISTS %I PARTITION OF query_logs 
                 FOR VALUES FROM (%L) TO (%L)',
                partition_name, start_date, end_date
            );
            RAISE NOTICE 'Created partition: %', partition_name;
        END IF;
        
        start_date := end_date;
    END LOOP;
END;
$$;

-- ============================================================================
-- pg_cron Job Scheduling (Supabase or self-hosted with pg_cron)
-- ============================================================================
-- 
-- Uncomment and run these commands after enabling pg_cron:
-- 
-- Schedule daily cleanup at 3 AM UTC (delete data older than 90 days):
-- SELECT cron.schedule(
--     'cleanup-old-query-logs',
--     '0 3 * * *',  -- Every day at 3 AM UTC
--     $$SELECT delete_old_query_logs(90)$$
-- );
-- 
-- Schedule daily session cleanup at 3:30 AM UTC:
-- SELECT cron.schedule(
--     'cleanup-old-sessions', 
--     '30 3 * * *',  -- Every day at 3:30 AM UTC
--     $$SELECT delete_old_sessions(90)$$
-- );
-- 
-- Schedule monthly partition creation (1st of each month at 1 AM UTC):
-- SELECT cron.schedule(
--     'create-query-logs-partitions',
--     '0 1 1 * *',  -- First day of each month at 1 AM UTC
--     $$SELECT create_future_partitions()$$
-- );
-- 
-- View scheduled jobs:
-- SELECT * FROM cron.job;
-- 
-- View job run history:
-- SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 10;
-- 
-- Unschedule a job:
-- SELECT cron.unschedule('cleanup-old-query-logs');
-- ============================================================================

