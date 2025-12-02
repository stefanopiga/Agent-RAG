# Epic Technical Specification: Project Structure Refactoring & Organization

Date: 2025-01-27
Author: Stefano
Epic ID: 6
Status: Draft

---

## Overview

Epic 6 implementa una struttura directory rigorosa eliminando file sparsi nella root e organizzando il codice per responsabilità, seguendo best practices FastMCP e TDD. Questo epic completa la trasformazione del progetto da prototipo a sistema production-ready attraverso organizzazione rigorosa che migliora mantenibilità, testabilità e scalabilità. L'implementazione garantisce che tutti i file siano in directory appropriate, gli script siano organizzati per categoria, e zero file temporanei o di debug esistano nella root directory. Epic 6 si basa su Epic 1 (documentazione centralizzata) e Epic 2 (MCP server refactored) per completare l'organizzazione strutturale necessaria per mantenibilità a lungo termine.

## Objectives and Scope

**In-Scope:**

- Eliminazione di tutti i file markdown dalla root directory (eccetto README.md, incluso pr_description_concise.md se presente)
- Rimozione o spostamento di file Python temporanei/debug dalla root (temp_query.py, debug_mcp_tools.py)
- Riorganizzazione scripts in sottodirectory: `scripts/verification/`, `scripts/debug/`
- Organizzazione codice per responsabilità: `docling_mcp/`, `core/`, `ingestion/`, `utils/`, `api/`
- Verifica che MCP server sia in modulo `docling_mcp/` (già completato in Epic 2 Story 2.5)
- Verifica directory temporanee/copy dalla root (documents*copy_cooleman/, documents_copy_mia/, metrics/) - documents_copy*\* sono già in .gitignore quindi verificare che siano ignorati, non rimossi fisicamente se contengono dati
- Validazione struttura: verifica imports funzionano dopo riorganizzazione
- Aggiornamento documentazione struttura progetto per riflettere organizzazione finale
- Verifica CI/CD paths funzionano dopo riorganizzazione
- Verifica Docker builds funzionano dopo riorganizzazione

**Out-of-Scope:**

- Refactoring codice esistente (solo riorganizzazione file/directory)
- Modifica logica business (solo struttura organizzativa)
- Creazione nuovi moduli o componenti (solo riorganizzazione esistente)
- Modifica dipendenze o configurazioni (solo aggiornamento paths se necessario)

## System Architecture Alignment

Epic 6 si allinea direttamente con l'architettura documentata in `docs/architecture.md`, implementando la decisione architetturale ADR-008 (Project Structure Mapping epics → directories con convenzioni). I componenti principali coinvolti sono:

- **Root Directory**: Solo file essenziali (README.md, pyproject.toml, docker-compose.yml, app.py entry point, file di configurazione autorizzati)

- **`docling_mcp/`**: MCP Server già organizzato (Epic 2 Story 2.5) - verifica struttura corretta

- **`core/`**: Business logic RAG - verifica organizzazione corretta

- **`ingestion/`**: Document processing pipeline - verifica organizzazione corretta

- **`utils/`**: Shared utilities - verifica organizzazione corretta

- **`api/`**: FastAPI service (optional) - verifica organizzazione corretta

- **`tests/`**: Test infrastructure già organizzata rigorosamente (Epic 5) - verifica struttura corretta

- **`scripts/`**: Utility scripts - riorganizzazione in sottodirectory per categoria

- **`docs/`**: Documentazione centralizzata (Epic 1) - verifica struttura corretta

- **`sql/`**: Database schema scripts - verifica organizzazione corretta

L'epic implementa il pattern "Rigorous Project Structure" per garantire che ogni file sia in directory appropriata, migliorando navigabilità e mantenibilità del progetto.

## Detailed Design

### Services and Modules

