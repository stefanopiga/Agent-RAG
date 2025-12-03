# Unified Project Structure - docling-rag-agent

**Version:** 1.0  
**Last Updated:** 2025-01-27  
**Status:** Authoritative Reference

## Overview

Questo documento definisce la struttura directory standardizzata e unificata per il progetto `docling-rag-agent`. La struttura segue principi di organizzazione per responsabilità, separazione delle concerns, e scalabilità, garantendo coerenza architetturale e facilità di navigazione.

**Principi Fondamentali:**

- **Zero File Sparsi**: Nessun file markdown o Python temporaneo nella root (eccetto entry points essenziali)
- **Organizzazione per Responsabilità**: Directory organizzate per dominio funzionale, non per tipo di file
- **Separazione delle Concerns**: Business logic separata da I/O, observability separata da core logic
- **Scalabilità**: Struttura che supporta crescita senza refactoring massivo
- **Testabilità**: Organizzazione che facilita testing isolato e coverage tracking

---

## 1. Root Directory Structure

### 1.1 Authorized Root Files

**Solo i seguenti file sono autorizzati nella root:**

```
docling-rag-agent/
├── README.md                    # ✅ Project documentation (user-facing)
├── CHANGELOG.md                 # ✅ Semantic versioning changelog
├── pyproject.toml               # ✅ Project configuration (UV)
├── uv.lock                      # ✅ Dependency lock file
├── docker-compose.yml           # ✅ Docker orchestration
├── Dockerfile                   # ✅ Streamlit container
├── Dockerfile.api               # ✅ API container (optional)
├── .env.example                 # ✅ Environment variables template
├── .gitignore                   # ✅ Git ignore rules
├── coderabbit.yaml              # ✅ CodeRabbit configuration
├── mkdocs.yml                   # ✅ MkDocs configuration
├── package.json                 # ✅ Node.js dependencies (MkDocs)
├── app.py                       # ✅ Streamlit UI entry point
└── [NO OTHER FILES]             # ❌ Tutti gli altri file devono essere in directory appropriate
```

**Regole:**

- ❌ Nessun file markdown nella root (eccetto README.md)
- ❌ Nessun file Python temporaneo o di debug nella root
- ❌ Nessun file di configurazione sparsi (tutti in directory appropriate)
- ❌ Nessun file di documentazione nella root (tutti in `docs/`)

### 1.2 Root Directories

**Directory autorizzate nella root:**

```
docling-rag-agent/
├── docling_mcp/                 # MCP Server module (Epic 2)
├── core/                        # Core RAG business logic (Epic 2)
├── ingestion/                   # Document processing pipeline (Epic 1)
├── utils/                       # Shared utilities
├── api/                         # FastAPI service (Epic 4, optional)
├── tests/                       # Test suite (Epic 5)
├── scripts/                     # Utility scripts (Epic 4)
├── docs/                        # Documentation (Epic 1)
├── guide/                       # User guides (Epic 1)
├── sql/                         # Database schema and migrations
├── .github/                     # CI/CD workflows (Epic 4)
├── .bmad/                       # BMAD workflow configuration
├── documents/                   # Source documents for ingestion
└── [NO OTHER DIRECTORIES]       # ❌ Directory temporanee o non organizzate non autorizzate
```

---

## 2. Module Organization by Responsibility

### 2.1 Core Business Logic (`core/`)

**Responsibility:** Pure RAG business logic, decoupled from I/O and frameworks.

```
core/
├── __init__.py                  # Module exports
├── agent.py                     # PydanticAI agent wrapper (Streamlit integration)
└── rag_service.py               # Pure RAG logic (search, embedding, formatting)
```

**Rules:**

- ✅ Business logic only (no I/O operations)
- ✅ No framework dependencies (PydanticAI, Streamlit) in `rag_service.py`
- ✅ Functions are pure and testable
- ✅ Direct imports from `utils/` for shared resources

**Epic Mapping:** Epic 2 (MCP Observability)

### 2.2 MCP Server (`docling_mcp/`)

**Responsibility:** MCP server implementation with observability integration.

