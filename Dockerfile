# Dockerfile for Docling RAG Agent with Streamlit
FROM python:3.11-slim-bookworm

# Copy uv directly from its official image (best practice)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies including PostgreSQL client
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# uv optimizations:
# - Compile bytecode for faster startup
# - Use copy mode for libraries (more stable in Docker)
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 1. Copy ONLY dependency files first
COPY pyproject.toml uv.lock ./

# 2. Install dependencies
# --mount=type=cache: Keeps downloaded package cache between builds
# --frozen: Uses exact versions from lockfile
# --no-install-project: Installs only libraries, not your code yet
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# 3. ONLY NOW copy the rest of the source code
# If you modify code, Docker will restart from HERE, skipping dependency installation
COPY . .

# 4. Install current project and finalize sync
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose Streamlit port
EXPOSE 8501

# Health check for Streamlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
