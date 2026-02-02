#!/usr/bin/env python3
"""
MCP Server Entry Point with Observability
==========================================
Unified entry point that runs:
1. MCP server on STDIO (for Cursor/Claude Desktop integration)
2. HTTP server on port 8080 (for /health and /metrics endpoints)

Usage:
    uv run python mcp_server.py

Cursor MCP Configuration (mcp.json):
    {
      "docling-rag": {
        "command": "uv",
        "args": [
          "run",
          "--project",
          "C:/path/to/docling-rag-agent",
          "python",
          "C:/path/to/docling-rag-agent/mcp_server.py"
        ]
      }
    }

Endpoints (after server starts):
    - http://localhost:8080/health  - Health check
    - http://localhost:8080/metrics - Prometheus metrics
    - http://localhost:8080/docs    - API documentation
"""

import asyncio
import logging
import os
import threading
from typing import Optional

# Load environment variables FIRST (before any other imports)
from dotenv import load_dotenv

load_dotenv()

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def start_http_server_thread(host: str = "0.0.0.0", port: int = 8080) -> Optional[threading.Thread]:
    """
    Start the HTTP observability server in a background thread.
    
    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to listen on (default: 8080, or METRICS_PORT env var)
    
    Returns:
        Thread object if started successfully, None otherwise
    """
    port = int(os.getenv("METRICS_PORT", port))
    
    def run_server():
        try:
            import uvicorn

            from docling_mcp.http_server import app
            
            # Suppress uvicorn access logs to avoid polluting STDIO
            uvicorn_config = uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level="warning",
                access_log=False,
            )
            server = uvicorn.Server(uvicorn_config)
            
            # Run in a new event loop for the thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(server.serve())
        except Exception as e:
            logger.error(f"HTTP server error: {e}")
    
    thread = threading.Thread(target=run_server, daemon=True, name="http-observability")
    thread.start()
    logger.info(f"HTTP observability server started on http://{host}:{port}")
    logger.info(f"  - Health: http://localhost:{port}/health")
    logger.info(f"  - Metrics: http://localhost:{port}/metrics")
    return thread


def main():
    """Main entry point."""
    # Start HTTP server for observability in background
    http_thread = start_http_server_thread()
    
    # Import and run MCP server (blocks on STDIO)
    from docling_mcp.server import mcp
    
    logger.info("Starting MCP server on STDIO...")
    mcp.run()


if __name__ == "__main__":
    main()