| Service/Module                 | Responsibility                        | Inputs                | Outputs                                                      | Owner  |
| ------------------------------ | ------------------------------------- | --------------------- | ------------------------------------------------------------ | ------ |
| `scripts/verification/`        | Scripts di verifica setup/config      | Scripts verify\_\*.py | Scripts organizzati per categoria                            | Dev    |
| `scripts/debug/`               | Debug utilities                       | debug_mcp_tools.py    | Debug utilities organizzate                                  | Dev    |
| `scripts/optimize_database.py` | Database optimization script          | Script root           | Script spostato in scripts/verification/ o scripts/database/ | Dev    |
| `scripts/test_*.py`            | Test scripts (non pytest)             | Scripts root          | Scripts spostati in tests/ o scripts/testing/                | Dev    |
| `documents_copy_*/`            | Directory temporanee/copy             | Directory root        | Directory rimosse o merge in documents/                      | Dev    |
| `metrics`                      | Directory metrics (se non necessaria) | Directory root        | Directory rimossa o spostata                                 | Dev    |
| `site/`                        | MkDocs generated site                 | Directory root        | Verificato in .gitignore                                     | Dev    |
| `node_modules/`                | npm dependencies                      | Directory root        | Verificato in .gitignore                                     | Dev    |
| Python import system           | Import validation                     | Reorganized codebase  | Verifica imports funzionano correttamente                    | Dev    |
| Docker build system            | Docker build validation               | Reorganized codebase  | Verifica Docker builds funzionano                            | Dev    |
| CI/CD pipeline                 | CI/CD path validation                 | Reorganized codebase  | Verifica CI/CD paths funzionano                              | DevOps |

### Data Models and Contracts

**Project Structure Validation:**

```python
# scripts/validate_structure.py (nuovo script per validazione)
"""
Validates project structure against Epic 6 requirements.
"""

ROOT_ALLOWED_FILES = [
    "README.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "uv.lock",
    "docker-compose.yml",
    "Dockerfile",
    "Dockerfile.api",
    "Dockerfile.mcp",
    ".env.example",
    ".gitignore",
    "coderabbit.yaml",
    "mkdocs.yml",
    "package.json",
    "package-lock.json",
    "app.py",
    # Note: pr_description_concise.md should be removed or moved to docs/ if present
]

ROOT_FORBIDDEN_PATTERNS = [
    "*.md",  # Except README.md
    "temp_*.py",
    "debug_*.py",
    "*_copy_*",
    "test_*.py",  # Except in tests/
]

REQUIRED_DIRECTORIES = [
    "docling_mcp/",
    "core/",
    "ingestion/",
    "utils/",
    "api/",
    "tests/",
    "scripts/",
    "docs/",
    "sql/",
]

REQUIRED_SCRIPT_SUBDIRECTORIES = [
    "scripts/verification/",
    "scripts/debug/",
]
```

**Import Validation Contract:**

```python
# scripts/validate_imports.py (nuovo script per validazione imports)
"""
Validates all Python imports work correctly after reorganization.
Verifies both syntax and actual import resolution.
"""

import ast
import importlib.util
import sys
from pathlib import Path
from typing import List, Tuple

def validate_imports(root_dir: Path, project_root: Path) -> List[Tuple[str, str]]:
    """
    Validates all Python imports in project.
    Returns list of (file_path, error_message) tuples if any errors.
    """
    errors = []

    # Add project root to Python path for import resolution
    sys.path.insert(0, str(project_root))

    for py_file in root_dir.rglob("*.py"):
        # Skip __pycache__ and .venv directories
        if "__pycache__" in str(py_file) or ".venv" in str(py_file):
            continue

        try:
            # Parse AST to check syntax and extract imports
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(py_file))

            # Extract all import statements
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        try:
                            importlib.import_module(alias.name.split(".")[0])
                        except ImportError as e:
                            # Check if it's a project module (core, ingestion, docling_mcp, utils, api)
                            if alias.name.split(".")[0] in ["core", "ingestion", "docling_mcp", "utils", "api", "client"]:
                                errors.append((str(py_file), f"Import error: {alias.name} - {e}"))
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        try:
                            importlib.import_module(node.module.split(".")[0])
                        except ImportError as e:
                            if node.module.split(".")[0] in ["core", "ingestion", "docling_mcp", "utils", "api", "client"]:
                                errors.append((str(py_file), f"ImportFrom error: {node.module} - {e}"))

            # Try to compile to verify syntax
            compile(content, str(py_file), "exec")

        except SyntaxError as e:
            errors.append((str(py_file), f"Syntax error: {e}"))
        except Exception as e:
            errors.append((str(py_file), f"Validation error: {e}"))

    return errors
```

### APIs and Interfaces

**CLI Validation Interface:**

```bash
# Validate project structure (scripts created in Story 6.1)
uv run python scripts/validate_structure.py

# Validate imports (scripts created in Story 6.1)
uv run python scripts/validate_imports.py

# Validate Docker builds
docker-compose build

# Validate CI/CD paths (optional: run CI/CD locally)
# Requires 'act' tool: https://github.com/nektos/act
# act -j lint  # GitHub Actions local runner
# Alternative: Push to PR branch and verify CI/CD runs successfully
```

