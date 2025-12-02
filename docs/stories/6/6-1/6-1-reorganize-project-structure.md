# Story 6.1: Reorganize Project Structure

Status: ready-for-dev

## Story

As a developer,  
I want a rigorous directory structure without scattered files in root,  
so that the project is maintainable and easy to navigate.

## Acceptance Criteria

1. **Given** the project root, **When** I check for files, **Then** no markdown files exist except README.md (pr_description_concise.md removed or moved to docs/ if present)
2. **Given** the project root, **When** I check for Python files, **Then** no temporary or debug files exist (temp_query.py, debug_mcp_tools.py removed or moved)
3. **Given** the scripts directory, **When** I inspect it, **Then** scripts are organized in subdirectories: `scripts/verification/`, `scripts/debug/`
4. **Given** the codebase, **When** I check organization, **Then** code is organized by responsibility: `docling_mcp/`, `core/`, `ingestion/`, `utils/`, `api/`
5. **Given** the MCP server, **When** I check location, **Then** it's in `docling_mcp/` module, not root
6. **Given** temporary directories, **When** I check root, **Then** documents*copy*\* directories are verified in .gitignore (already ignored, no physical removal needed if they contain data)
7. **Given** the metrics directory, **When** I check root, **Then** metrics directory is removed or relocated if not needed
8. **Given** generated directories, **When** I check .gitignore, **Then** site/ and node_modules/ are in .gitignore

## Tasks / Subtasks

- [ ] Task 1: Scan and identify files to reorganize (AC: 1, 2, 3, 7)

  - [ ] Scan root directory for markdown files (except README.md)
  - [ ] Scan root directory for Python temporary/debug files (temp*\*.py, debug*\*.py)
  - [ ] Identify scripts in scripts/ root that need subdirectory organization
  - [ ] Identify metrics directory status (needed or removable)
  - [ ] Document findings in task notes

- [ ] Task 2: Reorganize scripts directory (AC: 3)

  - [ ] Move `scripts/optimize_database.py` to `scripts/verification/` or create `scripts/database/` subdirectory
  - [ ] Move `scripts/test_cost_tracking.py` to `tests/integration/` or `scripts/testing/` (determine if test or utility)
  - [ ] Move `scripts/test_e2e_langfuse_timing.py` to `tests/e2e/` or `scripts/testing/` (determine if test or utility)
  - [ ] Move `scripts/test_mcp_performance.py` to `tests/performance/` or `scripts/testing/` (determine if test or utility)
  - [ ] Verify `scripts/debug/` contains `debug_mcp_tools.py` (already moved in previous epic)
  - [ ] Verify `scripts/verification/` contains all verify\_\*.py scripts

- [ ] Task 3: Remove or relocate temporary files from root (AC: 1, 2)

  - [ ] Remove `temp_query.py` from root (if exists)
  - [ ] Verify `debug_mcp_tools.py` is not in root (should be in scripts/debug/)
  - [ ] Remove `pr_description_concise.md` from root or move to docs/ (if exists)

- [ ] Task 4: Verify code organization by responsibility (AC: 4, 5)

  - [ ] Verify `docling_mcp/` module exists and contains MCP server (already done in Epic 2 Story 2.5)
  - [ ] Verify `core/` contains business logic RAG
  - [ ] Verify `ingestion/` contains document processing pipeline
  - [ ] Verify `utils/` contains shared utilities
  - [ ] Verify `api/` contains FastAPI service (if present)
  - [ ] Document any deviations from expected structure

- [ ] Task 5: Handle temporary/copy directories (AC: 6)

  - [ ] Verify `documents_copy_cooleman/` is in .gitignore (already ignored, no physical removal if contains data)
  - [ ] Verify `documents_copy_mia/` is in .gitignore (already ignored, no physical removal if contains data)
  - [ ] Document decision: keep ignored or merge into documents/ if data needed

- [ ] Task 6: Handle metrics directory (AC: 7)

  - [ ] Review contents of `metrics/` directory
  - [ ] Determine if directory is needed or can be removed
  - [ ] If needed, relocate to appropriate location (e.g., `docs/metrics/` or `scripts/metrics/`)
  - [ ] If not needed, remove directory

