-- Epic 3: Verifica Setup Session Tables
-- Eseguire questo script per verificare che tutto sia stato creato correttamente

-- 1. Verifica tabelle create
SELECT 
    table_name,
    table_type
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('sessions', 'query_logs')
ORDER BY table_name;

-- 2. Verifica RLS abilitato
SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('sessions', 'query_logs')
ORDER BY tablename;

-- 3. Verifica policies create
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies 
WHERE schemaname = 'public' 
  AND tablename IN ('sessions', 'query_logs')
ORDER BY tablename, policyname;

-- 4. Verifica indexes creati
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
  AND tablename IN ('sessions', 'query_logs')
ORDER BY tablename, indexname;

-- 5. Test protezione RLS (dovrebbe restituire 0 righe con anon role)
SET ROLE anon;
SELECT COUNT(*) as anon_access_count FROM sessions;
SELECT COUNT(*) as anon_access_count FROM query_logs;
RESET ROLE;

-- 6. Test accesso service_role (dovrebbe funzionare)
SET ROLE service_role;
SELECT COUNT(*) as service_role_access_count FROM sessions;
SELECT COUNT(*) as service_role_access_count FROM query_logs;
RESET ROLE;

