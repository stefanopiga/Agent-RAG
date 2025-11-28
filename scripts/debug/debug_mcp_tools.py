#!/usr/bin/env python3
"""
Debug MCP Tools
===============
Inspects the MCP server and lists registered tools.

Usage:
    uv run python scripts/debug/debug_mcp_tools.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from docling_mcp.server import mcp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def inspect_tools():
    print("Inspecting MCP Server Tools...")

    # Try using get_tools()
    try:
        tools = await mcp.get_tools()
        print(f"Type of tools: {type(tools)}")
        print(f"Tools repr: {tools}")

        tool_names = []
        if isinstance(tools, dict):
            print(f"Found {len(tools)} tools (dict):")
            for name, tool in tools.items():
                print(f" - {name}: {tool}")
                tool_names.append(name)
        elif isinstance(tools, list):
            print(f"Found {len(tools)} tools (list):")
            for tool in tools:
                print(f" - {tool}")
                if hasattr(tool, "name"):
                    tool_names.append(tool.name)
                else:
                    tool_names.append(str(tool))
        else:
            print(f"Unknown tools type: {type(tools)}")

        print(f"Tool Names: {tool_names}")

        expected_tools = [
            "query_knowledge_base",
            "list_knowledge_base_documents",
            "get_knowledge_base_document",
            "get_knowledge_base_overview",
            "ask_knowledge_base",
        ]

        all_found = True
        for tool in expected_tools:
            if tool in tool_names:
                print(f"  ✅ {tool}")
            else:
                print(f"  ❌ {tool} MISSING")
                all_found = False

        if all_found:
            print("\n[SUCCESS] All expected tools are registered.")
        else:
            print("\n[FAIL] Some tools are missing.")

    except Exception as e:
        print(f"Error calling get_tools(): {e}")

        # Fallback: check _tool_manager if available
        if hasattr(mcp, "_tool_manager"):
            print("\nChecking _tool_manager...")
            tm = mcp._tool_manager
            print(f"Tool Manager: {tm}")


if __name__ == "__main__":
    try:
        asyncio.run(inspect_tools())
    except Exception as e:
        print(f"Error inspecting tools: {e}")
        sys.exit(1)
