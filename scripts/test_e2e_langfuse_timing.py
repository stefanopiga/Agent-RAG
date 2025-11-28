#!/usr/bin/env python
"""
E2E Test: Execute full query workflow to verify timing breakdown in LangFuse.

Run this script to execute a real query and verify timing appears in LangFuse dashboard.

Usage:
    uv run python scripts/test_e2e_langfuse_timing.py

Expected LangFuse output:
- Trace: query_knowledge_base
  - Span: embedding-generation
    - metadata.duration_ms: timing in milliseconds
    - metadata.embedding_time_ms: embedding generation time
    - metadata.db_search_time_ms: database search time
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


async def main():
    print("=" * 60)
    print("E2E Test: LangFuse Timing Breakdown Verification")
    print("=" * 60)

    # Check LangFuse configuration
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key:
        print("\n[WARNING] LangFuse not configured!")
        print("Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env")
        print("Proceeding anyway to verify metrics...")
    else:
        print(f"\n[OK] LangFuse configured (public_key: {public_key[:10]}...)")

    # Initialize database
    print("\n[1/4] Initializing database connection...")
    from utils.db_utils import initialize_database

    await initialize_database()
    print("      Database initialized")

    # Initialize embedder
    print("\n[2/4] Initializing embedder (may take ~40s on cold start)...")
    from core.rag_service import get_global_embedder, initialize_global_embedder

    await initialize_global_embedder()

    # Wait for embedder to be ready
    embedder = await get_global_embedder()
    print(f"      Embedder ready: {embedder is not None}")

    # Initialize LangFuse
    print("\n[3/4] Initializing LangFuse...")
    from docling_mcp.lifespan import _initialize_langfuse, is_langfuse_enabled

    _initialize_langfuse()
    print(f"      LangFuse enabled: {is_langfuse_enabled()}")

    # Execute query
    print("\n[4/4] Executing test query...")
    test_query = "What is Docling and how does it work?"

    from docling_mcp.server import query_knowledge_base

    print(f"\n      Query: '{test_query}'")
    print("      Executing...")

    try:
        result = await query_knowledge_base.fn(test_query, limit=3)

        print("\n" + "=" * 60)
        print("QUERY RESULT:")
        print("=" * 60)
        print(result[:500] + "..." if len(result) > 500 else result)

        print("\n" + "=" * 60)
        print("VERIFICATION STEPS:")
        print("=" * 60)
        print("""
1. Open LangFuse dashboard: https://cloud.langfuse.com

2. Navigate to Traces

3. Find the trace named 'query_knowledge_base'

4. Verify timing breakdown in spans:
   - Click on the trace to expand
   - Look for 'embedding-generation' span
   - Check metadata for:
     * duration_ms: Total span duration
     * embedding_time_ms: Embedding generation time
     * db_search_time_ms: Database search time

5. Expected timing values:
   - embedding_time_ms: 100-500ms (SLO: <500ms)
   - db_search_time_ms: 20-100ms (SLO: <100ms)
   - Total duration: <2000ms (SLO: <2s p95)
""")

    except Exception as e:
        print(f"\n[ERROR] Query failed: {e}")
        import traceback

        traceback.print_exc()

    # Flush LangFuse
    print("\n[CLEANUP] Flushing LangFuse traces...")
    from docling_mcp.lifespan import _shutdown_langfuse

    _shutdown_langfuse()

    # Close database
    from utils.db_utils import close_database

    await close_database()

    print("\n[DONE] Check LangFuse dashboard for timing breakdown")


if __name__ == "__main__":
    asyncio.run(main())