```
docling_mcp/
├── __init__.py                  # Module exports
├── server.py                    # FastMCP instance + tool definitions
├── lifespan.py                  # Server lifecycle (startup/shutdown)
├── metrics.py                   # Prometheus metrics definitions
├── health.py                    # Health check logic
├── http_server.py               # FastAPI /metrics and /health endpoints
└── tools/                       # MCP tool modules (for reference/documentation)
    ├── __init__.py
    ├── search.py                # query_knowledge_base, ask_knowledge_base
    ├── documents.py             # list_knowledge_base_documents, get_knowledge_base_document
    └── overview.py              # get_knowledge_base_overview
```

**Rules:**

- ✅ Standalone server (no dependency on `api/main.py`)
- ✅ Direct integration with `core/rag_service.py` (no HTTP proxy)
- ✅ Observability integrated (LangFuse, Prometheus)
- ✅ Tools organized by domain (search, documents, overview)

**Epic Mapping:** Epic 2 (MCP Observability)

**Note:** Directory named `docling_mcp/` to avoid conflict with FastMCP's `mcp` package.

### 2.3 Document Ingestion (`ingestion/`)

**Responsibility:** Document processing pipeline (parsing, chunking, embedding).

```
ingestion/
├── __init__.py                  # Module exports
├── ingest.py                    # DocumentIngestionPipeline orchestration
├── chunker.py                   # HybridChunker, SimpleChunker
└── embedder.py                  # EmbeddingGenerator (OpenAI with caching)
```

**Rules:**

- ✅ Processing logic only (no storage operations)
- ✅ Uses `utils/` for database operations
- ✅ Supports multiple document formats (PDF, DOCX, PPTX, etc.)

**Epic Mapping:** Epic 1 (Core RAG Baseline)

### 2.4 Shared Utilities (`utils/`)

**Responsibility:** Shared utilities used across modules.

```
utils/
├── __init__.py                  # Module exports
├── db_utils.py                  # AsyncPG connection pooling
├── models.py                    # Pydantic data models
└── providers.py                 # OpenAI provider configuration
```

**Rules:**

- ✅ No business logic (pure utilities)
- ✅ Reusable across all modules
- ✅ Connection pooling and resource management

**Epic Mapping:** All Epics (shared infrastructure)

### 2.5 API Service (`api/`)

**Responsibility:** FastAPI REST API service (optional, for scaling).

```
api/
├── __init__.py                  # Module exports
├── main.py                      # FastAPI app + endpoints
└── models.py                    # API request/response models
```

**Rules:**

- ✅ Optional module (Epic 4)
- ✅ Uses `core/rag_service.py` for business logic
- ✅ REST API endpoints for external clients

**Epic Mapping:** Epic 4 (Production Infrastructure)

---

## 3. Testing Infrastructure (`tests/`)

**Responsibility:** Complete test suite organized by test type.

```
tests/
├── __init__.py                  # Test package marker
├── conftest.py                  # Shared pytest fixtures
├── README.md                    # Test documentation
├── unit/                        # Unit tests (>70% coverage)
│   ├── test_rag_service.py
│   ├── test_embedder.py
│   ├── test_langfuse_integration.py
│   ├── test_performance_metrics.py
│   └── test_mcp_server_validation.py
├── integration/                 # Integration tests
│   ├── test_mcp_server_integration.py
│   └── test_observability_endpoints.py
├── e2e/                         # End-to-end tests (Playwright)
│   └── test_streamlit_workflow.py
└── fixtures/                    # Test fixtures + golden dataset
    └── golden_dataset.json      # 20+ query-answer pairs (RAGAS)
```

**Rules:**

- ✅ Rigorous organization: `unit/`, `integration/`, `e2e/`, `fixtures/`
- ✅ Test files: `test_*.py` or `*_test.py`
- ✅ Coverage target: >70% for core modules, >80% for critical modules
- ✅ Golden dataset in `fixtures/` for RAGAS evaluation

**Epic Mapping:** Epic 5 (Testing & Quality Assurance)

**Reference:** [Testing Strategy](./testing-strategy.md)

---

## 4. Scripts Organization (`scripts/`)

**Responsibility:** Utility scripts organized by purpose.

```
scripts/
├── verification/                # Verification and health check scripts
│   ├── verify_api_endpoints.py
│   ├── verify_mcp_setup.py
│   └── verify_client_integration.py
├── debug/                       # Debug utilities
│   └── debug_mcp_tools.py
└── [NO ROOT-LEVEL SCRIPTS]      # ❌ Tutti gli script devono essere in subdirectory
```

**Rules:**

