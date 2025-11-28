# Epic Technical Specification: Core RAG Baseline & Documentation

Date: 2025-11-26
Author: Stefano
Epic ID: 1
Status: Draft

---

## Overview

Epic 1 stabilisce la baseline documentale del sistema RAG esistente, creando le fondamenta necessarie per gli epic successivi di monitoring e observability. Questo epic trasforma il sistema da prototipo funzionale a sistema production-ready con documentazione completa, API reference auto-generata, e guida per sviluppatori. Senza questa documentazione completa, l'implementazione di monitoring (Epic 2) sarebbe difficile da validare e mantenere. Questo epic crea la "single source of truth" per il sistema, garantendo che tutti gli sviluppatori abbiano accesso a informazioni accurate e aggiornate sull'architettura, le API, e le procedure di setup.

## Objectives and Scope

**In-Scope:**

- Documentazione completa architettura esistente (`docs/architecture.md`)
- API reference auto-generata per tutte le funzioni pubbliche (`core/`, `ingestion/`, `utils/`)
- README production-ready con setup < 5 minuti
- Centralizzazione documentazione progetto in `guide/` (eliminazione file sparsi in root)
- Pulizia root directory da file obsoleti o inutili
- Troubleshooting guide completa per MCP server
- Guida struttura progetto e organizzazione codice

**Out-of-Scope:**

- Implementazione nuove features (solo documentazione)
- Refactoring codice esistente (solo documentazione)
- Testing infrastructure (Epic 5)
- Monitoring implementation (Epic 2)

## System Architecture Alignment

Epic 1 si allinea direttamente con l'architettura esistente documentata in `docs/architecture.md`. I componenti principali coinvolti sono:

- **`docs/`**: Directory per documentazione BMAD (sviluppo workflow, non modificata da questo epic)
- **`guide/`**: Directory per documentazione progetto (nuova, da creare)
- **`core/`**: Business logic RAG (da documentare con API reference)
- **`ingestion/`**: Pipeline di processamento documenti (da documentare)
- **`utils/`**: Utility condivise (da documentare)
- **`mcp/`**: MCP server (architettura già documentata, troubleshooting da aggiungere)

L'epic non modifica l'architettura esistente ma la documenta completamente, garantendo che tutti i componenti siano chiaramente descritti con responsabilità, input/output, e pattern di utilizzo.

## Detailed Design

### Services and Modules

| Service/Module                   | Responsibility                            | Inputs                            | Outputs                          | Owner     |
| -------------------------------- | ----------------------------------------- | --------------------------------- | -------------------------------- | --------- |
| **Documentation Generator**      | Genera API reference da docstrings        | Python source files               | HTML/PDF documentation           | SM        |
| **Architecture Documentation**   | Documenta architettura sistema            | Codebase scan, ADRs               | `docs/architecture.md`           | Architect |
| **README Generator**             | Crea README production-ready              | Project info, setup steps         | `README.md`                      | SM        |
| **Documentation Consolidator**   | Centralizza file markdown progetto sparsi | Root-level `.md` files (progetto) | `guide/` directory               | SM        |
| **Root Cleaner**                 | Rimuove file obsoleti/inutili dalla root  | Root directory scan               | Root directory pulita            | SM        |
| **Troubleshooting Guide Writer** | Crea guida troubleshooting MCP            | Error logs, common issues         | `guide/troubleshooting-guide.md` | SM        |

### Data Models and Contracts

**Documentation Structure:**

- `docs/`: Directory BMAD (documentazione workflow sviluppo, non modificata)
- `guide/`: Directory documentazione progetto (nuova, da creare)
  - `guide/api-reference/`: Directory per API reference auto-generata
  - `guide/troubleshooting-guide.md`: Guida troubleshooting MCP server
  - `guide/development-guide.md`: Guida struttura progetto e organizzazione codice
- `README.md`: Entry point root con quick start

**API Reference Structure:**

- Moduli organizzati per directory (`core/`, `ingestion/`, `utils/`)
- Ogni funzione pubblica con docstring completa
- Esempi di utilizzo per funzioni principali
- Type hints per tutti i parametri e return types

### APIs and Interfaces

**Documentation Generation API:**

- **Tool**: Sphinx o MkDocs CLI
- **Input**: Python source files con docstrings
- **Output**: HTML documentation (static site)
- **Deployment**: GitHub Pages o local server

**File Organization Interface:**

