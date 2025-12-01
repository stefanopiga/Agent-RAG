# Story 5.4: Implement Playwright E2E Tests

Status: ready-for-dev

## Story

As a QA engineer,  
I want E2E tests for critical Streamlit workflows,  
so that I can validate user experience.

## Acceptance Criteria

**Nota:** Questi AC corrispondono a AC#13, AC#14, AC#15 nel tech spec (tech-spec-epic-5.md).

1. **Given** Streamlit app running, **When** pytest-playwright test runs, **Then** it simulates user query and validates response (AC#13)
2. **Given** E2E test, **When** it completes, **Then** I see screenshot/video recording for debugging (AC#14)
3. **Given** CI/CD, **When** tests run, **Then** E2E tests execute in headless mode (AC#15)

## Tasks / Subtasks

- [ ] Task 1: Setup pytest-playwright infrastructure (AC: #1/AC#13, #2/AC#14, #3/AC#15)

  - [ ] Install pytest-playwright dependencies: `pytest-playwright>=0.4.0` (include playwright)
  - [ ] Verify playwright browsers installation: `playwright install chromium` (solo Chromium per CI/CD)
  - [ ] Create `tests/e2e/` directory per E2E tests (se non esiste già)
  - [ ] Create `tests/e2e/__init__.py` per package init
  - [ ] Create `tests/e2e/screenshots/` directory per screenshot storage
  - [ ] Configure pytest marker `@pytest.mark.e2e` per E2E tests (verificare in pyproject.toml)
  - [ ] Configure pytest marker `@pytest.mark.slow` per E2E tests (già presente in pyproject.toml da Story 5-1)
  - [ ] Create conftest.py fixture per pytest-playwright: `streamlit_app_url` fixture con configurazione base URL
  - [ ] Configure pytest-playwright browser context: `browser_context_args` fixture per viewport e altre impostazioni

- [ ] Task 2: Implement Streamlit query workflow E2E test (AC: #1/AC#13, #2/AC#14)

  - [ ] Create `tests/e2e/test_streamlit_workflow.py` con test completo per Streamlit query workflow
  - [ ] Implement `test_streamlit_query_workflow()` che simula query utente completa:
    - Navigate to Streamlit app usando `page.goto()` con base URL da fixture
    - Wait for app to load usando `page.wait_for_selector('[data-testid="query-input"]')`
    - Enter query usando `page.locator('[data-testid="query-input"]').fill()`
    - Submit query usando `page.locator('[data-testid="submit-button"]').click()`
    - Wait for response usando `page.wait_for_selector('[data-testid="response"]', timeout=10000)`
    - Verify response contiene contenuto atteso usando `expect(response).to_contain_text()`
  - [ ] Implement screenshot capture: `page.screenshot(path="tests/e2e/screenshots/query_workflow.png")` dopo test completion
  - [ ] Implement video recording: configurare pytest-playwright per video recording automatico
  - [ ] Test che screenshot/video sono salvati correttamente (verifica AC#14)
  - [ ] Test che workflow completo funziona end-to-end (verifica AC#13)

- [ ] Task 3: Add data-testid selectors to Streamlit app (AC: #1/AC#13)

  - [ ] Verificare che `app.py` ha `data-testid` attributes per elementi critici:
    - `data-testid="query-input"` per input query
    - `data-testid="submit-button"` per submit button
    - `data-testid="response"` per response area
    - `data-testid="sidebar-stats"` per sidebar statistics (se presente)
  - [ ] Se `data-testid` non presenti, aggiungere a `app.py` per elementi critici del workflow
    - **Nota:** Opzionalmente usare MCP browser (cursor-browser-extension) per esplorare UI e identificare elementi, ma Playwright è necessario per test automatizzati
  - [ ] Verificare che selectors sono unici e non cambiano con UI updates

- [ ] Task 4: Configure CI/CD for E2E tests (AC: #3/AC#15)

  - [ ] Verificare che `.github/workflows/ci.yml` esiste (già creato in Epic 4)
  - [ ] Aggiungere step per install playwright browsers: `playwright install chromium` (solo Chromium per CI/CD)
  - [ ] Aggiungere step per start Streamlit app in background: `streamlit run app.py --server.headless=true` con port 8501
  - [ ] Aggiungere step per run E2E tests: `pytest tests/e2e/ --base-url=http://localhost:8501` (headless mode default)
  - [ ] Configurare pytest-playwright per headless mode in CI/CD (default behavior)
  - [ ] Aggiungere step per upload screenshots/videos come artifacts su test failure
  - [ ] Verificare che E2E tests sono eseguiti solo su PR/push a main (non su ogni commit per performance)

- [ ] Task 5: Testing subtasks (AC: #1, #2, #3)

  - [ ] Run E2E test localmente: `pytest tests/e2e/ --base-url=http://localhost:8501` (verifica AC#13)
  - [ ] Verify screenshot/video sono generati correttamente (verifica AC#14)
  - [ ] Verify E2E test funziona in headless mode: `pytest tests/e2e/ --base-url=http://localhost:8501 --headed=false` (verifica AC#15)
  - [ ] Verify CI/CD pipeline esegue E2E tests correttamente (verifica AC#15)
  - [ ] Document E2E test results in Dev Notes

## Dev Notes

### ⚠️ Technical Debt Analysis

**IMPORTANTE:** Prima di iniziare l'implementazione, leggere il documento di analisi del debito tecnico:

- [Source: docs/stories/5/5-4/5-4-technical-debt-analysis.md]

Il documento identifica **10 lacune critiche** che devono essere affrontate per evitare debito tecnico futuro. Le **3 lacune CRITICHE** devono essere implementate durante questa story:

1. **Test Isolation e Streamlit Session State Cleanup** - Essenziale per test deterministici
2. **Retry Logic per Test Flaky** - Essenziale per CI/CD stabile
3. **Network Interception** - Essenziale per test deterministici e costi controllati

Il documento contiene per ogni lacuna:

- Descrizione dettagliata del problema
- Impatto sul progetto
- Raccomandazioni con codice esempio
- Task aggiuntivi da implementare
- Riferimenti a best practices

### Architecture Patterns and Constraints

**pytest-playwright E2E Testing Structure (ADR-003):**

- E2E tests in `tests/e2e/` directory
- Use pytest-playwright fixtures: `page`, `context`, `browser` (automaticamente disponibili)
- pytest-playwright configurazione: `conftest.py` configura `browser_context_args` per viewport e altre impostazioni
- Base URL configurazione: Usa `--base-url` CLI option per evitare hardcoded URLs nei test
- Screenshots: Capture screenshots on test failure per debugging (automatico con `--screenshot=on`)
- Video: Optional video recording per debugging (`--video=on`)
- Tracing: Optional tracing per debugging (`--tracing=on`)
- Selectors: Use `data-testid` attributes per reliable element selection (non CSS selectors che cambiano con UI updates)
- CLI Options: `--headed`, `--browser`, `--tracing`, `--video`, `--screenshot` disponibili

**pytest-playwright E2E Testing Workflow:**

1. Start Streamlit app in background (local: manual, CI/CD: automated)
2. Configure pytest-playwright fixtures in `conftest.py`:
   - `streamlit_app_url` fixture con base URL configurabile
   - `browser_context_args` fixture per viewport e altre impostazioni
3. Write E2E test usando `page` fixture da pytest-playwright:
   - Navigate: `page.goto(base_url)` o `page.goto("/")` se `--base-url` configurato
   - Wait for elements: `page.wait_for_selector('[data-testid="..."]')` invece di `time.sleep()`
   - Interact: `page.locator('[data-testid="..."]').fill()`, `.click()`, etc.
   - Assert: `expect(page.locator('[data-testid="..."]')).to_contain_text("...")`
4. Capture screenshots/videos: Automatico con pytest-playwright configurazione
5. Run tests: `pytest tests/e2e/ --base-url=http://localhost:8501` (headless mode default)

**CI/CD Integration:**

- Install playwright browsers: `playwright install chromium` (solo Chromium per CI/CD, non tutti i browser)
- Start Streamlit app: `streamlit run app.py --server.headless=true` in background
- Run E2E tests: `pytest tests/e2e/ --base-url=http://localhost:8501` (headless mode default)
- Upload artifacts: Screenshots/videos/traces su test failure come GitHub Actions artifacts
- Performance: E2E tests sono lenti (<30s per test), eseguire solo su PR/push a main (non su ogni commit)

**Testing Standards:**

- E2E tests usano `@pytest.mark.e2e` marker (già configurato in pyproject.toml)
- E2E tests usano `@pytest.mark.slow` marker (già configurato in pyproject.toml)
- Test naming pattern: `test_<functionality>_<condition>_<expected_result>`
- Pattern AAA (Arrange, Act, Assert) per tutti i test
- E2E tests richiedono Streamlit app running - considerare setup/teardown in CI/CD
- Use `data-testid` selectors per reliable element selection (non CSS selectors)

**MCP Browser vs Playwright:**

- **MCP Browser (cursor-browser-extension)**: Tool per AI agents per esplorare UI durante design phase, utile per identificare `data-testid` e scoprire funzionalità. NON sostituisce Playwright per test automatizzati.
- **Playwright/Chromium**: Framework di testing automatizzato necessario per:
  - Test ripetibili in CI/CD (AC#15)
  - Screenshot/video automatici (AC#14)
  - Assertions programmatiche (AC#13)
  - Test isolation e parallel execution
  - Integrazione con pytest per reporting
- **Uso combinato**: MCP browser può essere usato opzionalmente per esplorare UI e generare test iniziali, ma Playwright è obbligatorio per esecuzione automatizzata.

[Source: docs/architecture.md#ADR-003]
[Source: docs/testing-strategy.md#End-to-End-Testing]
[Source: docs/stories/5/tech-spec-epic-5.md#Playwright-E2E-Interface]

### Learnings from Previous Story

**From Story 5-3 (Status: done)**

**File Creati/Modificati dalla Storia 5-3:**

| File                                        | Azione      | Descrizione                                                      | Utilizzo in Story 5-4                                                                                  |
| ------------------------------------------- | ----------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `tests/evaluation/test_ragas_evaluation.py` | Creato      | RAGAS evaluation test suite                                      | Non necessario per E2E tests (E2E tests usano real Streamlit app, non RAGAS evaluation)                |
| `tests/fixtures/golden_dataset.json`        | Disponibile | 25 query-answer pairs per RAGAS evaluation (creato in Story 5-1) | **Potenzialmente utilizzabile** per E2E tests se vogliamo testare query specifiche dal golden dataset  |
| `tests/conftest.py`                         | Disponibile | Fixtures complete per database, embedder, LLM, LangFuse          | **Riutilizzare pattern** per fixtures pytest-playwright (ma E2E tests usano real services, non mocked) |

**Infrastruttura Disponibile:**

- **Test Directory Structure**: `tests/e2e/` directory già presente (creato in Story 5-1) - utilizzare per E2E tests
- **Pytest Markers**: `@pytest.mark.e2e` e `@pytest.mark.slow` già configurati in `pyproject.toml` (Story 5-1) - utilizzare per E2E tests
- **Streamlit App**: `app.py` già presente con session tracking (Epic 3) - utilizzare come target per E2E tests
- **CI/CD Pipeline**: `.github/workflows/ci.yml` già esistente (Epic 4) - estendere con E2E test steps

**Pattern da Seguire:**

- Utilizzare `data-testid` selectors invece di CSS selectors per reliable element selection
- Utilizzare `@pytest.mark.e2e` e `@pytest.mark.slow` markers per tutti gli E2E tests
- Seguire pattern AAA (Arrange-Act-Assert) documentato in `tests/README.md`
- Implementare screenshot/video recording per debugging (automatico con pytest-playwright)
- Configurare CI/CD per eseguire E2E tests solo su PR/push a main (performance)

**Note Importanti:**

- **E2E Tests Richiedono Real Streamlit App**: E2E tests NON possono usare mocked Streamlit app perché richiedono real browser automation. Questo significa che E2E tests richiedono Streamlit app running in background.
- **pytest-playwright Fixtures**: pytest-playwright fornisce automaticamente `page`, `context`, `browser` fixtures - non è necessario crearle manualmente. Configurare solo `browser_context_args` e `streamlit_app_url` fixtures in `conftest.py`.
- **CI/CD Setup**: E2E tests richiedono setup complesso in CI/CD: start Streamlit app in background, install playwright browsers, run tests, upload artifacts. Considerare timeout appropriati per E2E tests (<30s per test).
- **Headless Mode**: pytest-playwright esegue in headless mode di default in CI/CD. Per debugging locale, usare `--headed` flag.

[Source: docs/stories/5/5-3/5-3-implement-ragas-evaluation-suite.md#Dev-Agent-Record]
[Source: docs/stories/5/5-1/5-1-setup-testing-infrastructure-with-tdd-structure.md#Dev-Agent-Record]

### Project Structure Notes

**Following unified-project-structure.md requirements:**

**Directory Alignment:**

- `tests/e2e/` directory già presente (creato in Story 5-1) - utilizzare per E2E tests
- File test seguono convenzione: `test_*.py` o `*_test.py` (come specificato in unified-project-structure.md)
- `tests/e2e/screenshots/` directory da creare per screenshot storage

**File Locations:**

- `tests/e2e/test_streamlit_workflow.py`: Nuovo file per E2E tests Streamlit workflow
- `tests/e2e/__init__.py`: Package init per E2E tests (se non esiste già)
- `tests/conftest.py`: Estendere con fixtures pytest-playwright (`streamlit_app_url`, `browser_context_args`)
- `app.py`: Aggiungere `data-testid` attributes per elementi critici (se non presenti)
- `.github/workflows/ci.yml`: Estendere con E2E test steps

**No Conflicts Detected:**

- Struttura allineata con Epic 5 requirements
- Compatibile con unified-project-structure.md specifications
- Compatibile con infrastruttura testing esistente (Story 5-1, Story 5-2, Story 5-3)

[Source: docs/unified-project-structure.md#tests-directory]
[Source: docs/stories/5/tech-spec-epic-5.md#System-Architecture-Alignment]

### References

**Internal Documentation:**

- [Source: docs/prd.md#Testing-&-Quality-Assurance-(TDD)]: Product requirements document - E2E testing requirements (FR34), pytest-playwright E2E tests per workflow critici
- [Source: docs/stories/5/tech-spec-epic-5.md]: Complete technical specification for Epic 5, Story 5.4 acceptance criteria (AC#13, AC#14, AC#15), pytest-playwright E2E testing workflow, CI/CD integration
- [Source: docs/epics.md#Epic-5]: Story breakdown and acceptance criteria
- [Source: docs/architecture.md#ADR-003]: TDD Structure Rigorosa decision
- [Source: docs/testing-strategy.md#End-to-End-Testing]: Complete E2E testing strategy, pytest-playwright setup, screenshot/video recording, CI/CD integration
- [Source: docs/coding-standards.md#Testing-Standards]: Testing standards, test organization (sezione 7.1), naming conventions (sezione 7.2), AAA pattern (sezione 7.3)
- [Source: docs/unified-project-structure.md#tests-directory]: Test directory structure requirements
- [Source: app.py#Streamlit-App-Entry-Point]: Streamlit app entry point - target per E2E tests, aggiungere `data-testid` attributes per elementi critici
- [Source: tests/conftest.py#Shared-Test-Fixtures]: Available fixtures - estendere con fixtures pytest-playwright (`streamlit_app_url`, `browser_context_args`)
- [Source: tests/e2e/#E2E-Test-Directory]: E2E test directory - utilizzare per E2E tests (già presente con `__init__.py` e `test_streamlit_ui_observability.py`)
- **[Source: docs/stories/5/5-4/5-4-technical-debt-analysis.md]**: ⚠️ **CRITICO** - Analisi architetturale con 10 lacune identificate che potrebbero tradursi in debito tecnico. Affrontare almeno le 3 lacune CRITICHE (Test Isolation, Retry Logic, Network Interception) durante l'implementazione. Contiene raccomandazioni dettagliate con codice esempio per ogni lacuna.

**External Official Documentation:**

- **pytest-playwright Documentation**: https://playwright.dev/python/docs/intro - Complete pytest-playwright guide
- **Playwright Python API**: https://playwright.dev/python/docs/api/class-playwright - Playwright Python API reference
- **pytest-playwright Fixtures**: https://playwright.dev/python/docs/test-runners#fixtures - pytest-playwright fixtures documentation
- **Playwright Selectors**: https://playwright.dev/python/docs/selectors - Playwright selector strategies, `data-testid` best practices
- **Playwright Screenshots**: https://playwright.dev/python/docs/screenshots - Screenshot capture guide
- **Playwright Video**: https://playwright.dev/python/docs/videos - Video recording guide
- **Playwright CI/CD**: https://playwright.dev/python/docs/ci - CI/CD integration guide

## Change Log

- **2025-01-30**: Story created from tech-spec-epic-5.md and epics.md

## Dev Agent Record

### Context Reference

- docs/stories/5/5-4/5-4-implement-playwright-e2e-tests.context.xml

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
