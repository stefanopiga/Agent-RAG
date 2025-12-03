"""
Test script for verifying LangFuse cost tracking.
Run: uv run python scripts/test_cost_tracking.py
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()


async def test_cost_tracking():
    # Check LangFuse config
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key:
        print("⚠️  LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY non configurati")
        print("   Aggiungi al file .env per abilitare cost tracking")
        print()
    else:
        print(f"✅ LangFuse configurato (public_key: {public_key[:10]}...)")

    # Initialize services
    print("\n📦 Inizializzazione servizi...")
    from core.rag_service import (
        close_global_embedder,
        initialize_global_embedder,
        search_knowledge_base_structured,
    )
    from utils.db_utils import close_database, initialize_database

    await initialize_database()
    await initialize_global_embedder()

    # Execute test query with LONG text to see cost
    query = """
    Explain in detail how Docling works for document processing, including its architecture, 
    the different parsing strategies it uses for PDF, Word, PowerPoint and other formats,
    how it handles tables, images, and complex layouts, the chunking mechanisms available,
    how embeddings are generated and stored in vector databases like PostgreSQL with PGVector,
    and best practices for optimizing RAG retrieval performance with large document collections.
    Also describe integration patterns with LangChain, LlamaIndex, and other AI frameworks.
    """
    print(f"\n🔍 Esecuzione query lunga ({len(query)} caratteri)...")

    result = await search_knowledge_base_structured(query, limit=3)

    print("\n📊 Risultati:")
    print(f"   - Documenti trovati: {len(result['results'])}")
    print(f"   - Timing embedding: {result['timing'].get('embedding_ms', 'N/A')}ms")
    print(f"   - Timing DB: {result['timing'].get('db_ms', 'N/A')}ms")
    print(f"   - Timing totale: {result['timing'].get('total_ms', 'N/A')}ms")

    # Cleanup
    await close_global_embedder()
    await close_database()

    print("\n✅ Test completato!")
    print("\n👉 Vai su https://cloud.langfuse.com → Traces per verificare:")
    print("   - Trace 'search_knowledge_base_structured' presente")
    print("   - Span 'embedding-generation' visibile")
    print("   - Cost e token count mostrati")


if __name__ == "__main__":
    asyncio.run(test_cost_tracking())