- **Input**: Root-level `.md` files progetto da spostare (escludendo file BMAD in `docs/`)
- **Output**: File organizzati in `guide/` con struttura logica
- **Process**: Script di migrazione o manuale con validazione, pulizia root da file obsoleti

### Workflows and Sequencing

**Story 1.1: Document Current Architecture**

1. Review existing `docs/architecture.md`
2. Verify accuracy against current codebase
3. Update sections if needed (MCP server architecture, component descriptions)
4. Add data flow diagrams if missing
5. Validate completeness

**Story 1.2: Generate API Reference Documentation**

1. Install Sphinx o MkDocs
2. Configure documentation generator (`guide/api-reference/conf.py` o `mkdocs.yml`)
3. Scan `core/`, `ingestion/`, `utils/` per funzioni pubbliche
4. Verify docstrings completeness
5. Generate HTML documentation
6. Configure GitHub Actions per auto-build
7. Deploy su GitHub Pages o local server

**Story 1.3: Create Production-Ready README**

1. Review existing README.md
2. Add quick start section (< 5 minuti)
3. Add prerequisites con versioni
4. Add GitHub badges (build status, coverage, version)
5. Add Docker setup instructions
6. Add troubleshooting section
7. Validate setup instructions

**Story 1.4: Centralize Documentation**

1. Create `guide/` directory per documentazione progetto
2. Identify root-level `.md` files progetto (eccetto README.md e file BMAD in `docs/`)
3. Identify file obsoleti/inutili nella root da rimuovere
4. Categorize files per contenuto
5. Move file progetto a `guide/` con nomi appropriati
6. Remove file obsoleti/inutili dalla root
7. Integrate contenuto da file sparsi in guide appropriate
8. Create `guide/troubleshooting-guide.md` con sezione MCP server
9. Add project structure guide a `guide/development-guide.md`
10. Update links in tutti i file
11. Validate struttura finale (root pulita, `guide/` organizzata)

## Non-Functional Requirements

### Performance

- **NFR-P1**: Documentazione generation < 2 minuti per build completo
- **NFR-P2**: API reference search < 100ms per query
- **NFR-P3**: README setup completabile in < 5 minuti (misurato con nuovo sviluppatore)

### Security

- **NFR-SEC1**: Nessun secret o API key nella documentazione
- **NFR-SEC2**: `.env.example` template senza valori reali
- **NFR-SEC3**: Documentazione pubblica non contiene informazioni sensibili

### Reliability/Availability

- **NFR-R1**: Documentazione sempre accessibile (GitHub Pages uptime > 99%)
- **NFR-R2**: README sempre aggiornato con setup instructions corrette
- **NFR-R3**: Link interni sempre validi (no broken links)

### Observability

- **NFR-O1**: Documentazione versioning tramite git tags
- **NFR-O2**: Changelog per modifiche documentazione significative
- **NFR-O3**: Badge GitHub mostrano stato build e coverage

## Dependencies and Integrations

**Documentation Tools:**

- **Sphinx** (>=7.0.0) o **MkDocs** (>=1.5.0): API reference generation
- **sphinx-autodoc** o **mkdocs-material**: Auto-documentation da docstrings
- **GitHub Pages**: Hosting documentazione statica

**Project Dependencies (da `pyproject.toml`):**

- Python >=3.10 (runtime)
- UV (package manager)
- Tutte le dipendenze esistenti per validazione setup

**External Services:**

- GitHub (hosting, CI/CD, Pages)
- Shields.io (badge generation)

## Acceptance Criteria (Authoritative)

**AC1**: `docs/architecture.md` riflette accuratamente tutti i componenti (core, ingestion, utils, MCP, Streamlit) con responsabilità chiare

**AC2**: `docs/architecture.md` contiene diagrammi completi per ingestion e query pipelines

**AC3**: Tutte le funzioni pubbliche in `core/`, `ingestion/`, `utils/` hanno docstrings complete

**AC4**: API reference generata contiene parametri, return types, e esempi di utilizzo per ogni funzione

**AC5**: API reference deployata e accessibile via GitHub Pages o local server

**AC6**: README.md permette setup locale in < 5 minuti (validato con nuovo sviluppatore)

**AC7**: README.md contiene tutti i prerequisites con versioni specifiche

**AC8**: README.md contiene GitHub badges (build status, coverage, version)

**AC9**: Nessun file `.md` progetto in root directory (eccetto README.md, `docs/` rimane per BMAD)

**AC10**: Tutti i file markdown progetto sparsi sono integrati in guide appropriate in `guide/`

**AC11**: Root directory pulita da file obsoleti o inutili

