-- Epic 3: Streamlit UI Observability - Session Storage Schema     SECOND MIGRATION
-- Execute this in Supabase SQL Editor after creating tables
-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    query_count INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0.0,
    total_latency_ms DECIMAL(10, 2) DEFAULT 0.0
);
-- Query logs table
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    response_text TEXT,
    cost DECIMAL(10, 6) NOT NULL,
    latency_ms DECIMAL(10, 2) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    langfuse_trace_id VARCHAR(255)
);
-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_query_logs_session_id ON query_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
-- Enable Row Level Security (OBBLIGATORIO per sicurezza)
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_logs ENABLE ROW LEVEL SECURITY;
-- Policies: Solo service_role può accedere (backend only)
-- Questo protegge i dati anche se anon key è esposta
CREATE POLICY "Service role only - sessions" ON sessions FOR ALL TO service_role USING (true);
CREATE POLICY "Service role only - query_logs" ON query_logs FOR ALL TO service_role USING (true);
-- Note: Con queste policies, anche se anon key è esposta pubblicamente,
-- le tabelle sessions e query_logs NON sono accessibili via Supabase Data API.
-- Solo connessioni dirette PostgreSQL con service_role possono accedere.