**Python Import Interface:**

```python
# After reorganization, imports should work as:
from docling_mcp.server import mcp
from core.rag_service import RAGService
from ingestion.embedder import EmbeddingGenerator
from utils.db_utils import get_db_pool
from api.main import app
```

### Workflows and Sequencing

**Reorganization Workflow:**

1. **Identify Files to Move**: Scan root directory per file che violano struttura rigorosa (usare `find . -maxdepth 1 -type f` per lista completa)
2. **Categorize Files**: Classifica file per destinazione (scripts/verification/, scripts/debug/, tests/, remove, docs/)
3. **Find File References**: Per ogni file da spostare, trova tutti i riferimenti usando `grep -r "filename" --include="*.py" --include="*.md" --include="*.yml" --include="*.yaml" .`
4. **Move Files**: Sposta file in directory appropriate usando `git mv` per preservare git history (es. `git mv file.py scripts/debug/`)
5. **Update Imports**: Aggiorna import statements in tutti i file trovati al passo 3 (cercare pattern `from file import` o `import file`)
6. **Update Hardcoded Paths**: Cerca e aggiorna paths hardcoded in:
   - Scripts Python: `grep -r "scripts/" --include="*.py" .`
   - Documentazione: `grep -r "\.\.\/" --include="*.md" .`
   - CI/CD workflows: Verifica `.github/workflows/*.yml` per paths hardcoded
   - Dockerfile: Verifica `COPY` e `WORKDIR` commands in tutti i Dockerfile
7. **Clean Generated Files**: Rimuovi `__pycache__/` directories: `find . -type d -name "__pycache__" -exec rm -r {} +`
8. **Verify .gitignore**: Verifica che documents*copy*\* e metrics siano in .gitignore (non rimuovere fisicamente se già ignorati)
9. **Validate Structure**: Esegui script validazione struttura: `uv run python scripts/validate_structure.py`
10. **Validate Imports**: Esegui script validazione imports: `uv run python scripts/validate_imports.py`
11. **Run Tests**: Esegui test suite per verificare che tutto funzioni: `uv run pytest tests/ -v`
12. **Validate Docker**: Verifica Docker builds funzionano: `docker-compose build`
13. **Validate CI/CD**: Verifica CI/CD paths funzionano (push a PR branch e verificare che CI/CD esegua correttamente)
14. **Update Documentation**: Aggiorna unified-project-structure.md con struttura finale

**Validation Workflow:**

1. **Structure Validation**: Verifica root directory contiene solo file autorizzati
2. **Directory Validation**: Verifica directory richieste esistono e sono organizzate correttamente
3. **Script Organization Validation**: Verifica scripts sono in sottodirectory appropriate
4. **Import Validation**: Verifica tutti gli imports funzionano correttamente
5. **Docker Validation**: Verifica Docker builds completano senza errori
6. **CI/CD Validation**: Verifica CI/CD pipeline esegue correttamente
7. **Documentation Validation**: Verifica documentazione struttura riflette organizzazione finale

## Non-Functional Requirements

### Performance

**Reorganization Performance:**

- **File Move Operations**: < 1 minuto per riorganizzazione completa (NFR-P1)
- **Import Validation**: < 30 secondi per validazione completa imports (NFR-P2)
- **Structure Validation**: < 10 secondi per validazione struttura (NFR-P3)

**Build Performance:**

- **Docker Build Time**: Nessun aumento significativo (< 5% overhead) dopo riorganizzazione (NFR-P4)
- **CI/CD Execution Time**: Nessun aumento significativo (< 5% overhead) dopo riorganizzazione (NFR-P5)

### Security

**File Organization Security:**

- **No Sensitive Files in Root**: Nessun file contenente secrets o API keys nella root directory (NFR-SEC1)
- **Gitignore Validation**: Verifica .gitignore include tutti i file generati/build (site/, node_modules/, **pycache**/) (NFR-SEC2)
- **Import Security**: Verifica imports non espongono percorsi sensibili (NFR-SEC3)

### Reliability/Availability

**Reorganization Reliability:**

