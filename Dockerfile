# Dockerfile for Docling RAG Agent with Streamlit
# Multi-stage build for optimized image size < 500MB
# AC4.3.1, AC4.3.4, AC4.3.7, AC4.3.9

# ============================================================================
# BUILDER STAGE
# Install build dependencies and compile Python packages
# ============================================================================
FROM python:3.11-slim-bookworm AS builder

# Copy uv directly from its official image (best practice)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install build dependencies (NOT included in final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# uv optimizations:
# - Compile bytecode for faster startup
# - Use copy mode for libraries (more stable in Docker)
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# 1. Copy ONLY dependency files first
COPY pyproject.toml uv.lock ./

# 2. Install ONLY streamlit dependencies (no docling/ML models)
# --mount=type=cache: Keeps downloaded package cache between builds
# --frozen: Uses exact versions from lockfile
# --no-install-project: Installs only libraries, not your code yet
# --no-editable: Remove dependency on source code for multi-stage builds
# --extra streamlit: Install only streamlit group (lightweight)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-editable --extra streamlit

# 3. Copy ONLY necessary source code for Streamlit app
COPY app.py ./
COPY client/ ./client/
COPY utils/ ./utils/

# 4. Install current project and finalize sync
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable --extra streamlit

# ============================================================================
# RUNTIME STAGE
# Minimal image with only runtime dependencies
# ============================================================================
FROM python:3.11-slim AS runtime

# Install ONLY runtime dependencies (no build tools)
# - libpq5: PostgreSQL client library (runtime only, for asyncpg)
# - curl: for health checks
# NOTE: ffmpeg and postgresql-client removed - not used by Streamlit UI
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Environment variables for Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy ONLY necessary application code from builder stage
COPY --from=builder /app/app.py ./
COPY --from=builder /app/client ./client/
COPY --from=builder /app/utils ./utils/

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose Streamlit port
EXPOSE 8501

# Health check for Streamlit with extended start-period for network readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
