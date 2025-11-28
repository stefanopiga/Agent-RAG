#!/usr/bin/env python3
"""
Verify client integration with RAG API.

Usage:
    uv run python scripts/verification/verify_client_integration.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from client.api_client import RAGClient


async def test_client():
    print("\n--- Testing RAGClient ---")
    client = RAGClient()

    # Test Health
    print("Checking Health...")
    if await client.health_check():
        print("[OK] Health check passed")
    else:
        print("[FAIL] Health check failed")
        return False

    # Test Documents List
    print("Listing Documents...")
    try:
        docs = await client.list_documents(limit=1)
        print(f"[OK] Found {docs.get('count', 0)} documents")
    except Exception as e:
        print(f"[FAIL] List documents failed: {e}")
        return False

    # Test Search
    print("Searching...")
    try:
        results = await client.search("test", limit=1)
        print(f"[OK] Search returned {len(results.get('results', []))} results")
    except Exception as e:
        print(f"[FAIL] Search failed: {e}")
        return False

    return True


async def main():
    print("Starting Integration Verification...")

    # We only test the Client because MCP functions are wrapped by FastMCP
    # and cannot be called directly in this script without mocking the MCP runtime.
    # Since MCP server is just a wrapper around RAGClient, testing RAGClient is sufficient.

    client_ok = await test_client()

    if client_ok:
        print("\n[SUCCESS] Client integration tests passed! \u2705")
        print("Note: MCP functions were skipped as they require MCP runtime context.")
    else:
        print("\n[FAIL] Client tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