- **Git History Preservation**: Git history preservata durante file moves (usare `git mv` invece di `mv`) (NFR-R1)
- **Backward Compatibility**: Imports esistenti continuano a funzionare dopo riorganizzazione (NFR-R2)
- **Rollback Capability**: Possibilità di rollback riorganizzazione se problemi (git commit separato) (NFR-R3)

**Validation Reliability:**

- **Deterministic Validation**: Scripts validazione producono risultati deterministici (NFR-R4)
- **Error Reporting**: Scripts validazione forniscono errori chiari e actionable con file path e line number (NFR-R5)
- **Import Resolution**: Script validazione imports verifica realmente che i moduli siano importabili, non solo sintassi (NFR-R6)

### Observability

**Reorganization Observability:**

- **Change Logging**: Log di tutti i file spostati/rimossi durante riorganizzazione con git commit message descrittivo (NFR-O1)
- **Validation Results**: Report validazione struttura pubblicato come artifact CI/CD con dettagli errori (NFR-O2)
- **Documentation Updates**: Changelog aggiornato con riorganizzazione struttura e lista file spostati (NFR-O3)
- **Import Change Tracking**: Log di tutti gli imports aggiornati durante riorganizzazione (NFR-O4)

## Dependencies and Integrations

**No New Dependencies Required:**

Epic 6 non richiede nuove dipendenze. Utilizza strumenti esistenti:

- **Git**: Per preservare history durante file moves (`git mv`)
- **Python Standard Library**: Per validazione imports (`ast`, `importlib`)
- **Docker**: Per validazione Docker builds (già presente)
- **CI/CD**: Per validazione CI/CD paths (già presente)

**Integration Points:**

- **Git Integration**: File moves devono usare `git mv` per preservare history. Verificare history preservata con `git log --follow -- file.py` dopo move
- **Python Import System**: Validazione imports deve verificare che tutti gli imports funzionino realmente (non solo sintassi). Verificare imports relativi e assoluti
- **Docker Integration**: Validazione Docker builds deve verificare che builds completino senza errori. Paths specifici da verificare:
  - `Dockerfile`: `COPY app.py`, `COPY client/`, `COPY utils/` (linee 42-44)
  - `Dockerfile.api`: `COPY api/`, `COPY core/`, `COPY ingestion/`, `COPY utils/`
  - `Dockerfile.mcp`: `COPY docling_mcp/`, `COPY core/`, `COPY ingestion/`, `COPY utils/`, `COPY client/`
- **CI/CD Integration**: Validazione CI/CD paths deve verificare che pipeline eseguano correttamente. Paths specifici da verificare:
  - `.github/workflows/ci.yml`: `uv run mypy core ingestion docling_mcp utils` (linea 94)
  - `.github/workflows/ci.yml`: `--cov=core --cov=ingestion --cov=docling_mcp --cov=utils` (linee 135-138)
  - Tutti i `run:` commands che referenziano paths relativi
- **Documentation Integration**: Aggiornamento unified-project-structure.md per riflettere struttura finale. Verificare anche:
  - `docs/architecture.md`: Sezione Project Structure
  - `README.md`: Paths in esempi e istruzioni
  - `docs/development-guide.md`: Paths in esempi

## Acceptance Criteria (Authoritative)

**Story 6.1: Reorganize Project Structure**

1. **Given** the project root, **When** I check for files, **Then** no markdown files exist except README.md (pr_description_concise.md removed or moved to docs/ if present)
2. **Given** the project root, **When** I check for Python files, **Then** no temporary or debug files exist (temp_query.py, debug_mcp_tools.py removed or moved)
3. **Given** the scripts directory, **When** I inspect it, **Then** scripts are organized in subdirectories: `scripts/verification/`, `scripts/debug/`
4. **Given** the codebase, **When** I check organization, **Then** code is organized by responsibility: `docling_mcp/`, `core/`, `ingestion/`, `utils/`, `api/`
5. **Given** the MCP server, **When** I check location, **Then** it's in `docling_mcp/` module, not root
6. **Given** temporary directories, **When** I check root, **Then** documents*copy*\* directories are verified in .gitignore (already ignored, no physical removal needed if they contain data)
7. **Given** the metrics directory, **When** I check root, **Then** metrics directory is removed or relocated if not needed
8. **Given** generated directories, **When** I check .gitignore, **Then** site/ and node_modules/ are in .gitignore

**Story 6.2: Clean Up and Validate Structure**

