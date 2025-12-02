# Data Retention Strategy

## Overview

This document describes the data retention and archival strategy for the `query_logs` table in the docling-rag-agent project. The strategy addresses storage growth concerns by implementing multiple layers of protection.

**Reference Documentation:**

- [Supabase Partitioning Guide](https://supabase.com/docs/guides/database/partitions)
- [Supabase Cron/pg_cron Guide](https://supabase.com/docs/guides/cron)

## Problem Statement

The `query_logs` table stores all user queries and AI responses for observability purposes. Without limits:

- `response_text` column (TEXT type) can grow unbounded
- Storage costs increase linearly with usage
- Query performance degrades as table grows
- Backup/restore times increase

## Mitigation Strategy

### 1. Application-Level Truncation (Primary Protection)

**Location:** `utils/session_manager.py`

```python
MAX_RESPONSE_TEXT_BYTES = 10240  # 10KB limit

def truncate_response_text(response_text: Optional[str]) -> Optional[str]:
    """Truncate response to MAX_RESPONSE_TEXT_BYTES if exceeded."""
    # ... implementation
```

**Behavior:**

- Responses exceeding 10KB are truncated before database insertion
- Truncated responses include indicator: `[... response truncated for storage ...]`
- UTF-8 safe truncation (handles multi-byte characters)

**Why 10KB?**

- Typical RAG responses are 500-2000 characters (~0.5-2KB)
- 10KB accommodates detailed responses with citations
- Prevents outliers (malformed responses, errors) from bloating storage

### 2. Database-Level Constraint (Safeguard)

**Location:** `sql/01-init-schema.sql`

```sql
CREATE TABLE query_logs (
    ...
    response_text TEXT,
    CONSTRAINT response_text_max_size CHECK (
        response_text IS NULL OR octet_length(response_text) <= 10240
    )
);
```

**Behavior:**

- INSERT/UPDATE fails if response_text exceeds 10KB
- Acts as failsafe if application-level truncation is bypassed
- Error is logged and can be monitored

### 3. Monthly Table Partitioning

**Location:** `sql/01-init-schema.sql`

```sql
CREATE TABLE query_logs (
    ...
    PRIMARY KEY (timestamp, id)
) PARTITION BY RANGE (timestamp);
```

**Benefits:**

- Queries on recent data only scan relevant partitions
- Old partitions can be dropped for instant bulk deletion
- Vacuum/analyze operations are faster per partition
- Easy archival: detach partition → export → attach to archive schema

**Partition Naming:** `query_logs_YYYY_MM` (e.g., `query_logs_2025_01`)

**Automatic Creation:**

```sql
SELECT create_future_partitions();  -- Creates next 3 months
```

### 4. Automated Retention Policy (pg_cron)

**Location:** `sql/01-init-schema.sql`

**Cleanup Functions:**

```sql
-- Delete query_logs older than N days
SELECT delete_old_query_logs(90);

-- Delete inactive sessions older than N days
SELECT delete_old_sessions(90);
```

**Scheduled Jobs (Supabase/pg_cron):**

```sql
-- Daily cleanup at 3 AM UTC (90-day retention)
SELECT cron.schedule(
    'cleanup-old-query-logs',
    '0 3 * * *',
    $$SELECT delete_old_query_logs(90)$$
);

-- Monthly partition creation (1st of month at 1 AM UTC)
SELECT cron.schedule(
    'create-query-logs-partitions',
    '0 1 1 * *',
    $$SELECT create_future_partitions()$$
);
```

## Configuration

### Retention Period

Default: **90 days**

To change retention period, modify the pg_cron job:

```sql
-- Change to 30-day retention
SELECT cron.unschedule('cleanup-old-query-logs');
SELECT cron.schedule(
    'cleanup-old-query-logs',
    '0 3 * * *',
    $$SELECT delete_old_query_logs(30)$$
);
```

### Response Size Limit

Default: **10KB (10,240 bytes)**

To change, update both:

1. **Application:** `utils/session_manager.py`

   ```python
   MAX_RESPONSE_TEXT_BYTES = 20480  # 20KB
   ```

2. **Database:** Run migration
   ```sql
   ALTER TABLE query_logs
   DROP CONSTRAINT response_text_max_size,
   ADD CONSTRAINT response_text_max_size CHECK (
       response_text IS NULL OR octet_length(response_text) <= 20480
   );
   ```

## Setup Instructions

### For Supabase (Cloud)

1. **Enable pg_cron** (if not already enabled):

   - Go to Database → Extensions → Enable `pg_cron`

2. **Run schema migration:**

   ```sql
   -- Run contents of sql/01-init-schema.sql in SQL Editor
   ```

3. **Schedule cleanup jobs:**

   ```sql
   -- Schedule daily cleanup (90-day retention)
   SELECT cron.schedule(
       'cleanup-old-query-logs',
       '0 3 * * *',
       $$SELECT delete_old_query_logs(90)$$
   );

   SELECT cron.schedule(
       'cleanup-old-sessions',
       '30 3 * * *',
       $$SELECT delete_old_sessions(90)$$
   );

   SELECT cron.schedule(
       'create-query-logs-partitions',
       '0 1 1 * *',
       $$SELECT create_future_partitions()$$
   );
   ```

4. **Verify jobs are scheduled:**
   ```sql
   SELECT * FROM cron.job;
   ```

### For Self-Hosted PostgreSQL

1. **Install pg_cron extension:**

   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql-16-cron
   ```

2. **Enable in postgresql.conf:**

   ```
   shared_preload_libraries = 'pg_cron'
   cron.database_name = 'your_database'
   ```

3. **Restart PostgreSQL and create extension:**

   ```sql
   CREATE EXTENSION pg_cron;
   ```

4. **Run schema migration and schedule jobs** (same as Supabase)

### For Docker (Development)

For development without pg_cron, run cleanup manually:

```sql
-- Manual cleanup (run periodically)
SELECT delete_old_query_logs(90);
SELECT delete_old_sessions(90);
SELECT create_future_partitions();
```

Or use external scheduler (cron, systemd timer, etc.):

```bash
# crontab entry for daily cleanup
0 3 * * * psql $DATABASE_URL -c "SELECT delete_old_query_logs(90)"
```

## Monitoring

### Check Storage Usage

```sql
-- Table sizes including partitions
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as size
FROM pg_tables
WHERE tablename LIKE 'query_logs%'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
```

### Check Partition Status

```sql
-- List all partitions
SELECT
    child.relname AS partition_name,
    pg_get_expr(child.relpartbound, child.oid) AS partition_range
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'query_logs';
```

### Check Cron Job History

```sql
-- Recent job runs
SELECT
    jobid,
    jobname,
    status,
    start_time,
    end_time,
    return_message
FROM cron.job_run_details
ORDER BY start_time DESC
LIMIT 20;
```

### Check Truncation Activity

```sql
-- Count truncated responses (last 30 days)
SELECT COUNT(*)
FROM query_logs
WHERE timestamp > NOW() - INTERVAL '30 days'
  AND response_text LIKE '%[... response truncated for storage ...]';
```

## Manual Archival

### Archive Old Partition

```sql
-- 1. Create archive schema
CREATE SCHEMA IF NOT EXISTS archive;

-- 2. Detach partition
ALTER TABLE query_logs DETACH PARTITION query_logs_2024_01;

-- 3. Move to archive schema
ALTER TABLE query_logs_2024_01 SET SCHEMA archive;

-- 4. (Optional) Export to file
COPY archive.query_logs_2024_01 TO '/path/to/archive/query_logs_2024_01.csv' CSV HEADER;
```

### Drop Old Partition (Bulk Delete)

```sql
-- Fastest way to delete old data
ALTER TABLE query_logs DETACH PARTITION query_logs_2024_01;
DROP TABLE query_logs_2024_01;
```

## Summary

| Layer                  | Protection             | When Applied      |
| ---------------------- | ---------------------- | ----------------- |
| Application Truncation | Limit response to 10KB | Before INSERT     |
| DB CHECK Constraint    | Reject > 10KB          | On INSERT/UPDATE  |
| Partitioning           | Isolate data by month  | Table structure   |
| pg_cron Cleanup        | Delete data > 90 days  | Daily at 3 AM UTC |

This multi-layer approach ensures:

- ✅ Bounded storage growth per response
- ✅ Efficient queries on recent data
- ✅ Easy archival/deletion of old data
- ✅ Automated maintenance
- ✅ Configurable retention period