- ✅ Scripts organized in subdirectories by purpose
- ✅ No temporary or debug scripts in root
- ✅ Performance test scripts can be in `scripts/` or `tests/performance/`

**Epic Mapping:** Epic 4 (Production Infrastructure), Epic 6 (Project Structure)

**Prohibited:**

- ❌ `temp_*.py` files anywhere
- ❌ `debug_*.py` files in root (must be in `scripts/debug/`)
- ❌ `test_*.py` files in root (must be in `tests/`)

---

## 5. Documentation Organization (`docs/`)

**Responsibility:** All project documentation centralized.

```
docs/
├── index.md                     # Documentation index (entry point)
├── architecture.md              # System architecture
├── coding-standards.md          # Code style guide
├── testing-strategy.md         # Testing strategy
├── unified-project-structure.md # This file
├── epics.md                     # Epic breakdown
├── prd.md                       # Product Requirements Document
├── project-overview.md          # Project overview
├── api-and-data-analysis.md     # API and data analysis
├── source-tree-analysis.md      # Source tree analysis
├── development-guide.md         # Development guide
├── stories/                     # Story documentation (BMAD workflow)
│   ├── sprint-status.yaml       # Story tracking
│   ├── 1/                       # Epic 1 stories
│   ├── 2/                       # Epic 2 stories
│   └── ...
└── documents/                   # Generated technical documents
    ├── deep-dive-ingestion.md
    ├── deep-dive-mcp.md
    └── ...
```

**Rules:**

- ✅ All markdown files in `docs/` (except README.md in root)
- ✅ BMAD workflow documentation in `docs/stories/`
- ✅ Generated documentation in `docs/documents/`
- ✅ User guides in `guide/` (separate from technical docs)

**Epic Mapping:** Epic 1 (Core RAG Baseline), Epic 6 (Project Structure)

**Reference:** [Coding Standards](./coding-standards.md) § Documentation Standards

---

## 6. User Guides (`guide/`)

**Responsibility:** User-facing guides and tutorials.

```
guide/
├── index.md                     # Guide index
├── development-guide.md         # Development patterns and walkthroughs
├── troubleshooting-guide.md     # Troubleshooting MCP server
└── api-reference/               # API reference documentation
    ├── index.md
    └── ...
```

**Rules:**

- ✅ User-facing documentation (not technical architecture)
- ✅ Step-by-step guides and tutorials
- ✅ API reference for external users

**Epic Mapping:** Epic 1 (Core RAG Baseline)

---

## 7. Database Schema (`sql/`)

**Responsibility:** Database schema, migrations, and optimization scripts.

```
sql/
├── schema.sql                   # PostgreSQL + PGVector schema
├── optimize_index.sql           # HNSW index optimization
└── removeDocuments.sql          # Cleanup scripts
```

**Rules:**

- ✅ All SQL scripts in `sql/` directory
- ✅ Schema files are versioned
- ✅ Migration scripts follow naming convention: `migration_YYYYMMDD_description.sql`

**Epic Mapping:** All Epics (database is core infrastructure)

---

## 8. CI/CD Configuration (`.github/`)

**Responsibility:** GitHub Actions workflows and CI/CD configuration.

```
.github/
└── workflows/
    ├── ci.yml                   # Lint, type-check, test, build
    └── release.yml               # Release automation
```

**Rules:**

- ✅ All CI/CD workflows in `.github/workflows/`
- ✅ Workflow files: `*.yml` or `*.yaml`
- ✅ No CI/CD configuration files in root

**Epic Mapping:** Epic 4 (Production Infrastructure)

---

## 9. Entry Points

### 9.1 Streamlit UI (`app.py`)

**Location:** Root directory (authorized entry point)

**Responsibility:** Streamlit UI entry point for web interface.

**Rules:**

- ✅ Single entry point for Streamlit app
- ✅ Imports from `core/agent.py` for RAG agent
- ✅ No business logic in entry point (delegates to core modules)

**Epic Mapping:** Epic 3 (Streamlit UI Observability)

### 9.2 MCP Server Entry Point

**Location:** `docling_mcp/server.py` (not in root)

**Responsibility:** MCP server entry point for Cursor IDE integration.

**Rules:**

- ✅ Entry point is `docling_mcp/server.py` (not root-level `mcp_server.py`)
- ✅ Uses FastMCP framework
- ✅ Standalone server (no external API dependency)