9. **Given** the project structure, **When** I validate it, **Then** all files are in appropriate directories
10. **Given** the root directory, **When** I check it, **Then** only essential files exist (README.md, pyproject.toml, docker-compose.yml, app.py entry point)
11. **Given** the documentation, **When** I check structure guide, **Then** it accurately reflects the new organization
12. **Given** the codebase, **When** I check imports, **Then** all imports work correctly after reorganization
13. **Given** Docker builds, **When** I run docker-compose build, **Then** builds complete without errors
14. **Given** CI/CD pipeline, **When** I check paths, **Then** CI/CD paths work correctly after reorganization

## Traceability Mapping

| AC   | Spec Section(s)                                   | Component(s)/API(s)                            | Test Idea                                                                    |
| ---- | ------------------------------------------------- | ---------------------------------------------- | ---------------------------------------------------------------------------- |
| AC1  | Services and Modules, Workflows and Sequencing    | Root directory, file scanning                  | Scan root directory, verify no .md files except README.md                    |
| AC2  | Services and Modules, Workflows and Sequencing    | Root directory, Python file scanning           | Scan root directory, verify no temp*\*.py or debug*\*.py files               |
| AC3  | Services and Modules                              | scripts/ directory structure                   | Inspect scripts/ directory, verify subdirectories verification/ and debug/   |
| AC4  | Services and Modules                              | Code organization by responsibility            | Verify code organization: docling_mcp/, core/, ingestion/, utils/, api/      |
| AC5  | Services and Modules                              | docling_mcp/ module location                   | Verify MCP server is in docling_mcp/ module, not root                        |
| AC6  | Services and Modules, Workflows and Sequencing    | Root directory, temporary directories          | Verify documents*copy*\* directories removed or merged                       |
| AC7  | Services and Modules                              | Root directory, metrics directory              | Verify metrics directory removed or relocated                                |
| AC8  | Services and Modules, Non-Functional Requirements | .gitignore file                                | Verify site/ and node_modules/ in .gitignore                                 |
| AC9  | Services and Modules, Workflows and Sequencing    | Project structure validation script            | Run structure validation script, verify all files in appropriate directories |
| AC10 | Services and Modules                              | Root directory, allowed files list             | Verify root directory contains only essential files                          |
| AC11 | Services and Modules, Workflows and Sequencing    | unified-project-structure.md documentation     | Verify documentation accurately reflects new organization                    |
| AC12 | Services and Modules, APIs and Interfaces         | Python import system, import validation script | Run import validation script, verify all imports work correctly              |
| AC13 | Services and Modules, Workflows and Sequencing    | Docker build system                            | Run docker-compose build, verify builds complete without errors              |
| AC14 | Services and Modules, Workflows and Sequencing    | CI/CD pipeline paths                           | Run CI/CD pipeline, verify paths work correctly after reorganization         |

## Risks, Assumptions, Open Questions

**Risks:**

1. **Risk: Import Breakage After Reorganization** (Probability: Medium, Impact: High)

   - **Description**: Spostare file può rompere imports esistenti se non aggiornati correttamente
   - **Mitigation**: Usare script validazione imports prima e dopo riorganizzazione, testare tutti gli imports dopo moves
   - **Owner**: Dev team

2. **Risk: Git History Loss** (Probability: Low, Impact: Medium)

   - **Description**: Usare `mv` invece di `git mv` può causare perdita git history
   - **Mitigation**: Usare sempre `git mv` per file moves, verificare history preservata dopo moves
   - **Owner**: Dev team

3. **Risk: CI/CD Path Breakage** (Probability: Medium, Impact: Medium)

   - **Description**: Riorganizzazione può rompere paths hardcoded in CI/CD workflows
   - **Mitigation**: Verificare tutti i paths CI/CD dopo riorganizzazione, aggiornare se necessario
   - **Owner**: DevOps team

4. **Risk: Docker Build Failure** (Probability: Low, Impact: Medium)
   - **Description**: Riorganizzazione può rompere Docker builds se paths hardcoded
   - **Mitigation**: Verificare Docker builds dopo riorganizzazione, aggiornare Dockerfile se necessario
   - **Owner**: DevOps team

**Assumptions:**

1. **Assumption: Git History Preservation**

   - **Description**: Assumiamo che `git mv` preservi history correttamente per tutti i file
   - **Validation**: Verificare git log dopo moves per confermare history preservata
   - **Owner**: Dev team