**AC12**: `guide/troubleshooting-guide.md` contiene sezione completa per MCP server issues

**AC13**: `guide/development-guide.md` contiene guida struttura progetto e organizzazione codice

**AC14**: Tutti i link interni nella documentazione sono validi (no broken links)

## Traceability Mapping

| AC   | Spec Section                           | Component/API                    | Test Idea                                                                        |
| ---- | -------------------------------------- | -------------------------------- | -------------------------------------------------------------------------------- |
| AC1  | Detailed Design → Services and Modules | `docs/architecture.md`           | Manual review: verifica tutti i componenti documentati                           |
| AC2  | Detailed Design → Workflows            | `docs/architecture.md`           | Manual review: verifica presenza diagrammi                                       |
| AC3  | Detailed Design → APIs and Interfaces  | `core/`, `ingestion/`, `utils/`  | Script: scan docstrings, verifica completeness                                   |
| AC4  | Detailed Design → APIs and Interfaces  | API reference generator          | Manual review: verifica parametri, types, esempi                                 |
| AC5  | Detailed Design → APIs and Interfaces  | GitHub Pages deployment          | Manual test: accesso documentazione online                                       |
| AC6  | Detailed Design → Workflows            | `README.md`                      | User test: nuovo sviluppatore completa setup in < 5 min                          |
| AC7  | Detailed Design → Workflows            | `README.md`                      | Manual review: verifica prerequisites con versioni                               |
| AC8  | Detailed Design → Workflows            | `README.md`                      | Manual review: verifica presenza badge                                           |
| AC9  | Detailed Design → Workflows            | Root directory                   | Script: verifica nessun `.md` file progetto (eccetto README.md, `docs/` esclusa) |
| AC10 | Detailed Design → Workflows            | `guide/` directory               | Manual review: verifica integrazione contenuto file progetto sparsi              |
| AC11 | Detailed Design → Workflows            | Root directory                   | Script: verifica rimozione file obsoleti/inutili                                 |
| AC12 | Detailed Design → Workflows            | `guide/troubleshooting-guide.md` | Manual review: verifica sezione MCP server                                       |
| AC13 | Detailed Design → Workflows            | `guide/development-guide.md`     | Manual review: verifica guida struttura progetto                                 |
| AC14 | Detailed Design → Workflows            | Tutti i file `guide/`            | Script: link checker, verifica validità link interni                             |

## Risks, Assumptions, Open Questions

**Risk R1**: Documentazione potrebbe diventare obsoleta rapidamente se non mantenuta

- **Mitigation**: Integrare documentazione generation in CI/CD, review periodico

**Risk R2**: Setup instructions potrebbero non funzionare su tutti gli ambienti

- **Mitigation**: Testare su macOS, Linux, Windows, validare con nuovi sviluppatori

**Assumption A1**: Sviluppatori hanno accesso a GitHub per vedere badge e documentazione

- **Validation**: Verificare che GitHub Pages sia accessibile pubblicamente

**Assumption A2**: Tutti i file markdown progetto sparsi contengono informazioni utili da preservare

- **Validation**: Review manuale di ogni file prima di integrazione in `guide/`

**Assumption A3**: File in `docs/` sono documentazione BMAD e non devono essere spostati

- **Validation**: Verificare che `docs/` contenga solo file workflow BMAD, non file progetto

**Question Q1**: Preferire Sphinx o MkDocs per API reference?

- **Decision**: MkDocs più semplice e moderno, meglio per progetti Python moderni

**Question Q2**: Dove hostare documentazione? GitHub Pages o local server?

- **Decision**: GitHub Pages per accessibilità pubblica, local server per sviluppo

## Test Strategy Summary

**Test Levels:**

1. **Unit Tests**: Script per validazione docstrings completeness
2. **Integration Tests**: Link checker per validazione link interni
3. **Manual Tests**: User testing con nuovo sviluppatore per setup instructions

**Test Coverage:**

- Docstrings: 100% delle funzioni pubbliche devono avere docstrings
- Link validity: 100% dei link interni devono essere validi
- Setup instructions: Validato con almeno 1 nuovo sviluppatore

**Test Frameworks:**

- **pytest**: Per script di validazione
- **linkchecker**: Per validazione link
- **Manual testing**: Per user experience validation

**Critical Test Cases:**

1. Setup completo da zero in < 5 minuti
2. API reference accessibile e completa
3. Nessun broken link nella documentazione
4. Tutti i componenti architetturali documentati