**Epic Mapping:** Epic 2 (MCP Observability)

---

## 10. Epic to Directory Mapping

| Epic                                  | Primary Directories                   | Responsibility                                 |
| ------------------------------------- | ------------------------------------- | ---------------------------------------------- |
| **Epic 1: Core RAG Baseline**         | `docs/`, `ingestion/`, `guide/`       | Documentation + ingestion pipeline             |
| **Epic 2: MCP Observability**         | `docling_mcp/`, `core/rag_service.py` | LangFuse integration + MCP standalone          |
| **Epic 3: Streamlit Observability**   | `app.py`, `core/agent.py`             | Session tracking + LangFuse tracing            |
| **Epic 4: Production Infrastructure** | `api/`, `scripts/`, `.github/`        | CI/CD, health checks, Docker optimization      |
| **Epic 5: Testing & QA**              | `tests/`                              | TDD infrastructure, unit/integration/E2E tests |
| **Epic 6: Project Structure**         | All directories                       | Cleanup + validation                           |

**Cross-Epic Directories:**

- `utils/`: Shared across all epics
- `sql/`: Database schema used by all epics
- `docs/`: Documentation for all epics

---

## 11. File Naming Conventions

### 11.1 Python Files

**Pattern:** `snake_case.py`

**Examples:**

- ✅ `rag_service.py`
- ✅ `mcp_server.py`
- ✅ `db_utils.py`
- ❌ `RAGService.py` (PascalCase not allowed)
- ❌ `rag-service.py` (hyphens not allowed)

**Reference:** [Coding Standards](./coding-standards.md) § Naming Conventions

### 11.2 Test Files

**Pattern:** `test_*.py` or `*_test.py`

**Examples:**

- ✅ `test_rag_service.py`
- ✅ `test_performance_metrics.py`
- ✅ `rag_service_test.py` (alternative)
- ❌ `testRAGService.py` (camelCase not allowed)

**Location:** Must be in `tests/unit/`, `tests/integration/`, or `tests/e2e/`

### 11.3 Configuration Files

**Pattern:** Descriptive name with extension

**Examples:**

- ✅ `pyproject.toml`
- ✅ `.env.example`
- ✅ `docker-compose.yml`
- ✅ `mkdocs.yml`
- ✅ `coderabbit.yaml`

**Location:** Root directory (authorized config files only)

### 11.4 Documentation Files

**Pattern:** `kebab-case.md` or `snake_case.md`

**Examples:**

- ✅ `coding-standards.md`
- ✅ `testing-strategy.md`
- ✅ `unified-project-structure.md`
- ✅ `api-and-data-analysis.md`

**Location:** Must be in `docs/` (except README.md in root)

---

## 12. Directory Naming Conventions

### 12.1 Python Modules

**Pattern:** `snake_case/`

**Examples:**

- ✅ `docling_mcp/`
- ✅ `core/`
- ✅ `ingestion/`
- ✅ `utils/`
- ❌ `DoclingMCP/` (PascalCase not allowed)
- ❌ `docling-mcp/` (hyphens not allowed)

### 12.2 Test Directories

**Pattern:** `snake_case/`

**Examples:**

- ✅ `tests/unit/`
- ✅ `tests/integration/`
- ✅ `tests/e2e/`
- ✅ `tests/fixtures/`

### 12.3 Script Directories

**Pattern:** `snake_case/`

**Examples:**

- ✅ `scripts/verification/`
- ✅ `scripts/debug/`
- ❌ `scripts/Verification/` (PascalCase not allowed)

---

## 13. Prohibited Patterns

### 13.1 Root Directory Prohibitions

**❌ Prohibited in Root:**

- Markdown files (except README.md)
- Python files (except `app.py` entry point)
- Temporary files (`temp_*.py`, `test_*.py`, `debug_*.py`)
- Configuration files sparsi (tutti in directory appropriate)
- Documentation files (tutti in `docs/`)

**Examples of Prohibited Files:**

```
❌ temp_query.py
❌ debug_mcp_tools.py (should be in scripts/debug/)
❌ test_performance.py (should be in tests/)
❌ architecture.md (should be in docs/)
❌ setup-guide.md (should be in docs/ or guide/)
```

### 13.2 Directory Prohibitions

**❌ Prohibited Directory Patterns:**

