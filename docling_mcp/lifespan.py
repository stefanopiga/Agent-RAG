import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastmcp import FastMCP

from core.rag_service import close_global_embedder, initialize_global_embedder
from utils.db_utils import close_database, initialize_database

# Load environment variables (for development consistency)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Module-level LangFuse client state
_langfuse_client = None
_langfuse_enabled = False


def get_langfuse_client():
    """Get the LangFuse client instance if available."""
    return _langfuse_client


def is_langfuse_enabled() -> bool:
    """Check if LangFuse is enabled and initialized."""
    return _langfuse_enabled


def _initialize_langfuse():
    """
    Initialize LangFuse client with graceful degradation.
    Returns (client, enabled) tuple.
    """
    global _langfuse_client, _langfuse_enabled

    # Check for required environment variables
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key:
        logger.warning(
            "LangFuse API keys not configured (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY). "
            "Tracing will be disabled."
        )
        _langfuse_client = None
        _langfuse_enabled = False
        return

    try:
        from langfuse import get_client

        _langfuse_client = get_client()
        _langfuse_enabled = True
        logger.info("LangFuse client initialized successfully.")
    except ImportError as e:
        logger.warning(f"LangFuse SDK not available: {e}. Tracing will be disabled.")
        _langfuse_client = None
        _langfuse_enabled = False
    except Exception as e:
        logger.warning(
            f"Failed to initialize LangFuse client: {e}. Tracing will be disabled.", exc_info=True
        )
        _langfuse_client = None
        _langfuse_enabled = False


def _shutdown_langfuse():
    """Shutdown LangFuse client gracefully."""
    global _langfuse_client, _langfuse_enabled

    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()
            _langfuse_client.shutdown()
            logger.info("LangFuse client shut down successfully.")
        except Exception as e:
            logger.warning(f"Error shutting down LangFuse client: {e}")
        finally:
            _langfuse_client = None
            _langfuse_enabled = False


@asynccontextmanager
async def lifespan(server: FastMCP):
    """
    Lifespan context manager for the MCP server.
    Initializes resources (database, embedder, LangFuse) on startup and cleans up on shutdown.
    """
    logger.info("Starting MCP server lifespan...")

    try:
        # Initialize LangFuse client (graceful degradation if unavailable)
        logger.info("Initializing LangFuse client...")
        _initialize_langfuse()

        # Initialize database connection pool
        logger.info("Initializing database connection...")
        await initialize_database()

        # Initialize global embedder (this might take a moment)
        logger.info("Initializing global embedder...")
        await initialize_global_embedder()

        logger.info("MCP server resources initialized successfully.")
        yield

    except Exception as e:
        logger.error(f"Error during MCP server startup: {e}")
        raise
    finally:
        logger.info("Shutting down MCP server resources...")

        # Clean up resources
        try:
            await close_global_embedder()
            await close_database()
            _shutdown_langfuse()
            logger.info("MCP server resources cleaned up successfully.")
        except Exception as e:
            logger.error(f"Error during MCP server shutdown: {e}")
