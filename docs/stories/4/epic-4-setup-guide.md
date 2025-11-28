# Epic 4 Setup Guide: Production Infrastructure & CI/CD

**Date**: 2025-01-27  
**Epic ID**: 4  
**Status**: Implementation Guide

---

## Overview

Questa guida fornisce istruzioni step-by-step per implementare Epic 4: Production Infrastructure & CI/CD. Include setup di GitHub Actions workflows, configurazione TruffleHog secret scanning, integrazione CodeRabbit, e ottimizzazione Docker images.

**Prerequisites:**

- Repository GitHub con Actions abilitato
- Accesso a repository settings per configurazione secrets
- Docker installato localmente per testing
- Conoscenza base di YAML e GitHub Actions

---

## Step 1: Setup GitHub Actions CI/CD Workflow

### 1.1 Create Main CI Workflow

Crea il file `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install UV
        uses: astral-sh/setup-uv@v4
      - name: Install dependencies
        run: uv sync
      - name: Run Ruff linting
        run: uv run ruff check --output-format=github .
      - name: Run Ruff format check
        run: uv run ruff format --check .

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install UV
        uses: astral-sh/setup-uv@v4
      - name: Install dependencies
        run: uv sync
      - name: Run Mypy type checking
        run: uv run mypy core ingestion docling_mcp utils --ignore-missing-imports

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install UV
        uses: astral-sh/setup-uv@v4
      - name: Install dependencies
        run: uv sync
      - name: Run tests with coverage
        run: |
          uv run pytest \
            --cov=core \
            --cov=ingestion \
            --cov=docling_mcp \
            --cov=utils \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=70 \
            tests/
      - name: Upload coverage to artifacts
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage-report
          path: coverage.xml

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Build Streamlit Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile
          push: false
          tags: docling-rag-agent:test
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Build API Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.api
          push: false
          tags: docling-rag-agent-api:test
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Verify image sizes
        run: |
          STREAMLIT_SIZE=$(docker images docling-rag-agent:test --format "{{.Size}}" | sed 's/MB//' | head -1)
          API_SIZE=$(docker images docling-rag-agent-api:test --format "{{.Size}}" | sed 's/MB//' | head -1)
          echo "Streamlit image size: ${STREAMLIT_SIZE}MB"
          echo "API image size: ${API_SIZE}MB"
          # Note: Size verification logic may need adjustment based on actual output format

  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - name: Run TruffleHog OSS
        uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --results=verified,unknown --fail
```

### 1.2 Verify Workflow

1. Commit e push il workflow file
2. Verifica che il workflow appaia in GitHub Actions tab
3. Crea un test PR per triggerare il workflow
4. Verifica che tutti i job passino

**Troubleshooting:**

- Se linting fallisce: Esegui `ruff check .` localmente e fix warnings
- Se type-check fallisce: Esegui `mypy` localmente e fix errors
- Se test fallisce: Verifica che coverage sia >70% (`pytest --cov=... --cov-fail-under=70`)

---

## Step 2: Configure TruffleHog Secret Scanning

### 2.1 Verify Secret Scanning Job

Il job `secret-scan` è già configurato nel workflow CI. Verifica che:

- `fetch-depth: 0` è presente per scan completo della history
- `--fail` flag è presente per bloccare build se secrets rilevati
- `--results=verified,unknown` filtra falsi positivi

### 2.2 Test Secret Scanning

1. Crea un file di test con un fake secret:
   ```python
   # test_secret.py
   API_KEY = "sk-test1234567890abcdef"
   ```

2. Commit e push
3. Verifica che TruffleHog rilevi il secret e fallisca il build
4. Rimuovi il file di test

### 2.3 Configure Ignore Patterns (Optional)

Se necessario, crea `.trufflehogignore`:

```
# Ignore test files
tests/
*.test.py

# Ignore documentation
docs/
*.md
```

