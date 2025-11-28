# Epic Technical Specification: Production Infrastructure & CI/CD

Date: 2025-01-27
Author: Stefano
Epic ID: 4
Status: Draft

---

## Overview

Epic 4 prepara il sistema per deployment production-ready su GitHub con CI/CD automatizzato, quality gates rigorosi, security scanning, e Docker optimization. Questo epic trasforma il progetto da sistema development-only a sistema production-ready con automated testing, linting, type checking, secret scanning, e code review AI-powered. L'implementazione segue best practices industry-standard per Python projects con GitHub Actions, integrazione TruffleHog OSS per secret scanning, CodeRabbit per code review automatica, e Docker multi-stage builds per ottimizzazione immagini. Epic 4 completa l'infrastruttura necessaria per deployment sicuro e affidabile, garantendo qualità del codice e prevenzione leak di credenziali attraverso automation completa.

## Objectives and Scope

**In-Scope:**

- GitHub Actions CI/CD workflow completo con lint, type-check, test, build validation
- Ruff linting automatizzato con zero warnings enforcement
- Mypy type checking automatizzato con zero errors enforcement
- Pytest con coverage threshold enforcement (>70%, fail build se non raggiunto)
- TruffleHog OSS secret scanning su ogni PR/push con build failure se secrets rilevati
- CodeRabbit integration verificata e configurata per code review automatica
- Health check endpoints completi per MCP server e API (verifica DB, LangFuse connectivity)
- Docker multi-stage optimization per immagini <500MB
- Release workflow per semantic versioning con CHANGELOG automation
- Coverage reporting automatico con threshold enforcement in CI/CD
- Docker build test in CI/CD per validazione immagini

**Out-of-Scope:**

- Deployment automation (Kubernetes, cloud providers) - Future epic
- Monitoring infrastructure (Prometheus, Grafana) - Già implementato in Epic 2
- Load testing o performance testing in CI/CD - Epic 5
- Multi-environment deployment (staging/production) - Future epic
- Database migration automation - Future epic

## System Architecture Alignment

Epic 4 si allinea direttamente con l'architettura documentata in `docs/architecture.md`, implementando le decisioni architetturali ADR-004 (Git Workflow & CI/CD) e ADR-005 (Prometheus Metrics and Health Check Endpoints). I componenti principali coinvolti sono:

- **`.github/workflows/`**: GitHub Actions workflows per CI/CD automation

  - `ci.yml`: Main CI pipeline (lint, type-check, test, build, secret-scan)
  - `release.yml`: Release automation su tag creation
  - `docs.yml`: Documentation deployment (già esistente)

- **`Dockerfile` e `Dockerfile.api`**: Multi-stage optimized builds per produzione

- **`docling_mcp/http_server.py`**: Health check endpoints già implementati (Story 4.2 parzialmente completa)

- **`pyproject.toml`**: Configuration per ruff, mypy, pytest, coverage threshold

- **`coderabbit.yaml`**: CodeRabbit configuration per code review automatica

L'epic implementa il pattern "Quality Gates Automation" per garantire che solo codice di qualità venga mergiato, con security scanning integrato e code review AI-powered.

## Detailed Design

### Services and Modules

| Service/Module                  | Responsibility              | Inputs                        | Outputs                                      | Owner    |
| ------------------------------- | --------------------------- | ----------------------------- | -------------------------------------------- | -------- |
| `.github/workflows/ci.yml`      | CI/CD pipeline automation   | Code changes, PR events       | Build status, test results, coverage report  | DevOps   |
| `.github/workflows/release.yml` | Release automation          | Git tags (v*.*.\*)            | GitHub Release, CHANGELOG update             | DevOps   |
| `Dockerfile` (Streamlit)        | Multi-stage optimized build | Source code, dependencies     | Docker image <500MB                          | DevOps   |
| `Dockerfile.api`                | Multi-stage optimized build | API source code, dependencies | Docker image <500MB                          | DevOps   |
| `docling_mcp/http_server.py`    | Health check endpoints      | HTTP requests                 | JSON health status                           | Epic 2   |
| `docling_mcp/health.py`         | Health check logic          | Service status checks         | HealthResponse object                        | Epic 2   |
| TruffleHog OSS Action           | Secret scanning             | Repository code               | Scan results, build failure if secrets found | Security |
| CodeRabbit GitHub App           | AI code review              | Pull requests                 | Code review comments, suggestions            | QA       |

