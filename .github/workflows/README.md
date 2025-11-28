# GitHub Actions Workflows

Documentazione dei workflow CI/CD per il progetto docling-rag-agent.

## Workflow Disponibili

### CI (`ci.yml`)

**Trigger:**

- Pull requests su branch `main` o `develop`
- Push su branch `main` o `develop`

**Job Eseguiti in Parallelo:**

1. **lint** (Ruff)

   - Esegue `ruff check` con zero warnings enforcement
   - Esegue `ruff format --check` con zero errori enforcement
   - Timeout: 10 minuti
   - **Status:** Bloccante (build failure se fallisce)

2. **type-check** (Mypy)

   - Esegue `mypy` su moduli: `core`, `ingestion`, `docling_mcp`, `utils`
   - Zero errors enforcement
   - Timeout: 10 minuti
   - **Status:** Bloccante (build failure se fallisce)

3. **test** (Pytest + Coverage)

   - Esegue unit tests con coverage enforcement >70%
   - Upload coverage report XML come artifact
   - Timeout: 15 minuti
   - **Status:** Bloccante (build failure se coverage <70% o test falliscono)
   - **Nota:** Solo unit tests eseguiti in CI (integration/e2e richiedono database)

4. **build** (Docker)

   - Build Streamlit Docker image (`Dockerfile`)
   - Build API Docker image (`Dockerfile.api`)
   - Verifica dimensioni immagini <500MB
   - Timeout: 20 minuti
   - **Status:** Bloccante (build failure se build fallisce o immagini >500MB)
   - **Cache:** Docker Buildx cache configurato per performance

5. **secret-scan** (TruffleHog OSS)
   - Scansiona git history completa per secrets
   - Usa `.trufflehogignore` per falsi positivi
   - Timeout: 10 minuti
   - **Status:** Bloccante (build failure se secrets rilevati)

**Caching:**

- UV dependencies cache (chiave: `uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}`)
- Docker Buildx cache (GitHub Actions cache)

**Concurrency:**

- Cancella run in corso per lo stesso branch quando parte un nuovo run

## Quality Gates

Tutti i job sono **bloccanti** per garantire che solo codice di qualità venga mergiato:

- ✅ Linting: Zero warnings/errori di formattazione
- ✅ Type Checking: Zero type errors
- ✅ Testing: Coverage >70% e tutti i test passano
- ✅ Build: Immagini Docker compilano correttamente e <500MB
- ✅ Security: Nessun secret rilevato

**Risultato:** PR può essere mergiato solo se **tutti** i job completano con successo.

## Artifacts

- `coverage-report`: Coverage XML report (retention: 30 giorni)

## Troubleshooting

### Job Fallisce

1. Verifica i log del job fallito in GitHub Actions
2. Esegui localmente il comando che ha fallito:

   ```bash
   # Linting
   uv run ruff check .
   uv run ruff format --check .

   # Type checking
   uv run mypy core ingestion docling_mcp utils --ignore-missing-imports

   # Testing
   uv run pytest --cov=core --cov=ingestion --cov=docling_mcp --cov=utils --cov-report=term-missing --cov-fail-under=70 tests/unit/

   # Docker build
   docker build -f Dockerfile -t docling-rag-agent:test .
   docker build -f Dockerfile.api -t docling-rag-agent-api:test .
   ```

3. Risolvi i problemi localmente prima di fare push

### Coverage <70%

- Aggiungi test per codice non coperto
- Verifica coverage report: `coverage.xml` (artifact) o `htmlcov/index.html` (locale)

### Docker Build Fails

- Verifica che `Dockerfile` e `Dockerfile.api` siano corretti
- Testa build locale: `docker build -f Dockerfile .`
- Verifica dipendenze in `pyproject.toml`

### TruffleHog False Positives

- Aggiungi pattern a `.trufflehogignore`
- Verifica che non siano secrets reali prima di ignorare

## Riferimenti

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Pytest Coverage](https://pytest-cov.readthedocs.io/)
- [TruffleHog OSS](https://github.com/trufflesecurity/trufflehog)
- Story 4.1: `docs/stories/4/4-1/4-1-setup-github-actions-ci-cd.md`