**References:**
- [TruffleHog GitHub Action](https://github.com/marketplace/actions/trufflehog-oss)
- [TruffleHog Documentation](https://github.com/trufflesecurity/trufflehog)

---

## Step 3: Setup CodeRabbit Integration

### 3.1 Install CodeRabbit GitHub App

1. Visit [CodeRabbit login page](https://app.coderabbit.ai)
2. Click "Login with GitHub"
3. Authorize CodeRabbit permissions
4. Select organization/repository
5. Choose repository access:
   - **All repositories**: Accesso completo
   - **Only select repositories**: Accesso limitato
6. Click "Install & Authorize"

### 3.2 Configure CodeRabbit

Crea/aggiorna `coderabbit.yaml` nella root del repository:

```yaml
# CodeRabbit Configuration
reviews:
  auto_review:
    enabled: true
    drafts: true
  high_level_summary: true
  profile: chill
  request_changes_workflow: false
  review_status: true

chat:
  art: false

language: en-US
```

### 3.3 Verify CodeRabbit Integration

1. Crea un test PR
2. Verifica che CodeRabbit appaia nei GitHub Checks
3. Verifica che CodeRabbit posti commenti di review
4. Verifica che high-level summary sia generato

**Troubleshooting:**

- Se CodeRabbit non appare: Verifica che GitHub App sia installato correttamente
- Se review non viene generata: Verifica `coderabbit.yaml` configuration
- Se permissions error: Verifica che GitHub App abbia i permessi corretti

**References:**
- [CodeRabbit GitHub Integration](https://docs.coderabbit.ai/platforms/github-com)
- [CodeRabbit Configuration Reference](https://docs.coderabbit.ai/reference/configuration)

---

## Step 4: Optimize Docker Images

### 4.1 Update Streamlit Dockerfile

Aggiorna `Dockerfile` con multi-stage build:

```dockerfile
# Build stage
FROM python:3.11-slim-bookworm AS builder

# Copy UV from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Copy source code
COPY . .

# Install project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Runtime stage
FROM python:3.11-slim-bookworm

# Copy UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY . .

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
```

### 4.2 Update API Dockerfile

Aggiorna `Dockerfile.api` con multi-stage build (pattern simile).

### 4.3 Test Docker Builds

1. Build localmente:
   ```bash
   docker build -t docling-rag-agent:test -f Dockerfile .
   docker build -t docling-rag-agent-api:test -f Dockerfile.api .
   ```

2. Verifica dimensioni:
   ```bash
   docker images docling-rag-agent:test
   docker images docling-rag-agent-api:test
   ```

3. Verifica che immagini siano <500MB

4. Test funzionalità:
   ```bash
   docker run -p 8501:8501 docling-rag-agent:test
   docker run -p 8000:8000 docling-rag-agent-api:test
   ```

**Troubleshooting:**

- Se build fallisce: Verifica che tutte le dipendenze siano in `pyproject.toml`
- Se immagine è ancora >500MB: Verifica che build dependencies siano rimosse nello stage finale
- Se runtime error: Verifica che virtual environment sia copiato correttamente

**References:**
- [Docker Multi-Stage Builds](https://pythonspeed.com/articles/smaller-python-docker-images/)
- [Python Docker Optimization](https://www.freecodecamp.org/news/build-slim-fast-docker-images-with-multi-stage-builds/)

---

## Step 5: Configure Coverage Threshold

### 5.1 Update pyproject.toml

Aggiungi/aggiorna sezione coverage:

```toml
[tool.coverage.run]
source = ["core", "ingestion", "docling_mcp", "utils"]
omit = [
    "tests/*",
    "*/__pycache__/*",
    "*/conftest.py",
    "*/test_*.py"
]

[tool.coverage.report]
fail_under = 70
precision = 2
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod"
]

[tool.coverage.html]
directory = "htmlcov"
```

### 5.2 Test Coverage Locally

```bash
# Run tests with coverage
uv run pytest --cov=core --cov=ingestion --cov=docling_mcp --cov=utils \
    --cov-report=html --cov-report=term-missing \
    --cov-fail-under=70 tests/

# View HTML report
open htmlcov/index.html
```

### 5.3 Verify CI/CD Enforcement

1. Crea un test PR con coverage <70%
2. Verifica che CI/CD fallisca con messaggio coverage insufficiente
3. Aggiungi test per aumentare coverage
4. Verifica che CI/CD passi

---

## Step 6: Setup Release Workflow

### 6.1 Create Release Workflow

Crea `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - name: Extract version
        id: version
        run: |
          VERSION=${GITHUB_REF#refs/tags/v}
          echo "version=$VERSION" >> $GITHUB_OUTPUT
          echo "Version: $VERSION"
      - name: Update CHANGELOG
        run: |
          DATE=$(date +%Y-%m-%d)
          VERSION=${{ steps.version.outputs.version }}
          echo "## [v$VERSION] - $DATE" >> CHANGELOG.md
          echo "" >> CHANGELOG.md
          echo "### Added" >> CHANGELOG.md
          echo "- Release v$VERSION" >> CHANGELOG.md
          echo "" >> CHANGELOG.md
      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ steps.version.outputs.version }}
          body_path: CHANGELOG.md
          draft: false
          prerelease: false
```

### 6.2 Test Release Workflow

1. Crea un tag di test:
   ```bash
   git tag v0.1.0-test
   git push origin v0.1.0-test
   ```

2. Verifica che release workflow sia triggerato
3. Verifica che GitHub Release sia creato
4. Verifica che CHANGELOG.md sia aggiornato
5. Rimuovi tag di test:
   ```bash
   git tag -d v0.1.0-test
   git push origin --delete v0.1.0-test
   ```

---

## Step 7: Verify Health Check Endpoints

### 7.1 Verify MCP Server Health Check

Health check endpoint è già implementato in `docling_mcp/http_server.py`. Verifica:

1. Start MCP server
2. Test endpoint:
   ```bash
   curl http://localhost:8080/health
   ```

3. Verifica risposta JSON:
   ```json
   {
     "status": "ok",
     "timestamp": 1234567890,
     "services": {
       "database": {"status": "up", "latency_ms": 5.2},
       "langfuse": {"status": "up", "latency_ms": 10.1},
       "embedder": {"status": "up", "latency_ms": 0.5}
     }
   }
   ```

### 7.2 Verify API Health Check

Health check endpoint è già implementato in `api/main.py`. Verifica:

1. Start API server
2. Test endpoint:
   ```bash
   curl http://localhost:8000/health
   ```

3. Verifica risposta JSON:
   ```json
   {
     "status": "ok",
     "timestamp": 1234567890
   }
   ```

### 7.3 Verify Streamlit Health Check

Streamlit ha health check nativo. Verifica:

1. Start Streamlit app
2. Test endpoint:
   ```bash
   curl http://localhost:8501/_stcore/health
   ```

3. Verifica risposta 200 OK

---

## Verification Checklist

### CI/CD Pipeline

- [ ] Lint job passa con zero warnings
- [ ] Type-check job passa con zero errors
- [ ] Test job passa con coverage >70%
- [ ] Build job passa con immagini <500MB
- [ ] Secret-scan job passa senza secrets rilevati

### CodeRabbit Integration

- [ ] CodeRabbit GitHub App installato
- [ ] `coderabbit.yaml` configurato correttamente
- [ ] CodeRabbit review automatica su PR
- [ ] High-level summary generato

### Docker Optimization

- [ ] Streamlit image <500MB
- [ ] API image <500MB
- [ ] Multi-stage build implementato
- [ ] Health checks funzionanti

### Release Workflow

- [ ] Release workflow creato
- [ ] CHANGELOG.md aggiornato automaticamente
- [ ] GitHub Release creato automaticamente

### Health Check Endpoints

- [ ] MCP server `/health` endpoint funzionante
- [ ] API `/health` endpoint funzionante
- [ ] Streamlit `/_stcore/health` endpoint funzionante

---

## Troubleshooting

### CI/CD Pipeline Failures

**Lint failures:**
- Run `ruff check .` locally
- Fix warnings
- Commit fixes

**Type-check failures:**
- Run `mypy` locally
- Fix type errors
- Commit fixes

**Test failures:**
- Run `pytest` locally
- Fix failing tests
- Increase coverage if needed
- Commit fixes

**Build failures:**
- Check Dockerfile syntax
- Verify dependencies in `pyproject.toml`
- Test build locally
- Fix issues

**Secret scan failures:**
- Review TruffleHog output
- Remove secrets from code
- Use GitHub Secrets for sensitive data
- Update `.trufflehogignore` if needed

### CodeRabbit Issues

**CodeRabbit not reviewing:**
- Verify GitHub App installation
- Check `coderabbit.yaml` configuration
- Verify repository permissions
- Check CodeRabbit dashboard for errors

### Docker Build Issues

**Image size too large:**
- Verify multi-stage build implemented
- Check that build dependencies removed in final stage
- Use `python:3.11-slim` base image
- Remove unnecessary files

**Build failures:**
- Check Dockerfile syntax
- Verify all dependencies in `pyproject.toml`
- Test build locally
- Check error messages

---

## Next Steps

Dopo aver completato Epic 4:

1. **Epic 5**: Testing & Quality Assurance
   - Setup testing infrastructure completa
   - Implement unit/integration/E2E tests
   - RAGAS evaluation suite

2. **Epic 6**: Project Structure Refactoring
   - Reorganize project structure
   - Clean up scattered files
   - Validate structure

---

**Document Status**: Implementation Guide  
**Last Updated**: 2025-01-27  
**Related Documents**: `tech-spec-epic-4.md`

