import asyncio
import logging
import os
import time
from decimal import Decimal

import nest_asyncio
import streamlit as st
from dotenv import load_dotenv
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from client.api_client import RAGClient

# Apply nest_asyncio to allow nested event loops (crucial for Streamlit + Async)
nest_asyncio.apply()

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Session tracking imports
# Import agent from existing module
# We need to make sure we can import from the root directory
import sys

# LangFuse tracing imports (AC3.2.1, AC3.2.2)
from utils.langfuse_streamlit import (
    flush_langfuse,
    with_streamlit_context,
)
from utils.session_manager import (
    InMemorySessionStats,
    create_session,
    extract_cost_from_langfuse,
    generate_session_id,
    get_session_stats,
    log_query,
)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.agent import agent
except ImportError as e:
    st.error(f"Failed to import core.agent: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Docling RAG Agent", page_icon="🤖", layout="wide", initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize session tracking (AC3.1.1)
if "session_id" not in st.session_state:
    st.session_state.session_id = generate_session_id()
    st.session_state.session_db_available = True
    st.session_state.in_memory_stats = None
    logger.info(f"New session created: {st.session_state.session_id}")

# Initialize session in DB (AC3.1.2)
if "session_initialized" not in st.session_state:

    async def init_session():
        success = await create_session(st.session_state.session_id)
        if not success:
            st.session_state.session_db_available = False
            st.session_state.in_memory_stats = InMemorySessionStats(st.session_state.session_id)
        return success

    asyncio.run(init_session())
    st.session_state.session_initialized = True


# Check API health on startup
async def check_api_health():
    client = RAGClient()
    if not await client.health_check():
        st.warning("⚠️ RAG API Service appears to be down. Search functionality may not work.")
    else:
        logger.info("RAG API Service is healthy")


# Run health check once
if "health_checked" not in st.session_state:
    asyncio.run(check_api_health())
    st.session_state.health_checked = True


def convert_streamlit_messages_to_pydantic(messages):
    """Convert Streamlit message history to PydanticAI format."""
    pydantic_messages = []

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            pydantic_messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            pydantic_messages.append(ModelResponse(parts=[TextPart(content=content)]))

    return pydantic_messages


async def run_agent_with_tracking(user_input: str) -> tuple[str, Decimal, Decimal, str | None]:
    """
    Run the agent with session tracking and LangFuse tracing.

    Uses with_streamlit_context() to create root span with session_id
    propagation to all nested spans (AC3.2.1, AC3.2.2).

    Returns:
        Tuple of (response_text, cost, latency_ms, trace_id)
    """
    start_time = time.perf_counter()
    trace_id = None
    cost = Decimal("0.0")
    response_text = ""

    # Get session_id from session state
    session_id = st.session_state.session_id

    # Convert history to PydanticAI format
    history = convert_streamlit_messages_to_pydantic(st.session_state.messages[:-1])

    # Wrap agent execution with LangFuse tracing (AC3.2.1, AC3.2.2, AC3.2.4)
    # This creates root span "streamlit_query" with session_id propagation
    with with_streamlit_context(session_id, user_input) as ctx:
        try:
            # Run the agent - nested spans inherit session_id via propagate_attributes
            result = await agent.run(user_input, message_history=history)
            response_text = result.output if hasattr(result, "output") else str(result)

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            response_text = f"Error: {str(e)}"

        # Get trace_id from context for cost extraction
        trace_id = ctx.trace_id

    # Calculate latency
    latency_ms = Decimal(str((time.perf_counter() - start_time) * 1000))

    # Extract cost from LangFuse trace (AC3.1.4)
    if trace_id:
        try:
            flush_langfuse()  # Ensure trace is flushed before cost extraction
            cost = await extract_cost_from_langfuse(trace_id)
        except Exception as e:
            logger.debug(f"Could not extract cost from LangFuse trace: {e}")

    return response_text, cost, latency_ms, trace_id


async def run_agent(user_input: str):
    """Run the agent with the user input (backward compatible wrapper)."""
    response_text, cost, latency_ms, trace_id = await run_agent_with_tracking(user_input)

    # Log query and update session stats (AC3.1.3, AC3.1.5)
    session_id = st.session_state.session_id

    if st.session_state.session_db_available:
        await log_query(
            session_id=session_id,
            query_text=user_input,
            response_text=response_text,
            cost=cost,
            latency_ms=latency_ms,
            langfuse_trace_id=trace_id,
        )
    else:
        # Fallback to in-memory stats
        if st.session_state.in_memory_stats:
            st.session_state.in_memory_stats.update(cost, latency_ms)

    return response_text


# Get session stats for sidebar (AC3.1.6)
def get_cached_session_stats():
    """Get session stats with caching for performance."""
    session_id = st.session_state.session_id

    if st.session_state.session_db_available:
        stats = asyncio.run(get_session_stats(session_id))
        if stats:
            return stats

    # Fallback to in-memory stats
    if st.session_state.in_memory_stats:
        return st.session_state.in_memory_stats.to_dict()

    # Default empty stats
    return {
        "query_count": 0,
        "total_cost": Decimal("0.0"),
        "avg_latency_ms": Decimal("0.0"),
    }


# Sidebar
with st.sidebar:
    st.title("🤖 RAG Assistant")
    st.markdown("""
    This assistant uses **Docling** + **PydanticAI** + **PostgreSQL**
    to answer questions about your documents.
    """)

    # Session Statistics Section (AC3.1.6)
    st.divider()
    st.markdown("### 📊 Session Stats")

    stats = get_cached_session_stats()
    query_count = stats.get("query_count", 0)
    total_cost = stats.get("total_cost", Decimal("0.0"))
    avg_latency = stats.get("avg_latency_ms", Decimal("0.0"))

    # Format cost with appropriate precision
    # Ref: https://docs.streamlit.io/develop/api-reference/data/st.metric
    cost_float = float(total_cost)
    if cost_float == 0:
        cost_display = "$0.00"
    elif cost_float < 0.0001:
        cost_display = f"${cost_float:.6f}"
    elif cost_float < 0.01:
        cost_display = f"${cost_float:.4f}"
    else:
        cost_display = f"${cost_float:.2f}"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Queries", query_count)
    with col2:
        st.metric("Cost", cost_display)
    with col3:
        st.metric("Avg Latency", f"{float(avg_latency):.0f}ms")

    if not st.session_state.session_db_available:
        st.caption("⚠️ Stats in-memory only (DB unavailable)")

    st.divider()

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.markdown("### Documents")
    st.markdown("Place your documents in the `documents/` folder and run ingestion.")

    if st.button("Trigger Ingestion (API)"):
        with st.spinner("Triggering ingestion..."):
            try:
                client = RAGClient()
                # Run async call in sync context
                response = asyncio.run(client.trigger_ingestion())
                st.success(f"Ingestion started! Task ID: {response.get('task_id')}")
            except Exception as e:
                st.error(f"Failed to trigger ingestion: {e}")

# Main chat interface
st.title("📚 Knowledge Base Chat")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask something about your documents..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Run async agent in sync Streamlit context
            response_text = asyncio.run(run_agent(prompt))
            st.markdown(response_text)

    # Add assistant message to chat history
    st.session_state.messages.append({"role": "assistant", "content": response_text})