- [ ] Task 7: Verify .gitignore includes generated directories (AC: 8)

  - [ ] Verify `site/` is in .gitignore (MkDocs generated site)
  - [ ] Verify `node_modules/` is in .gitignore (npm dependencies)
  - [ ] Add entries if missing

- [ ] Task 8: Update imports after file moves (AC: 4)

  - [ ] Find all references to moved files using `grep -r "filename" --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml" .`
  - [ ] Update import statements in Python files
  - [ ] Update paths in documentation files
  - [ ] Update paths in CI/CD workflows if needed
  - [ ] Update paths in Dockerfile if needed

- [ ] Task 9: Clean up generated files (AC: 1, 2)

  - [ ] Remove `__pycache__/` directories: `find . -type d -name "__pycache__" -exec rm -r {} +`
  - [ ] Verify no temporary files remain in root

- [ ] Task 10: Testing and validation (AC: 1-8)
  - [ ] Run structure validation: verify root directory contains only authorized files
  - [ ] Run import validation: verify all imports work after reorganization
  - [ ] Run test suite: `uv run pytest tests/ -v` to verify functionality
  - [ ] Verify Docker builds: `docker-compose build` to ensure paths are correct
  - [ ] Document any issues found during validation

## Dev Notes

### Architecture Patterns and Constraints

**Project Structure Pattern:**