### GitHub Actions CI/CD Pipeline

**Workflow Structure:**

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
          python-version: "3.11"
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
          python-version: "3.11"
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
          python-version: "3.11"
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
          STREAMLIT_SIZE=$(docker images docling-rag-agent:test --format "{{.Size}}" | sed 's/MB//')
          API_SIZE=$(docker images docling-rag-agent-api:test --format "{{.Size}}" | sed 's/MB//')
          if (( $(echo "$STREAMLIT_SIZE > 500" | bc -l) )); then
            echo "Streamlit image size ($STREAMLIT_SIZE MB) exceeds 500MB limit"
            exit 1
          fi
          if (( $(echo "$API_SIZE > 500" | bc -l) )); then
            echo "API image size ($API_SIZE MB) exceeds 500MB limit"
            exit 1
          fi

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

**Key Features:**

- **Parallel Jobs**: Lint, type-check, test, build, secret-scan eseguiti in parallelo per velocità
- **Caching**: UV cache e Docker build cache per performance
- **Coverage Enforcement**: Build fails se coverage < 70%
- **Secret Scanning**: TruffleHog OSS con `--fail` flag per bloccare PR con secrets
- **Docker Build Validation**: Verifica che immagini compilino correttamente e siano <500MB

**References:**

- [GitHub Actions Python Workflow](https://docs.github.com/en/actions/use-cases-and-examples/building-and-testing/building-and-testing-python)
- [TruffleHog GitHub Action](https://github.com/marketplace/actions/trufflehog-oss)

### TruffleHog OSS Secret Scanning

**Configuration:**

```yaml
- name: Run TruffleHog OSS
  uses: trufflesecurity/trufflehog@main
  with:
    extra_args: --results=verified,unknown --fail
```

**Best Practices:**

- `fetch-depth: 0` per scan completo della git history
- `--results=verified,unknown` per includere solo secrets verificati o sconosciuti (evita falsi positivi)
- `--fail` flag per bloccare build se secrets rilevati
- Scan su ogni PR e push per prevenzione leak

**Common Secrets Detected:**

- API keys (OpenAI, LangFuse)
- Database connection strings
- GitHub tokens
- SSH keys
- AWS credentials

**References:**

- [TruffleHog Documentation](https://github.com/trufflesecurity/trufflehog)
- [Running TruffleHog in GitHub Actions](https://trufflesecurity.com/blog/running-trufflehog-in-a-github-action)

### CodeRabbit Integration

**Setup Process:**

1. **GitHub App Installation:**

   - Visit [CodeRabbit login page](https://app.coderabbit.ai)
   - Click "Login with GitHub"
   - Authorize CodeRabbit permissions
   - Select organization/repository
   - Install GitHub App

2. **Configuration File (`coderabbit.yaml`):**

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

**Permissions Required:**

- **Read-only**: Actions, Checks, Discussions, Members, Metadata
- **Read-write**: Contents, Commit statuses, Issues, Pull requests

**Features:**

- Automatic code review su ogni PR
- AI-powered suggestions e best practices
- Integration con GitHub Checks API
- Actionlint per GitHub Actions workflow validation
- Security analysis automatica

**References:**

- [CodeRabbit GitHub Integration](https://docs.coderabbit.ai/platforms/github-com)
- [CodeRabbit Configuration Reference](https://docs.coderabbit.ai/reference/configuration)

### Health Check Endpoints

**MCP Server Health Check (`docling_mcp/http_server.py`):**

```python
@app.get("/health", tags=["Observability"])
async def health_endpoint():
    """
    Health check endpoint.

    Returns JSON response with:
    - status: "ok" | "degraded" | "down"
    - timestamp: Unix timestamp
    - services: Status of each service (database, langfuse, embedder)
    """
    health_response = await get_health_status()

    status_code = 200
    if health_response.status == "down":
        status_code = 503

    return JSONResponse(
        content=health_response.to_dict(),
        status_code=status_code
    )
```

**Status Logic:**

- **"ok"**: All services operational (DB, LangFuse, Embedder)
- **"degraded"**: LangFuse unavailable (non-critical, graceful degradation)
- **"down"**: Database or Embedder unavailable (critical dependencies)

**API Health Check (`api/main.py`):**

```python
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": time.time()}
```

**Streamlit Health Check:**

- Native endpoint: `/_stcore/health` (built-in Streamlit)
- Docker HEALTHCHECK già configurato nel Dockerfile

**CI/CD Health Check Validation:**

```yaml
- name: Test health endpoints
  run: |
    # Start services (docker-compose up -d)
    # Wait for services to be ready
    # Test /health endpoints
    curl -f http://localhost:8080/health || exit 1
    curl -f http://localhost:8000/health || exit 1
```

### Docker Multi-Stage Optimization

**Current Dockerfile Analysis:**

- **Streamlit Dockerfile**: Base `python:3.11-slim-bookworm`, non multi-stage
- **API Dockerfile**: Base `python:3.11-slim`, non multi-stage
- **Estimated Size**: Probabilmente >500MB (non verificato)

**Optimized Multi-Stage Pattern:**

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

**Optimization Techniques:**

- **Multi-stage build**: Separazione build-time e runtime dependencies
- **Slim base image**: `python:3.11-slim` invece di `python:3.11`
- **Layer caching**: `--mount=type=cache` per UV cache
- **Minimal runtime**: Solo runtime dependencies nello stage finale
- **No build tools**: Rimozione `build-essential`, `gcc` nello stage finale

**Expected Size Reduction:**

- **Before**: ~600-800MB (stima)
- **After**: <500MB (target)
- **Reduction**: ~30-40% size reduction

**References:**

- [Docker Multi-Stage Builds Guide](https://pythonspeed.com/articles/smaller-python-docker-images/)
- [Python Docker Optimization](https://www.freecodecamp.org/news/build-slim-fast-docker-images-with-multi-stage-builds/)

### Release Workflow

**Workflow Structure:**

```yaml
name: Release

on:
  push:
    tags:
      - "v*.*.*"

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
      - name: Update CHANGELOG
        run: |
          # Add release entry to CHANGELOG.md
          # Format: ## [v$VERSION] - $(date +%Y-%m-%d)
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

**Semantic Versioning:**

- Format: `vMAJOR.MINOR.PATCH` (e.g., `v1.2.3`)
- CHANGELOG.md automatico update
- GitHub Release creation con notes

### Coverage Threshold Configuration

**pyproject.toml Configuration:**

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

**CI/CD Enforcement:**

```yaml
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
```

**Coverage Reporting:**

- XML report per CI/CD integration
- Terminal report per developer feedback
- HTML report per local development (`htmlcov/`)

### Data Models and Contracts

**GitHub Actions Workflow Models:**

- **Workflow Event**: `pull_request`, `push` events con branch filters (`main`, `develop`)
- **Job Status**: `success`, `failure`, `cancelled` con exit codes
- **Artifact Model**: Coverage report XML (`coverage.xml`) con upload/download

**Docker Image Models:**

- **Image Tag**: Format `docling-rag-agent:test` per CI/CD builds
- **Size Constraint**: Maximum 500MB per immagine (validato in CI/CD)
- **Health Check**: HTTP endpoint response con status code 200/503

**Health Check Response Model:**

```python
class HealthResponse:
    status: Literal["ok", "degraded", "down"]
    timestamp: float
    services: Dict[str, ServiceStatus]

class ServiceStatus:
    status: Literal["ok", "down"]
    message: Optional[str]
```

**Coverage Report Model:**

- **Format**: XML (Cobertura format) per CI/CD integration
- **Threshold**: Minimum 70% coverage enforced
- **Sources**: `core`, `ingestion`, `docling_mcp`, `utils`

**Release Model:**

- **Version Format**: Semantic versioning `vMAJOR.MINOR.PATCH`
- **CHANGELOG Entry**: `## [vVERSION] - YYYY-MM-DD` format
- **GitHub Release**: Tag name, release name, body from CHANGELOG.md

### APIs and Interfaces

**GitHub Actions API:**

- **Workflow Triggers**: `pull_request`, `push` events
- **Job Execution**: Parallel jobs con shared artifacts
- **Status Reporting**: GitHub Checks API integration

**Docker Build API:**

- **Build Context**: Repository root directory
- **Cache Strategy**: GitHub Actions cache (`type=gha`) per layer caching
- **Image Validation**: Size check via `docker images` command

**Health Check HTTP API:**

- **MCP Server**: `GET /health` → JSON response con status, timestamp, services
- **API Server**: `GET /health` → JSON response con status, timestamp
- **Streamlit**: `GET /_stcore/health` → HTTP 200 OK (built-in)

**TruffleHog OSS API:**

- **Scan Input**: Repository code (full git history con `fetch-depth: 0`)
- **Scan Output**: Verified/unknown secrets detection
- **Failure Mode**: Exit code 1 se secrets rilevati (`--fail` flag)

**CodeRabbit GitHub App API:**

- **Trigger**: Pull request creation/update
- **Review Output**: Code review comments via GitHub API
- **Status Integration**: GitHub Checks API per review status

**Coverage Reporting API:**

- **Input**: pytest execution con `--cov` flags
- **Output Formats**: XML (CI/CD), terminal (developer), HTML (local)
- **Threshold Enforcement**: `--cov-fail-under=70` per build failure

### Workflows and Sequencing

### CI/CD Pipeline Flow

```
Pull Request Created
  ├─> Trigger: pull_request event
  │
  ├─> Job: lint (parallel)
  │   ├─> Checkout code
  │   ├─> Setup Python 3.11
  │   ├─> Install UV
  │   ├─> Install dependencies
  │   ├─> Run Ruff linting
  │   └─> Run Ruff format check
  │
  ├─> Job: type-check (parallel)
  │   ├─> Checkout code
  │   ├─> Setup Python 3.11
  │   ├─> Install UV
  │   ├─> Install dependencies
  │   └─> Run Mypy type checking
  │
  ├─> Job: test (parallel)
  │   ├─> Checkout code
  │   ├─> Setup Python 3.11
  │   ├─> Install UV
  │   ├─> Install dependencies
  │   ├─> Run pytest with coverage
  │   └─> Upload coverage report
  │
  ├─> Job: build (parallel)
  │   ├─> Checkout code
  │   ├─> Setup Docker Buildx
  │   ├─> Build Streamlit image
  │   ├─> Build API image
  │   └─> Verify image sizes <500MB
  │
  └─> Job: secret-scan (parallel)
      ├─> Checkout code (full history)
      └─> Run TruffleHog OSS scan
          └─> Fail if secrets detected

All Jobs Complete
  ├─> If all pass: PR ready for merge
  └─> If any fail: PR blocked, fix required
```

### Release Workflow Flow

```
Git Tag Created (v*.*.*)
  ├─> Trigger: push tags event
  │
  ├─> Extract version from tag
  │
  ├─> Update CHANGELOG.md
  │   └─> Add release entry with date
  │
  ├─> Create GitHub Release
  │   ├─> Tag name: v*.*.*
  │   ├─> Release name: Release *.*.*
  │   ├─> Body: CHANGELOG.md content
  │   └─> Draft: false
  │
  └─> Release published
      └─> Notification sent
```

### CodeRabbit Review Flow

```
Pull Request Created
  ├─> CodeRabbit GitHub App triggered
  │
  ├─> Analyze code changes
  │   ├─> Code quality review
  │   ├─> Best practices check
  │   ├─> Security analysis
  │   └─> Actionlint (GitHub Actions validation)
  │
  ├─> Generate review comments
  │   ├─> Line-by-line suggestions
  │   ├─> High-level summary
  │   └─> Code improvement suggestions
  │
  └─> Post review comments on PR
      └─> GitHub Checks API status updated
```

## Non-Functional Requirements

### Performance

- **CI/CD Pipeline Duration**: <15 minutes per pipeline completa
- **Docker Build Time**: <5 minutes per immagine (con cache)
- **Test Execution Time**: <10 minutes per test suite completa
- **Secret Scan Duration**: <2 minutes per repository scan

### Reliability

- **Build Success Rate**: >95% per commits validi
- **False Positive Rate**: <5% per TruffleHog secret scanning
- **Coverage Accuracy**: Coverage report accurato entro ±2%

### Security

- **Secret Detection**: 100% coverage su tutti i file nel repository
- **Zero Secrets in History**: TruffleHog scan completo della git history
- **Access Control**: Solo maintainers possono bypass CI/CD checks

### Maintainability

- **Workflow Documentation**: Tutti i workflow documentati inline
- **Configuration Management**: Tutte le configurazioni in file versionati
- **Error Messages**: Messaggi di errore chiari e actionable

### Observability

- **CI/CD Status**: GitHub Actions status badges per build visibility
- **Coverage Reporting**: Automatic coverage report upload come artifact
- **Build Logs**: Detailed logs per ogni job step con error context
- **Health Check Monitoring**: Health endpoints verificabili via CI/CD tests

## Dependencies and Integrations

**External Services:**

- **GitHub Actions**: CI/CD pipeline execution platform
- **TruffleHog OSS**: Secret scanning service (GitHub Action)
- **CodeRabbit**: AI-powered code review service (GitHub App)
- **Docker Hub / GitHub Container Registry**: Container image storage (opzionale per push)

**Internal Dependencies:**

- **Epic 2**: Health check endpoints già implementati (`docling_mcp/http_server.py`, `docling_mcp/health.py`)
- **Epic 5**: Test infrastructure per coverage enforcement (pytest, pytest-cov)
- **Epic 1**: README.md e documentazione per setup instructions

**Framework/Libraries:**

- **GitHub Actions**: Workflow automation (`actions/checkout@v5`, `actions/setup-python@v5`, `astral-sh/setup-uv@v4`)
- **Docker**: Container build (`docker/setup-buildx-action@v3`, `docker/build-push-action@v5`)
- **Ruff**: Python linter (`ruff check`, `ruff format`)
- **Mypy**: Type checker (`mypy`)
- **Pytest**: Test framework (`pytest`, `pytest-cov`)
- **Coverage.py**: Coverage measurement (`coverage`)

**Configuration Files:**

- `.github/workflows/ci.yml`: Main CI pipeline configuration
- `.github/workflows/release.yml`: Release automation configuration
- `coderabbit.yaml`: CodeRabbit configuration
- `pyproject.toml`: Ruff, Mypy, Coverage threshold configuration
- `Dockerfile`: Streamlit container build configuration
- `Dockerfile.api`: API container build configuration

**Environment Variables (GitHub Secrets):**

- `GITHUB_TOKEN`: Automatic token per GitHub API access (non richiesto manualmente)
- `OPENAI_API_KEY`: Opzionale per test che richiedono API key (mock in CI/CD)
- `LANGFUSE_PUBLIC_KEY`: Opzionale per test LangFuse integration (mock in CI/CD)
- `DATABASE_URL`: Opzionale per test database (test database in CI/CD)

**Note:** Tutti i test devono usare mocks per evitare dipendenze esterne in CI/CD.

## Acceptance Criteria (Authoritative)

**AC1**: GitHub Actions CI/CD workflow esegue lint, type-check, test, build, secret-scan su ogni PR e push a `main`/`develop`

**AC2**: Ruff linting passa con zero warnings (build failure se warnings presenti)

**AC3**: Mypy type checking passa con zero errors (build failure se errors presenti)

**AC4**: Pytest esegue con coverage >70% enforcement (build failure se coverage <70%)

**AC5**: TruffleHog OSS secret scanning esegue su ogni PR/push con build failure se secrets rilevati

**AC6**: CodeRabbit GitHub App installato e configurato con `coderabbit.yaml` per code review automatica

**AC7**: Health check endpoint `/health` disponibile su MCP server con JSON response (status, timestamp, services)

**AC8**: Health check endpoint `/health` disponibile su API server con JSON response (status, timestamp)

**AC9**: Docker build test in CI/CD valida che immagini compilino correttamente

**AC10**: Docker build test in CI/CD valida che immagini siano <500MB

**AC11**: Docker multi-stage optimization implementato per `Dockerfile` (Streamlit)

**AC12**: Docker multi-stage optimization implementato per `Dockerfile.api` (API)

**AC13**: Release workflow triggerato su git tag creation (`v*.*.*`)

**AC14**: Release workflow aggiorna CHANGELOG.md automaticamente con release entry

**AC15**: Release workflow crea GitHub Release con tag name, release name, e CHANGELOG body

**AC16**: Coverage report XML generato automaticamente in CI/CD e uploadato come artifact

## Traceability Mapping

| AC   | Spec Section                          | Component/API                   | Test Idea                                                                       |
| ---- | ------------------------------------- | ------------------------------- | ------------------------------------------------------------------------------- |
| AC1  | Detailed Design → Workflows           | `.github/workflows/ci.yml`      | Manual test: creare PR, verificare che tutti i job eseguano                     |
| AC2  | Detailed Design → Workflows           | Ruff linting job                | Manual test: aggiungere warning, verificare build failure                       |
| AC3  | Detailed Design → Workflows           | Mypy type-check job             | Manual test: aggiungere type error, verificare build failure                    |
| AC4  | Detailed Design → Workflows           | Pytest coverage job             | Manual test: ridurre coverage <70%, verificare build failure                    |
| AC5  | Detailed Design → Workflows           | TruffleHog secret-scan job      | Manual test: aggiungere secret nel codice, verificare build failure             |
| AC6  | Detailed Design → APIs and Interfaces | CodeRabbit GitHub App           | Manual test: creare PR, verificare code review automatica                       |
| AC7  | Detailed Design → APIs and Interfaces | `docling_mcp/http_server.py`    | Integration test: `curl http://localhost:8080/health`, verificare JSON response |
| AC8  | Detailed Design → APIs and Interfaces | `api/main.py`                   | Integration test: `curl http://localhost:8000/health`, verificare JSON response |
| AC9  | Detailed Design → Workflows           | Docker build job                | CI/CD test: verificare che build completi senza errori                          |
| AC10 | Detailed Design → Workflows           | Docker build job                | CI/CD test: verificare che size check passi (<500MB)                            |
| AC11 | Detailed Design → Workflows           | `Dockerfile`                    | Manual test: build immagine, verificare multi-stage optimization                |
| AC12 | Detailed Design → Workflows           | `Dockerfile.api`                | Manual test: build immagine, verificare multi-stage optimization                |
| AC13 | Detailed Design → Workflows           | `.github/workflows/release.yml` | Manual test: creare git tag `v1.0.0`, verificare workflow trigger               |
| AC14 | Detailed Design → Workflows           | Release workflow                | Manual test: verificare CHANGELOG.md aggiornato dopo tag creation               |
| AC15 | Detailed Design → Workflows           | Release workflow                | Manual test: verificare GitHub Release creato con contenuto corretto            |
| AC16 | Detailed Design → Workflows           | Coverage reporting job          | CI/CD test: verificare artifact `coverage-report` uploadato                     |

## Risks, Assumptions, Open Questions

**Risk R1**: CI/CD pipeline potrebbe fallire per falsi positivi di TruffleHog

- **Mitigation**: Configurare `.trufflehogignore` per pattern noti, usare `--results=verified,unknown` per ridurre falsi positivi

**Risk R2**: Docker build potrebbe superare limite 500MB nonostante multi-stage optimization

- **Mitigation**: Analizzare layer sizes con `docker history`, ottimizzare ulteriormente rimuovendo dipendenze non necessarie

**Risk R3**: Coverage threshold 70% potrebbe essere troppo alto per codice legacy

- **Mitigation**: Valutare coverage attuale prima di enforcement, aggiustare threshold se necessario (minimo 60%)

**Risk R4**: GitHub Actions minutes potrebbero esaurirsi con pipeline frequenti

- **Mitigation**: Ottimizzare caching, ridurre frequenza di trigger se necessario, considerare self-hosted runners

**Assumption A1**: GitHub repository ha Actions abilitato e sufficienti minutes disponibili

- **Validation**: Verificare GitHub Actions settings e usage limits

**Assumption A2**: CodeRabbit GitHub App può essere installato senza restrizioni organizzazionali

- **Validation**: Verificare permissions GitHub App e approvazione organizzazione se necessario

**Assumption A3**: Health check endpoints già implementati in Epic 2 funzionano correttamente

- **Validation**: Testare health endpoints prima di integrazione CI/CD

**Question Q1**: Preferire GitHub Actions cache o Docker layer cache per performance?

- **Decision**: Usare entrambi: GitHub Actions cache per UV dependencies, Docker cache per layer optimization

**Question Q2**: Eseguire Docker build test su ogni PR o solo su merge?

- **Decision**: Su ogni PR per early detection di problemi Docker, ma con cache per performance

**Question Q3**: Coverage threshold enforcement deve essere rigido o warning-only inizialmente?

- **Decision**: Rigido (fail build) per garantire qualità, ma valutare coverage attuale prima di enforcement

## Test Strategy Summary

**Test Levels:**

1. **CI/CD Integration Tests**: Validazione workflow execution, job success, artifact upload
2. **Docker Build Tests**: Validazione build success, image size, health check functionality
3. **Health Check Tests**: Validazione endpoint response, status logic, error handling
4. **Manual Tests**: Validazione CodeRabbit review, release workflow, CHANGELOG update

**Test Coverage:**

- **Workflow Execution**: 100% dei job devono eseguire correttamente
- **Build Validation**: 100% dei Docker builds devono completare senza errori
- **Health Endpoints**: 100% degli endpoint devono rispondere correttamente
- **Coverage Enforcement**: Coverage threshold >70% enforced su tutti i moduli

**Test Frameworks:**

- **GitHub Actions**: Workflow execution e job validation
- **Docker**: Build test e image size validation
- **curl/httpie**: Health endpoint testing
- **Manual Testing**: CodeRabbit review, release workflow validation

**Critical Test Cases:**

1. CI/CD pipeline completa esegue in <15 minuti
2. Docker images compilano correttamente e sono <500MB
3. Health check endpoints rispondono con status corretto
4. Coverage enforcement blocca PR se coverage <70%
5. Secret scanning blocca PR se secrets rilevati
6. Release workflow crea GitHub Release correttamente

## Implementation Notes

### Prerequisites

- GitHub repository con Actions abilitato
- CodeRabbit GitHub App installato e configurato
- Accesso a GitHub Secrets per configurazione (se necessario)
- Docker Buildx abilitato per multi-platform builds (opzionale)

### Configuration Files

**Required Files:**

- `.github/workflows/ci.yml`: Main CI pipeline
- `.github/workflows/release.yml`: Release automation
- `coderabbit.yaml`: CodeRabbit configuration
- `pyproject.toml`: Coverage threshold configuration (update)

**Optional Files:**

- `.github/workflows/docker-build.yml`: Separate Docker build workflow (se necessario)
- `.trufflehogignore`: TruffleHog ignore patterns (se necessario)

### Rollback Plan

- **Workflow Failure**: Fix immediato richiesto, PR blocked
- **Secret Detection**: Rimozione secret + force push per pulizia history
- **Coverage Drop**: Fix test coverage prima di merge
- **Docker Build Failure**: Fix Dockerfile, rebuild

## References

### Official Documentation

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Building and Testing Python](https://docs.github.com/en/actions/use-cases-and-examples/building-and-testing/building-and-testing-python)
- [GitHub Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

### Tools Documentation

- [TruffleHog GitHub Action](https://github.com/marketplace/actions/trufflehog-oss)
- [TruffleHog Documentation](https://github.com/trufflesecurity/trufflehog)
- [CodeRabbit GitHub Integration](https://docs.coderabbit.ai/platforms/github-com)
- [CodeRabbit Configuration Reference](https://docs.coderabbit.ai/reference/configuration)

### Best Practices

- [Docker Multi-Stage Builds](https://pythonspeed.com/articles/smaller-python-docker-images/)
- [Python Docker Optimization](https://www.freecodecamp.org/news/build-slim-fast-docker-images-with-multi-stage-builds/)
- [GitHub Actions Best Practices](https://docs.github.com/en/actions/learn-github-actions/best-practices)

### Related Epic Documentation

- Epic 2: MCP Server Observability (health check endpoints già implementati)
- Epic 3: Streamlit UI Observability (test integration in CI/CD)
- Epic 5: Testing & Quality Assurance (coverage threshold enforcement)

---

**Document Status**: Draft  
**Last Updated**: 2025-01-27  
**Next Review**: Before Epic 4 implementation kickoff
