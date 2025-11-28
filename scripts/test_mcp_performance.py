#!/usr/bin/env python3
"""
Test MCP Server Performance
============================
Validates optimizations and measures actual performance.

Usage:
    uv run python scripts/test_mcp_performance.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.rag_service import (
    close_global_embedder,
    initialize_global_embedder,
    search_knowledge_base,
)
from utils.db_utils import close_database, initialize_database


async def test_initialization():
    """Test server initialization time."""
    print("🧪 Test 1: Initialization Performance")
    print("-" * 50)

    start = time.time()

    # Initialize database
    await initialize_database()
    db_time = time.time() - start
    print(f"✓ Database pool initialized: {db_time * 1000:.0f}ms")

    # Initialize embedder
    start = time.time()
    await initialize_global_embedder()
    embedder_time = time.time() - start
    print(f"✓ Global embedder initialized: {embedder_time * 1000:.0f}ms")

    total_time = (db_time + embedder_time) * 1000
    print(f"\n⏱️  Total startup time: {total_time:.0f}ms")

    if total_time < 2000:
        print("✅ PASS: Startup time <2s")
    else:
        print("⚠️  SLOW: Startup time >2s")

    return total_time


async def test_query_performance():
    """Test query performance with timing breakdown."""
    print("\n\n🧪 Test 2: Query Performance")
    print("-" * 50)

    test_queries = ["What is Docling?", "How to use PydanticAI?", "Langfuse deployment guide"]

    results = []

    for i, query in enumerate(test_queries, 1):
        print(f"\nQuery {i}: '{query}'")

        start = time.time()
        try:
            result = await search_knowledge_base(query, limit=3)
            elapsed = (time.time() - start) * 1000

            print(f"⏱️  Latency: {elapsed:.0f}ms")

            if "Found" in result:
                print("✓ Results returned")
            else:
                print(f"⚠️  No results: {result[:100]}")

            results.append(elapsed)

        except Exception as e:
            print(f"❌ Error: {e}")
            results.append(999999)

    # Calculate statistics
    if results:
        avg_latency = sum(results) / len(results)
        max_latency = max(results)
        min_latency = min(results)

        print("\n📊 Query Statistics:")
        print(f"   Avg: {avg_latency:.0f}ms")
        print(f"   Min: {min_latency:.0f}ms")
        print(f"   Max: {max_latency:.0f}ms")

        # Performance assessment
        if avg_latency < 200:
            print("\n✅ EXCELLENT: Average latency <200ms")
        elif avg_latency < 500:
            print("\n🟡 GOOD: Average latency <500ms")
        else:
            print("\n🔴 NEEDS OPTIMIZATION: Average latency >500ms")

        return avg_latency

    return None


async def test_cache_effectiveness():
    """Test embedding cache effectiveness."""
    print("\n\n🧪 Test 3: Cache Effectiveness")
    print("-" * 50)

    query = "Test query for cache performance"

    # First query (cache miss)
    print("\nFirst query (cache miss):")
    start = time.time()
    await search_knowledge_base(query, limit=3)
    first_latency = (time.time() - start) * 1000
    print(f"⏱️  Latency: {first_latency:.0f}ms")

    # Second query (cache hit)
    print("\nSecond query (should hit cache):")
    start = time.time()
    await search_knowledge_base(query, limit=3)
    second_latency = (time.time() - start) * 1000
    print(f"⏱️  Latency: {second_latency:.0f}ms")

    # Calculate improvement
    improvement = ((first_latency - second_latency) / first_latency) * 100

    print("\n📊 Cache Performance:")
    print(f"   First query: {first_latency:.0f}ms")
    print(f"   Cached query: {second_latency:.0f}ms")
    print(f"   Improvement: {improvement:.1f}%")

    if improvement > 20:
        print("\n✅ PASS: Cache providing >20% speedup")
    else:
        print("\n⚠️  WARNING: Cache not effective (<20% speedup)")

    return improvement


async def main():
    """Run all performance tests."""
    print("=" * 50)
    print("MCP Server Performance Tests")
    print("=" * 50)

    try:
        # Test 1: Initialization
        startup_time = await test_initialization()

        # Test 2: Query performance
        avg_latency = await test_query_performance()

        # Test 3: Cache effectiveness
        cache_improvement = await test_cache_effectiveness()

        # Final summary
        print("\n\n" + "=" * 50)
        print("📋 SUMMARY")
        print("=" * 50)
        print(f"Startup time: {startup_time:.0f}ms")
        if avg_latency:
            print(f"Average query latency: {avg_latency:.0f}ms")
        if cache_improvement:
            print(f"Cache speedup: {cache_improvement:.1f}%")

        print("\n🎯 Performance Targets:")
        print(f"   Startup: <2000ms - {'✅ PASS' if startup_time < 2000 else '❌ FAIL'}")
        if avg_latency:
            print(f"   Query: <300ms - {'✅ PASS' if avg_latency < 300 else '⚠️  NEEDS WORK'}")
        if cache_improvement:
            print(f"   Cache: >20% - {'✅ PASS' if cache_improvement > 20 else '⚠️  NEEDS WORK'}")

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        await close_global_embedder()
        await close_database()
        print("✓ Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