- Temporary directories (`temp/`, `tmp/`, `scratch/`)
- Unorganized directories (`misc/`, `other/`, `stuff/`)
- Duplicate functionality (`scriptsdebug/`, `scriptsverification/` - use subdirectories)

**Current Issues to Fix (Epic 6):**

- `scriptsdebug/` → Move to `scripts/debug/`
- `scriptsverification/` → Move to `scripts/verification/`
- `T/` → Remove (temporary directory)
- `=3.0.0` → Remove (temporary file)

### 13.3 File Organization Prohibitions

**❌ Prohibited Patterns:**

- Files sparsi per tipo invece di organizzazione per responsabilità
- Business logic mescolata con I/O operations
- Test files mescolati con source code
- Documentation sparsa in multiple directory

---

## 14. Migration Rules

### 14.1 Moving Files

**When moving files, ensure:**

1. ✅ Update all imports (use absolute imports)
2. ✅ Update documentation references
3. ✅ Update CI/CD paths if needed
4. ✅ Verify Docker builds still work
5. ✅ Run tests to verify functionality

**Example Migration:**

```bash
# Move debug script to proper location
mv debug_mcp_tools.py scripts/debug/

# Update imports in files that reference it
# Update documentation
# Verify tests pass
```

### 14.2 Adding New Files

**Before adding a new file, verify:**

1. ✅ File belongs in correct directory (check Epic mapping)
2. ✅ File follows naming conventions
3. ✅ File doesn't duplicate existing functionality
4. ✅ File is documented if it's a public API

**Decision Tree:**

```
New Python file?
├── Business logic? → core/ or docling_mcp/
├── Document processing? → ingestion/
├── Shared utility? → utils/
├── API endpoint? → api/
├── Test? → tests/unit/ or tests/integration/ or tests/e2e/
└── Script? → scripts/verification/ or scripts/debug/

New Markdown file?
├── User guide? → guide/
├── Technical doc? → docs/
└── Project README? → root (README.md only)
```

---

## 15. Validation Checklist

### 15.1 Structure Validation

**Run these checks before committing:**

- [ ] No markdown files in root (except README.md)
- [ ] No Python files in root (except `app.py`)
- [ ] No temporary files (`temp_*.py`, `test_*.py` in root)
- [ ] All scripts in `scripts/` subdirectories
- [ ] All tests in `tests/` subdirectories
- [ ] All documentation in `docs/` or `guide/`
- [ ] No duplicate directories (`scriptsdebug/`, `scriptsverification/`)
- [ ] All imports use absolute paths
- [ ] Docker builds successfully
- [ ] Tests pass after reorganization

### 15.2 Import Validation

**Verify imports after reorganization:**

```bash
# Check all Python files compile
python -m py_compile **/*.py

# Run tests to verify imports work
pytest tests/ -v
```

### 15.3 Documentation Validation

**Verify documentation references:**

- [ ] All file paths in docs are correct
- [ ] All cross-references work
- [ ] Architecture diagram reflects actual structure
- [ ] README.md references correct paths

---

## 16. Best Practices

### 16.1 Adding New Modules

**When adding a new module:**

1. Determine responsibility (check Epic mapping)
2. Choose appropriate directory (or create new if needed)
3. Follow naming conventions (`snake_case/`)
4. Add `__init__.py` for Python packages
5. Update `docs/architecture.md` with new module
6. Document module purpose in module docstring

### 16.2 Refactoring Structure

**When refactoring:**

1. Plan changes in Epic 6 Story 6.1
2. Update imports incrementally
3. Run tests after each change
4. Update documentation as you go
5. Verify CI/CD still works

### 16.3 Maintaining Clean Structure

**Ongoing maintenance:**

- Review root directory periodically (should be minimal)
- Move misplaced files immediately
- Update this document when structure changes
- Enforce structure in code reviews

---

## 17. Current Structure Status

### 17.1 Compliant Areas

**✅ Well Organized:**

- `core/` - Business logic properly separated
- `docling_mcp/` - MCP server well organized
- `tests/` - Test organization follows standards
- `docs/` - Documentation centralized
- `sql/` - Database scripts organized

### 17.2 Areas Requiring Cleanup (Epic 6)

**⚠️ Needs Reorganization:**