- Follow "Rigorous Project Structure" pattern from architecture [Source: docs/architecture.md#Project-Structure]
- Implement ADR-008 (Project Structure Mapping epics → directories) [Source: docs/architecture.md#Decision-Summary]
- Zero file sparsi in root directory [Source: docs/unified-project-structure.md#Root-Directory-Structure]

**File Organization Principles:**

- Organize by responsibility, not by file type [Source: docs/unified-project-structure.md#Module-Organization-by-Responsibility]
- Scripts organized in subdirectories by purpose [Source: docs/unified-project-structure.md#Scripts-Organization]
- Tests organized rigorously in tests/ subdirectories [Source: docs/testing-strategy.md]

**Git History Preservation:**

- Use `git mv` instead of `mv` to preserve git history [Source: docs/stories/6/tech-spec-epic-6.md#Non-Functional-Requirements]
- Verify history preserved with `git log --follow -- file.py` after moves [Source: docs/stories/6/tech-spec-epic-6.md#Integration-Points]

---

### Document Snippets (Extracted)

#### docs/unified-project-structure.md (Linee 23-45) - Authorized Root Files

```
docling-rag-agent/
├── README.md                    # ✅ Project documentation (user-facing)
├── CHANGELOG.md                 # ✅ Semantic versioning changelog
├── pyproject.toml               # ✅ Project configuration (UV)
├── uv.lock                      # ✅ Dependency lock file
├── docker-compose.yml           # ✅ Docker orchestration
├── Dockerfile                   # ✅ Streamlit container
├── Dockerfile.api               # ✅ API container (optional)
├── Dockerfile.mcp               # ✅ MCP server container (optional)
├── .env.example                 # ✅ Environment variables template
├── .gitignore                   # ✅ Git ignore rules
├── coderabbit.yaml              # ✅ CodeRabbit configuration
├── mkdocs.yml                   # ✅ MkDocs configuration
├── package.json                 # ✅ Node.js dependencies (MkDocs)
├── package-lock.json            # ✅ npm lock file
├── app.py                       # ✅ Streamlit UI entry point
└── [NO OTHER FILES]             # ❌ Tutti gli altri file devono essere in directory appropriate
```

#### docs/unified-project-structure.md (Linee 242-276) - Scripts Organization

```
scripts/
├── verification/                # Verification and health check scripts
│   ├── verify_api_endpoints.py
│   ├── verify_api.py
│   ├── verify_mcp_setup.py
│   └── verify_client_integration.py
├── debug/                       # Debug utilities
│   └── debug_mcp_tools.py
├── optimize_database.py         # ⚠️ Should be moved to appropriate subdirectory
├── test_cost_tracking.py        # ⚠️ Should be moved to tests/ or scripts/testing/
├── test_e2e_langfuse_timing.py  # ⚠️ Should be moved to tests/e2e/ or scripts/testing/
└── test_mcp_performance.py      # ⚠️ Should be moved to tests/performance/ or scripts/testing/

Rules:
- ✅ Scripts organized in subdirectories by purpose
- ✅ No temporary or debug scripts in root
- ⚠️ Current State: Some scripts exist in scripts/ root (should be moved - Epic 6)

Prohibited:
- ❌ temp_*.py files anywhere
- ❌ debug_*.py files in root (must be in scripts/debug/)
- ❌ test_*.py files in root (must be in tests/)
```

#### docs/unified-project-structure.md (Linee 717-741) - Areas Requiring Cleanup

```
⚠️ Needs Reorganization:

Scripts Directory:
- scripts/optimize_database.py → Should be moved to scripts/verification/ or scripts/database/
- scripts/test_cost_tracking.py → Should be moved to tests/integration/ or scripts/testing/
- scripts/test_e2e_langfuse_timing.py → Should be moved to tests/e2e/ or scripts/testing/
- scripts/test_mcp_performance.py → Should be moved to tests/performance/ or scripts/testing/

Root Directory (Temporary/Copy Directories):
- documents_copy_cooleman/ → Should be removed or moved to documents/ if needed
- documents_copy_mia/ → Should be removed or moved to documents/ if needed
- metrics → Should be moved to appropriate location or removed (if not needed)

Root Directory (Generated/Build Files - should be in .gitignore):
- site/ → MkDocs generated site (should be in .gitignore)
- node_modules/ → npm dependencies (should be in .gitignore)
```

#### .gitignore (Linee 1-29) - Current State

```
.env
.env.*
!.env.example

.venv
.pytest_cache
__pycache__
.claude
CLAUDE.md
ideal_documents
PRPs

/node_modules

#cartelle irrilevanti per proggetto
/documents_copy_cooleman
/documents_copy_mia

#.agent
#.bmad
#.cursor
.claude
.vscode

metrics
=3.0.0
.coverage
```

**Nota:** `site/` NON è presente in .gitignore - deve essere aggiunto (Task 7).

---

### Code References (File:Linea)

#### Scripts da Spostare

| File Attuale                                      | Destinazione            | Tipo           | Note                                         |
| ------------------------------------------------- | ----------------------- | -------------- | -------------------------------------------- |
| `scripts/optimize_database.py` (368 linee)        | `scripts/verification/` | Utility script | Database optimization con argparse CLI       |
| `scripts/test_cost_tracking.py` (70 linee)        | `scripts/testing/`      | Test utility   | Verifica LangFuse cost tracking (non pytest) |
| `scripts/test_mcp_performance.py` (197 linee)     | `scripts/testing/`      | Test utility   | Performance test MCP (non pytest)            |
| `scripts/test_e2e_langfuse_timing.py` (133 linee) | `scripts/testing/`      | Test utility   | E2E timing verification (non pytest)         |

#### Struttura Moduli Esistente (Verificata)

| Modulo                  | File                                                                                              | Responsabilità       |
| ----------------------- | ------------------------------------------------------------------------------------------------- | -------------------- |
| `core/`                 | `__init__.py`, `agent.py`, `rag_service.py`                                                       | Business logic RAG   |
| `docling_mcp/`          | `__init__.py`, `server.py`, `lifespan.py`, `metrics.py`, `health.py`, `http_server.py`, `tools/`  | MCP Server           |
| `ingestion/`            | `__init__.py`, `ingest.py`, `chunker.py`, `chunker_no_docling.py`, `embedder.py`                  | Document processing  |
| `utils/`                | `db_utils.py`, `models.py`, `providers.py`, `langfuse_streamlit.py`, `session_manager.py`         | Shared utilities     |
| `api/`                  | `main.py`, `models.py`                                                                            | FastAPI service      |
| `scripts/verification/` | `verify_api_endpoints.py`, `verify_api.py`, `verify_mcp_setup.py`, `verify_client_integration.py` | Verification scripts |
| `scripts/debug/`        | `debug_mcp_tools.py`                                                                              | Debug utilities      |

#### Dockerfile Paths da Verificare

**Dockerfile (Streamlit) - Linee 42-44:**

```dockerfile
COPY app.py ./
COPY client/ ./client/
COPY utils/ ./utils/
```

**Dockerfile.mcp - Linee 38-42:**

```dockerfile
COPY docling_mcp/ ./docling_mcp/
COPY core/ ./core/
COPY ingestion/ ./ingestion/
COPY utils/ ./utils/
COPY client/ ./client/
```

#### CI/CD Paths da Verificare

**.github/workflows/ci.yml - Linea 94:**

```yaml
run: uv run mypy core ingestion docling_mcp utils --ignore-missing-imports
```

**.github/workflows/ci.yml - Linee 135-138:**

```yaml
--cov=core \
--cov=ingestion \
--cov=docling_mcp \
--cov=utils \
```

---

### Interfaces / API Contracts

#### Script validate_structure.py (da creare)

**Input:**

- `root_dir: Path` - Directory root del progetto

**Output:**

- `List[str]` - Lista di violazioni trovate (vuota se struttura valida)

**Costanti:**

```python
ROOT_ALLOWED_FILES = [
    "README.md", "CHANGELOG.md", "pyproject.toml", "uv.lock",
    "docker-compose.yml", "Dockerfile", "Dockerfile.api", "Dockerfile.mcp",
    ".env.example", ".gitignore", "coderabbit.yaml", "mkdocs.yml",
    "package.json", "package-lock.json", "app.py"
]

ROOT_FORBIDDEN_PATTERNS = ["*.md", "temp_*.py", "debug_*.py", "*_copy_*", "test_*.py"]

REQUIRED_DIRECTORIES = [
    "docling_mcp/", "core/", "ingestion/", "utils/", "api/",
    "tests/", "scripts/", "docs/", "sql/"
]

REQUIRED_SCRIPT_SUBDIRECTORIES = ["scripts/verification/", "scripts/debug/"]
```

**CLI:**

```bash
uv run python scripts/validate_structure.py
# Exit code 0: struttura valida
# Exit code 1: violazioni trovate (lista stampata su stdout)
```

#### Script validate_imports.py (da creare)

**Input:**

- `root_dir: Path` - Directory root del progetto
- `project_root: Path` - Path per sys.path

**Output:**

- `List[Tuple[str, str]]` - Lista di (file_path, error_message)

**Logica:**

1. Aggiunge `project_root` a `sys.path`
2. Per ogni file `.py` (esclude `__pycache__`, `.venv`):
   - Parse AST per estrarre imports
   - Verifica che moduli progetto (`core`, `ingestion`, `docling_mcp`, `utils`, `api`, `client`) siano importabili
   - Verifica sintassi con `compile()`
3. Ritorna lista errori

**CLI:**

```bash
uv run python scripts/validate_imports.py
# Exit code 0: tutti gli imports validi
# Exit code 1: errori trovati (lista stampata su stdout)
```

---

### Dependencies (da pyproject.toml)

#### Runtime Dependencies (Base)

| Package         | Versione | Uso                     |
| --------------- | -------- | ----------------------- |
| `python-dotenv` | >=1.0.0  | Environment variables   |
| `asyncpg`       | >=0.30.0 | PostgreSQL async driver |
| `numpy`         | >=2.0.2  | Array operations        |
| `openai`        | >=1.0.0  | OpenAI API client       |
| `httpx`         | >=0.27.0 | HTTP client             |

#### MCP Dependencies (--extra mcp)

| Package             | Versione  | Uso                                |
| ------------------- | --------- | ---------------------------------- |
| `fastmcp`           | >=0.1.1   | MCP server framework               |
| `fastapi`           | >=0.109.0 | HTTP server per /health e /metrics |
| `pydantic-ai`       | >=0.7.4   | AI agent framework                 |
| `aiohttp`           | >=0.9.0   | Async HTTP                         |
| `docling[vlm]`      | >=2.55.0  | Document processing                |
| `aiofiles`          | >=24.1.0  | Async file I/O                     |
| `prometheus_client` | >=0.19.0  | Metrics export                     |
| `tenacity`          | >=8.2.0   | Retry logic                        |
| `pydantic`          | >=2.0.0   | Data models                        |
| `langfuse`          | >=3.0.0   | Observability (optional)           |

#### Dev Dependencies (--extra dev)

| Package                | Versione | Uso                    |
| ---------------------- | -------- | ---------------------- |
| `pytest`               | >=8.0.0  | Test framework         |
| `pytest-asyncio`       | >=0.23.0 | Async test support     |
| `pytest-cov`           | >=4.1.0  | Coverage reporting     |
| `pytest-mock`          | >=3.12.0 | Mocking                |
| `pytest-playwright`    | >=0.4.0  | E2E browser automation |
| `pytest-rerunfailures` | >=14.0   | Retry flaky tests      |
| `ruff`                 | >=0.8.0  | Linting                |
| `mypy`                 | >=1.13.0 | Type checking          |
| `ragas`                | >=0.1.0  | RAG evaluation         |
| `langchain-openai`     | >=0.1.0  | RAGAS dependency       |
| `datasets`             | >=2.14.0 | RAGAS dependency       |

#### Coverage Configuration (pyproject.toml Linee 126-147)

```toml
[tool.coverage.run]
source = ["core", "ingestion", "docling_mcp", "utils"]

[tool.coverage.report]
fail_under = 70
```

---

### Testing Standards

**Structure Validation:**

- Create validation script `scripts/validate_structure.py` per tech spec [Source: docs/stories/6/tech-spec-epic-6.md:84-133]
- Validate root directory contains only authorized files [Source: docs/stories/6/tech-spec-epic-6.md:342-349]
- Validate required directories exist and are organized correctly [Source: docs/stories/6/tech-spec-epic-6.md:448-454]

**Import Validation:**

- Create validation script `scripts/validate_imports.py` per tech spec [Source: docs/stories/6/tech-spec-epic-6.md:135-198]
- Verify all imports work correctly after reorganization (syntax + actual import resolution) [Source: docs/stories/6/tech-spec-epic-6.md:287-299]
- Run import validation after all file moves [Source: docs/stories/6/tech-spec-epic-6.md:248]

**Test Execution:**

- Run full test suite after reorganization: `uv run pytest tests/ -v` [Source: docs/stories/6/tech-spec-epic-6.md:249]
- Verify Docker builds: `docker-compose build` [Source: docs/stories/6/tech-spec-epic-6.md:250]
- Verify CI/CD paths work correctly [Source: docs/stories/6/tech-spec-epic-6.md:251]

**Test Ideas (from Tech Spec Traceability):**

| AC  | Test Idea                                                                  |
| --- | -------------------------------------------------------------------------- |
| AC1 | Scan root directory, verify no .md files except README.md                  |
| AC2 | Scan root directory, verify no temp*\*.py or debug*\*.py files             |
| AC3 | Inspect scripts/ directory, verify subdirectories verification/ and debug/ |
| AC4 | Verify code organization: docling_mcp/, core/, ingestion/, utils/, api/    |
| AC5 | Verify MCP server is in docling_mcp/ module, not root                      |
| AC6 | Verify documents*copy*\* directories in .gitignore                         |
| AC7 | Verify metrics directory removed or relocated                              |
| AC8 | Verify site/ and node_modules/ in .gitignore                               |

---

### References

- [Tech Spec Epic 6](../tech-spec-epic-6.md): Complete technical specification with ACs, workflows, and validation strategy
- [Epic 6 Requirements](../../epics.md#Epic-6-Project-Structure-Refactoring-&-Organization): Epic breakdown and story requirements
- [Architecture Document](../../architecture.md#Project-Structure): System architecture with project structure decisions
- [Unified Project Structure](../../unified-project-structure.md): Authoritative reference for directory organization
- [PRD Requirements](../../prd.md#Project-Structure-&-Organization): Functional requirements FR45-FR49
- [Testing Strategy](../../testing-strategy.md): Testing standards and organization patterns

## Dev Agent Record

### Context Reference

- docs/stories/6/6-1/6-1-reorganize-project-structure.context.xml

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

- **2025-12-02**: Story created from Epic 6 tech spec and epics.md
