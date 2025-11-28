#!/usr/bin/env python3
"""
Script di verifica completa per setup MCP Server.
Verifica tutti i componenti necessari per il funzionamento del server MCP.

Usage:
    uv run python scripts/verification/verify_mcp_setup.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path (scripts/verification/ -> scripts/ -> project_root)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def check_imports():
    """Verifica che tutte le dipendenze siano installate."""
    print("🔍 Verifica dipendenze...")
    try:
        from fastmcp import FastMCP  # noqa: F401

        print("  ✅ fastmcp installato")
    except ImportError:
        print("  ❌ fastmcp non installato - esegui: uv sync")
        return False

    try:
        from client.api_client import RAGClient  # noqa: F401

        print("  ✅ client.api_client disponibile")
    except ImportError as e:
        print(f"  ❌ Errore import client: {e}")
        return False

    return True


async def check_mcp_server():
    """Verifica che il server MCP sia configurato correttamente."""
    print("\n🔍 Verifica server MCP...")
    try:
        from docling_mcp.server import mcp

        # Verifica tool registrati
        tools = await mcp.get_tools()
        tool_names = list(tools.keys())

        print("  ✅ Server MCP inizializzato")
        print(f"  ✅ Tool registrati: {len(tool_names)}")

        expected_tools = [
            "query_knowledge_base",
            "list_knowledge_base_documents",
            "get_knowledge_base_document",
            "get_knowledge_base_overview",
            "ask_knowledge_base",
        ]
        for tool in expected_tools:
            if tool in tool_names:
                print(f"    ✅ {tool}")
            else:
                print(f"    ❌ {tool} MANCANTE")
                return False

        return True
    except Exception as e:
        print(f"  ❌ Errore server MCP: {e}")
        import traceback

        traceback.print_exc()
        return False


async def check_rag_api():
    """Verifica che l'API RAG sia disponibile."""
    print("\n🔍 Verifica API RAG...")
    try:
        from client.api_client import RAGClient

        client = RAGClient()

        # Health check
        is_healthy = await client.health_check()
        if is_healthy:
            print(f"  ✅ API RAG disponibile su {client.base_url}")

            # Test list documents
            try:
                response = await client.list_documents(limit=1)
                doc_count = response.get("count", 0)
                print(f"  ✅ Knowledge base accessibile ({doc_count} documenti)")
                return True
            except Exception as e:
                print(f"  ⚠️  API disponibile ma errore accesso KB: {e}")
                return False
        else:
            print(f"  ❌ API RAG non disponibile su {client.base_url}")
            print("     Assicurati che il servizio sia avviato:")
            print("     - docker-compose up rag-api")
            print("     - oppure avvia manualmente l'API")
            return False
    except Exception as e:
        print(f"  ❌ Errore verifica API: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_env_vars():
    """Verifica variabili d'ambiente essenziali."""
    print("\n🔍 Verifica variabili d'ambiente...")

    from dotenv import load_dotenv

    load_dotenv()

    required_vars = ["DATABASE_URL", "OPENAI_API_KEY"]
    all_ok = True

    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Maschera valori sensibili
            if "KEY" in var or "PASSWORD" in var:
                masked = value[:8] + "..." if len(value) > 8 else "***"
                print(f"  ✅ {var} = {masked}")
            else:
                print(f"  ✅ {var} = {value[:50]}...")
        else:
            print(f"  ❌ {var} non impostata")
            all_ok = False

    return all_ok


def check_cursor_config():
    """Verifica configurazione Cursor (se possibile)."""
    print("\n🔍 Verifica configurazione Cursor...")

    # Percorsi possibili per configurazione MCP
    possible_paths = [
        Path.home()
        / "AppData"
        / "Roaming"
        / "Cursor"
        / "User"
        / "globalStorage"
        / "rooveterinaryinc.roo-cline"
        / "settings"
        / "cline_mcp_settings.json",
        Path.home()
        / ".config"
        / "Cursor"
        / "User"
        / "globalStorage"
        / "rooveterinaryinc.roo-cline"
        / "settings"
        / "cline_mcp_settings.json",
        Path.home()
        / "Library"
        / "Application Support"
        / "Cursor"
        / "User"
        / "globalStorage"
        / "rooveterinaryinc.roo-cline"
        / "settings"
        / "cline_mcp_settings.json",
    ]

    config_found = False
    for config_path in possible_paths:
        if config_path.exists():
            print(f"  ✅ Configurazione trovata: {config_path}")
            config_found = True

            # Leggi e verifica contenuto
            try:
                import json

                with open(config_path, "r") as f:
                    config = json.load(f)

                if "mcpServers" in config:
                    servers = config["mcpServers"]
                    if "docling-rag" in servers:
                        print("    ✅ Server 'docling-rag' configurato")
                        server_config = servers["docling-rag"]
                        print(f"    Command: {server_config.get('command', 'N/A')}")
                        print(f"    Args: {server_config.get('args', [])}")
                    else:
                        print("    ⚠️  Server 'docling-rag' non trovato nella configurazione")
                        print(f"    Server disponibili: {list(servers.keys())}")
                else:
                    print("    ⚠️  Struttura configurazione non riconosciuta")
            except Exception as e:
                print(f"    ⚠️  Errore lettura configurazione: {e}")

            break

    if not config_found:
        print("  ⚠️  Configurazione Cursor non trovata nei percorsi standard")
        print("     Configura manualmente in Cursor: Settings > Features > MCP")

    return True  # Non bloccante


async def main():
    """Esegui tutte le verifiche."""
    print("=" * 60)
    print("VERIFICA SETUP MCP SERVER")
    print("=" * 60)

    checks = [
        ("Dipendenze", check_imports()),
        ("Variabili Ambiente", check_env_vars()),
        ("Server MCP", check_mcp_server()),
        ("API RAG", check_rag_api()),
        ("Config Cursor", check_cursor_config()),
    ]

    results = []
    for name, check_coro in checks:
        if asyncio.iscoroutine(check_coro):
            result = await check_coro
        else:
            result = check_coro
        results.append((name, result))

    print("\n" + "=" * 60)
    print("RIEPILOGO")
    print("=" * 60)

    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
        if not result:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✅ Tutte le verifiche sono passate!")
        print("Il server MCP dovrebbe funzionare correttamente.")
        print("\nProssimi passi:")
        print("1. Riavvia Cursor completamente")
        print("2. Verifica che il server MCP sia attivo (indicatore verde)")
        print("3. Prova a usare il tool: mcp_docling-rag_query_knowledge_base")
        return 0
    else:
        print("\n❌ Alcune verifiche sono fallite.")
        print("Risolvi i problemi indicati sopra prima di procedere.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