- `scriptsdebug/` → Should be `scripts/debug/`
- `scriptsverification/` → Should be `scripts/verification/`
- `T/` → Temporary directory, should be removed
- `=3.0.0` → Temporary file, should be removed
- `metrics` → Should be moved to appropriate location or removed
- Root-level scripts → Should be in `scripts/` subdirectories

**Reference:** [Epic 6 Story 6.1](./epics.md#Story-6.1-Reorganize-Project-Structure)

---

## 18. References

### Internal Documentation

- **[Architecture](./architecture.md)**: Complete system architecture with Project Structure section
- **[Coding Standards](./coding-standards.md)**: Code style guide including naming conventions
- **[Testing Strategy](./testing-strategy.md)**: Test organization standards
- **[Epic 6 Requirements](./epics.md#Epic-6-Project-Structure-Refactoring-&-Organization)**: Complete Epic 6 requirements
- **[Development Guide](./development-guide.md)**: Development workflow and structure patterns

### External References

- **Python Packaging Guide**: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- **pytest Test Organization**: https://docs.pytest.org/en/stable/explanation/goodpractices.html
- **FastMCP Project Structure**: https://github.com/jlowin/fastmcp

---

## 19. Changelog

- **2025-01-27**: Initial version based on existing codebase structure and Epic 6 requirements

---

## Appendix: Complete Directory Tree

```
docling-rag-agent/
├── README.md                        # ✅ Authorized root file
├── CHANGELOG.md                     # ✅ Authorized root file
├── pyproject.toml                   # ✅ Authorized root file
├── uv.lock                          # ✅ Authorized root file
├── docker-compose.yml               # ✅ Authorized root file
├── Dockerfile                       # ✅ Authorized root file
├── Dockerfile.api                   # ✅ Authorized root file
├── .env.example                     # ✅ Authorized root file
├── .gitignore                       # ✅ Authorized root file
├── coderabbit.yaml                  # ✅ Authorized root file
├── mkdocs.yml                       # ✅ Authorized root file
├── package.json                     # ✅ Authorized root file
├── app.py                           # ✅ Authorized entry point
│
├── docling_mcp/                     # Epic 2: MCP Server
│   ├── __init__.py
│   ├── server.py
│   ├── lifespan.py
│   ├── metrics.py
│   ├── health.py
│   ├── http_server.py
│   └── tools/
│       ├── __init__.py
│       ├── search.py
│       ├── documents.py
│       └── overview.py
│
├── core/                            # Epic 2: RAG Business Logic
│   ├── __init__.py
│   ├── agent.py
│   └── rag_service.py
│
├── ingestion/                       # Epic 1: Document Processing
│   ├── __init__.py
│   ├── ingest.py
│   ├── chunker.py
│   └── embedder.py
│
├── utils/                           # Shared Utilities
│   ├── __init__.py
│   ├── db_utils.py
│   ├── models.py
│   └── providers.py
│
├── api/                             # Epic 4: FastAPI Service (optional)
│   ├── __init__.py
│   ├── main.py
│   └── models.py
│
├── tests/                           # Epic 5: Testing Infrastructure
│   ├── __init__.py
│   ├── conftest.py
│   ├── README.md
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
│
├── scripts/                         # Epic 4: Utility Scripts
│   ├── verification/
│   └── debug/
│
├── docs/                            # Epic 1: Documentation
│   ├── index.md
│   ├── architecture.md
│   ├── coding-standards.md
│   ├── testing-strategy.md
│   ├── unified-project-structure.md
│   ├── epics.md
│   ├── prd.md
│   ├── stories/
│   └── documents/
│
├── guide/                           # Epic 1: User Guides
│   ├── index.md
│   ├── development-guide.md
│   ├── troubleshooting-guide.md
│   └── api-reference/
│
├── sql/                             # Database Schema
│   ├── schema.sql
│   ├── optimize_index.sql
│   └── removeDocuments.sql
│
├── .github/                         # Epic 4: CI/CD
│   └── workflows/
│
├── .bmad/                           # BMAD Configuration
│
└── documents/                       # Source Documents
```

**Files/Directories to Remove (Epic 6):**

- `scriptsdebug/` → Merge into `scripts/debug/`
- `scriptsverification/` → Merge into `scripts/verification/`
- `T/` → Remove (temporary)
- `=3.0.0` → Remove (temporary)
- `metrics` → Review and relocate or remove
