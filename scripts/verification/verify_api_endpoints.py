#!/usr/bin/env python3
"""
Verify API Endpoints
====================
Verifies that all API endpoints are available and working.

Usage:
    uv run python scripts/verification/verify_api_endpoints.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path (scripts/verification/ -> scripts/ -> project_root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import httpx

from client.api_client import RAGClient


async def test_health_check():
    """Test health check endpoint."""
    print("🧪 Testing /health endpoint...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                print("✅ Health check passed")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


async def test_overview_endpoint():
    """Test /v1/overview endpoint."""
    print("\n🧪 Testing /v1/overview endpoint...")
    try:
        client = RAGClient()
        overview = await client.get_overview()

        print("✅ Overview endpoint working")
        print(f"   Total Documents: {overview.get('total_documents', 0)}")
        print(f"   Total Chunks: {overview.get('total_chunks', 0)}")
        print(f"   Unique Sources: {overview.get('unique_sources', 0)}")
        return True
    except Exception as e:
        print(f"❌ Overview endpoint error: {e}")
        return False


async def test_documents_endpoint():
    """Test /v1/documents endpoint."""
    print("\n🧪 Testing /v1/documents endpoint...")
    try:
        client = RAGClient()
        response = await client.list_documents(limit=5)

        print("✅ Documents endpoint working")
        print(f"   Found {response.get('count', 0)} documents")
        return True
    except Exception as e:
        print(f"❌ Documents endpoint error: {e}")
        return False


async def test_search_endpoint():
    """Test /v1/search endpoint."""
    print("\n🧪 Testing /v1/search endpoint...")
    try:
        client = RAGClient()
        response = await client.search("test", limit=1)

        print("✅ Search endpoint working")
        print(f"   Found {len(response.get('results', []))} results")
        return True
    except Exception as e:
        print(f"❌ Search endpoint error: {e}")
        return False


async def main():
    """Run all endpoint tests."""
    print("=" * 60)
    print("API Endpoints Verification")
    print("=" * 60)

    results = []

    # Test health check first
    health_ok = await test_health_check()
    results.append(("Health Check", health_ok))

    if not health_ok:
        print("\n⚠️  API Service is not running!")
        print("   Start it with: uv run uvicorn api.main:app --host 0.0.0.0 --port 8000")
        return

    # Test other endpoints
    results.append(("Overview", await test_overview_endpoint()))
    results.append(("Documents", await test_documents_endpoint()))
    results.append(("Search", await test_search_endpoint()))

    # Summary
    print("\n" + "=" * 60)
    print("📋 Summary")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:20} {status}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 All endpoints are working correctly!")
    else:
        print("\n⚠️  Some endpoints failed. Check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