2. **Assumption: Import Compatibility**

   - **Description**: Assumiamo che Python import system funzioni correttamente dopo riorganizzazione
   - **Validation**: Eseguire script validazione imports dopo riorganizzazione
   - **Owner**: Dev team

3. **Assumption: CI/CD Path Compatibility**
   - **Description**: Assumiamo che CI/CD paths possano essere aggiornati facilmente se necessario
   - **Validation**: Verificare CI/CD pipeline dopo riorganizzazione
   - **Owner**: DevOps team

**Open Questions:**

1. **Question: Script Organization Strategy**

   - **Description**: Alcuni script (test\_\*.py) potrebbero essere in tests/ o scripts/testing/ - quale strategia preferire?
   - **Answer**: Scripts di test non-pytest vanno in tests/ se sono parte della test suite, altrimenti scripts/testing/ se sono utility
   - **Owner**: Dev team

2. **Question: Temporary Directory Cleanup**

   - **Description**: documents*copy*\* directories contengono dati importanti o possono essere rimossi?
   - **Answer**: Verificare contenuto, merge in documents/ se dati importanti, rimuovere se duplicati
   - **Owner**: Dev team

3. **Question: Metrics Directory Purpose**
   - **Description**: Directory metrics/ serve ancora o può essere rimossa?
   - **Answer**: Verificare se contiene dati importanti, rimuovere se non necessaria o spostare se contiene dati
   - **Owner**: Dev team

## Test Strategy Summary

**Test Levels:**

1. **Structure Validation Tests** (`scripts/validate_structure.py`):

   - **Scope**: Validazione struttura directory e file organization
   - **Target**: Root directory, required directories, script subdirectories
   - **Framework**: Python script con pathlib
   - **Coverage Target**: 100% validazione struttura (tutti i file/directory verificati)
   - **Execution Time**: < 10 secondi

2. **Import Validation Tests** (`scripts/validate_imports.py`):

   - **Scope**: Validazione tutti gli imports funzionano correttamente (sintassi + risoluzione reale)
   - **Target**: Tutti i file Python nel progetto (esclusi **pycache** e .venv)
   - **Framework**: Python script con ast, importlib, sys.path manipulation
   - **Coverage Target**: 100% validazione imports (tutti i file Python verificati, imports relativi e assoluti)
   - **Execution Time**: < 30 secondi
   - **Critical**: Deve verificare che i moduli siano realmente importabili, non solo sintassi corretta

3. **Docker Build Validation Tests**:

   - **Scope**: Validazione Docker builds funzionano dopo riorganizzazione
   - **Target**: Dockerfile, docker-compose.yml
   - **Framework**: Docker build commands
   - **Coverage Target**: Tutti i Dockerfile verificati
   - **Execution Time**: < 5 minuti per build completo

4. **CI/CD Path Validation Tests**:

   - **Scope**: Validazione CI/CD paths funzionano dopo riorganizzazione
   - **Target**: .github/workflows/ CI/CD workflows
   - **Framework**: GitHub Actions local runner (act) o manual verification
   - **Coverage Target**: Tutti i workflows CI/CD verificati
   - **Execution Time**: < 10 minuti per esecuzione completa

**Test Execution Strategy:**

- **Pre-Reorganization**:
  - Eseguire structure validation per identificare file da spostare
  - Trovare tutti i riferimenti ai file da spostare usando grep
  - Creare lista completa di file e riferimenti da aggiornare
- **During Reorganization**:
  - Usare `git mv` per preservare history (verificare con `git log --follow`)
  - Aggiornare imports immediatamente dopo ogni move
  - Pulire **pycache** dopo ogni move: `find . -type d -name "__pycache__" -exec rm -r {} +`
  - Eseguire test incrementali dopo ogni gruppo di moves
- **Post-Reorganization**:
  - Eseguire tutti i test di validazione (structure, imports, Docker, CI/CD)
  - Eseguire test suite completa: `uv run pytest tests/ -v`
  - Verificare che tutti i paths hardcoded siano aggiornati
- **Documentation Update**:
  - Aggiornare unified-project-structure.md con struttura finale
  - Aggiornare CHANGELOG.md con lista file spostati
  - Verificare che tutti i riferimenti in documentazione siano corretti

**Validation Strategy:**

- **Automated Validation**: Scripts Python per validazione struttura e imports
- **Manual Validation**: Verifica Docker builds e CI/CD paths manualmente o con tools
- **Documentation Validation**: Verifica documentazione struttura riflette organizzazione finale
