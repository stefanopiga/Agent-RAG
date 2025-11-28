# Guida allo Sviluppo

Questa guida fornisce informazioni dettagliate sull'architettura del progetto, pattern di sviluppo con FastMCP, testing con PydanticAI, e walkthrough dell'implementazione.

## Indice

- [Struttura del Progetto](#struttura-del-progetto)
- [Pattern FastMCP](#pattern-fastmcp)
- [Testing con PydanticAI](#testing-con-pydanticai)
- [Walkthrough Implementazione](#walkthrough-implementazione)

---

## Struttura del Progetto

### Organizzazione Directory

```
docling-rag-agent/
├── app.py                         # Interfaccia web Streamlit
├── docling_mcp/                   # MCP server per Cursor IDE (standalone)
├── core/
│   ├── agent.py                   # PydanticAI agent wrapper
│   └── rag_service.py             # Core RAG logic (decoupled)
├── api/
│   ├── main.py                    # FastAPI REST API
│   └── models.py                  # Modelli API
├── ingestion/
│   ├── ingest.py                  # Pipeline ingestione documenti
│   ├── embedder.py                # Generazione embedding con caching
│   └── chunker.py                 # Chunking intelligente (Docling HybridChunker)
├── utils/
│   ├── providers.py               # Configurazione modelli/client OpenAI
│   ├── db_utils.py                # Connection pooling ottimizzato
│   └── models.py                  # Modelli Pydantic per validazione
├── sql/
│   └── optimize_index.sql         # Schema completo + HNSW index ottimizzato
├── scripts/
│   ├── optimize_database.py       # Tool gestione index e performance
│   └── test_mcp_performance.py    # Performance test suite
├── guide/                         # Documentazione progetto
├── docs/                          # Documentazione BMAD workflow
├── documents/                     # Documenti per ingestione
└── tests/                         # Test suite
    ├── unit/                      # Unit tests
    └── integration/               # Integration tests
```

### Responsabilità Moduli

| Directory     | Responsabilità                                                    |
| ------------- | ----------------------------------------------------------------- |
| `core/`       | Business logic principale, agent RAG, servizio ricerca           |
| `api/`        | REST API per accesso programmatico                               |
| `mcp/`        | Server MCP per integrazione Cursor IDE                           |
| `ingestion/`  | Pipeline ingestione documenti, chunking, embedding               |
| `utils/`      | Utility condivise: configurazione, connessione DB, modelli       |
| `scripts/`    | Script operativi: ottimizzazione DB, test performance            |
| `guide/`      | Documentazione progetto (troubleshooting, development guide)     |
| `docs/`       | Documentazione workflow BMAD                                      |

---

## Pattern FastMCP

### Testabilità Unitaria con FastMCP 2.x

In FastMCP 2.x, i decoratori `@mcp.tool` e `@mcp.resource` trasformano le funzioni in oggetti (`FunctionTool`, `FunctionResource`).

```python
# FastMCP 2.x - NON funziona
@mcp.tool
def add(a: int, b: int) -> int:
    return a + b

print(add(1, 2))  # TypeError: 'FunctionTool' object is not callable
```

### Soluzioni per Testing

#### A) Accesso alla Funzione Originale tramite `.fn`

```python
# Accesso diretto alla funzione wrappata
result = add.fn(1, 2)  # Funziona
```

#### B) Approccio Raccomandato: Test via Client

```python
import pytest
from fastmcp.client import Client
from my_project.main import mcp

@pytest.fixture
async def main_mcp_client():
    async with Client(transport=mcp) as mcp_client:
        yield mcp_client

@pytest.mark.parametrize("a, b, expected", [(1, 2, 3), (2, 3, 5)])
async def test_add(a: int, b: int, expected: int, main_mcp_client: Client):
    result = await main_mcp_client.call_tool(
        name="add",
        arguments={"x": a, "y": b}
    )
    assert result.data == expected
```

Configurazione pytest richiesta in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Risorse Dinamiche vs Tools

| Concetto      | Semantica                                                                                              |
| ------------- | ------------------------------------------------------------------------------------------------------ |
| **Resources** | Rappresentano dati che un server MCP vuole rendere disponibili ai client (file, schemi DB, info app) |
| **Tools**     | Rappresentano operazioni dinamiche che possono modificare lo stato o interagire con sistemi esterni   |

#### Quando Usare Resources

Una lista di documenti generata dinamicamente da query DB **può essere esposta come Resource** se:

1. È read-only
2. Non ha side-effects
3. Rappresenta "lo stato corrente" di una collezione

```python
@mcp.resource("documents://{document_id}")
def get_document(document_id: str) -> dict:
    return db.query(f"SELECT * FROM docs WHERE id = {document_id}")
```

#### Quando Usare Tools

Preferire Tool se:

- L'operazione richiede parametri di filtro complessi
- L'operazione ha effetti collaterali
- Vuoi che l'LLM possa "invocare" l'operazione attivamente

**Nota Critica:** Dalla documentazione Cursor: "Resources are not yet supported in Cursor." Se il client è Cursor, **usare Tools** è l'unica opzione funzionante.

### Gestione Errori e Propagazione al Client

#### Meccanismo di Default

FastMCP converte automaticamente le eccezioni in risposte MCP error:

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP(name="Server", mask_error_details=True)

@mcp.tool
def divide(a: float, b: float) -> float:
    if b == 0:
        # Questo messaggio arriva SEMPRE al client
        raise ToolError("Division by zero is not allowed.")
    
    try:
        result = a / b
        if result > 1000000:
            # Con mask_error_details=True, questo diventa messaggio generico
            raise ValueError("Result too large")
        return result
    except Exception as e:
        raise ToolError("Calculation failed") from e
```

#### Comportamento con `mask_error_details`

| `mask_error_details` | `ToolError`        | Altre Eccezioni              |
| -------------------- | ------------------ | ---------------------------- |
| `False` (default)    | Messaggio visibile | Messaggio visibile           |
| `True`               | Messaggio visibile | Messaggio generico mascherato |

#### Logging verso il Client

Usare il `Context` per inviare log strutturati al client MCP:

```python
from fastmcp import FastMCP, Context

@mcp.tool
async def risky_operation(ctx: Context) -> dict:
    try:
        await ctx.info("Starting operation")
        result = await db.execute(...)
        await ctx.info("Operation completed")
        return result
    except DatabaseError as e:
        await ctx.error(f"Database error: {e}")
        raise ToolError("Database operation failed")
```

#### Codici Errore MCP Standard

Per errori critici (DB down), usare i codici JSON-RPC standard:

- `-32002`: Resource not found
- `-32602`: Invalid params
- `-32603`: Internal error

### Raccomandazioni FastMCP

1. **Testing**: Usare `.fn` per unit test rapidi, Client fixture per integration test completi
2. **Resources vs Tools**: Dato che Cursor non supporta Resources, convertire `documents://list` in un Tool `list_documents()`
3. **Errori**: Usare `ToolError` per messaggi espliciti, `mask_error_details=True` in produzione, Context logging per debug

---

## Testing con PydanticAI

### Panoramica

Testing in PydanticAI segue patterns standard Python con strumenti specializzati per evitare chiamate reali a LLM durante i test.

#### Stack Testing Raccomandato

| Tool                      | Scopo                                              |
| ------------------------- | -------------------------------------------------- |
| `pytest`                  | Test harness                                       |
| `inline-snapshot`         | Assertions lunghe                                  |
| `dirty-equals`            | Comparazione strutture dati complesse              |
| `TestModel`               | Mock model per sostituire LLM reali                |
| `FunctionModel`           | Mock model con logica custom                       |
| `Agent.override()`        | Mock model/dependencies/toolsets                   |
| `ALLOW_MODEL_REQUESTS`    | Blocca chiamate accidentali a LLM                  |

### TestModel

`TestModel` è un mock model per testing che:

- Chiama automaticamente tutti i tool dell'agent
- Genera risposte deterministiche (testo o structured output)
- **NON usa ML/AI** - solo codice Python procedurale
- Genera dati validi che soddisfano JSON schema dei tool registrati

```python
from pydantic_ai.models.test import TestModel

# Basic usage
test_model = TestModel()

# Con custom output text
test_model = TestModel(custom_output_text='Sunny')
```

**Limitazioni:**

- Dati generati sono "fake" e non semanticamente corretti
- Usa hardcoded values (es. date nel passato)
- Per testing realistico, usa `FunctionModel` con custom logic

### Agent.override()

```python
import pytest
from pydantic_ai.models.test import TestModel
from weather_app import weather_agent

async def test_forecast():
    # Override model con TestModel
    with weather_agent.override(model=TestModel()):
        prompt = 'What will the weather be like in London on 2024-11-28?'
        result = await weather_agent.run(prompt)
        
    # Assert sul risultato
    assert result.data == expected_data
```

### Pytest Fixture Pattern

```python
# test_agent.py
import pytest
from pydantic_ai.models.test import TestModel
from weather_app import weather_agent

@pytest.fixture
def override_weather_agent():
    with weather_agent.override(model=TestModel()):
        yield

async def test_forecast(override_weather_agent: None):
    # TestModel già attivo qui
    result = await weather_agent.run('test prompt')
    assert result.data == expected
```

### capture_run_messages()

Catturare e ispezionare messaggi scambiati tra agent e model:

```python
from pydantic_ai import capture_run_messages

with capture_run_messages() as messages:
    with weather_agent.override(model=TestModel()):
        result = await weather_agent.run('test prompt')

# Inspect tool calls
assert messages[1].parts[0].tool_name == 'weather_forecast'
assert messages[1].parts[0].args == {'location': 'London'}
```

### ALLOW_MODEL_REQUESTS

Safety measure per bloccare globalmente richieste a modelli non-test:

```python
from pydantic_ai import models

# A livello modulo (top del file test)
models.ALLOW_MODEL_REQUESTS = False
```

#### Pattern conftest.py

```python
# conftest.py
import pytest
from pydantic_ai import models

@pytest.fixture(autouse=True)
def disable_real_model_requests():
    """Disable real LLM requests globally for all tests."""
    original = models.ALLOW_MODEL_REQUESTS
    models.ALLOW_MODEL_REQUESTS = False
    yield
    models.ALLOW_MODEL_REQUESTS = original
```

### FunctionModel - Testing Avanzato

Per test che richiedono valori specifici o logica custom:

```python
import re
from pydantic_ai import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

def call_weather_forecast(
    messages: list[ModelMessage], 
    info: AgentInfo
) -> ModelResponse:
    """Custom function per generare tool calls realistici."""
    if len(messages) == 1:
        # First call: extract date from prompt
        user_prompt = messages[0].parts[-1]
        m = re.search(r'\d{4}-\d{2}-\d{2}', user_prompt.content)
        assert m is not None
        
        # Call weather_forecast tool con date estratta
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name='weather_forecast',
                    args={'location': 'London', 'date': m.group()}
                )
            ]
        )
    else:
        # Second call: return final response
        return ModelResponse(
            parts=[TextPart(content='Forecast result')]
        )

async def test_forecast_future():
    from weather_app import weather_agent
    
    with weather_agent.override(model=FunctionModel(call_weather_forecast)):
        result = await weather_agent.run('Weather for 2024-12-25?')
        
    # Ora il tool viene chiamato con date futura!
    assert '2024-12-25' in result.data
```

### Testing Checklist

```
✅ Setup
- [ ] ALLOW_MODEL_REQUESTS = False
- [ ] pytest.mark.anyio per async tests
- [ ] TestModel override configurato

✅ Test Coverage
- [ ] Agent logic (TestModel)
- [ ] Tool calls (capture_run_messages)
- [ ] Tool integration (FunctionModel)
- [ ] Error handling
- [ ] Dependency mocking

✅ Assertions
- [ ] Response data validation
- [ ] Tool call parameters
- [ ] Message exchange sequence
- [ ] Side effects (DB writes, etc.)
```

### Gotchas/Warnings Comuni

#### 1. TestModel Hardcoded Values

```python
# ❌ TestModel genera date nel passato
# Tool chiamato con: {'date': '2020-01-01'}

# ✅ Usa FunctionModel per date specifiche
def custom_model(...):
    return ToolCallPart(args={'date': '2024-12-25'})
```

#### 2. ALLOW_MODEL_REQUESTS Dimenticato

```python
# ❌ Senza safety flag
async def test_agent():
    # Se override fallisce, chiama OpenAI API! 💸

# ✅ Con safety flag
models.ALLOW_MODEL_REQUESTS = False
async def test_agent():
    # Fallisce subito se override mancante
```

#### 3. capture_run_messages Scope

```python
# ❌ Cattura fuori scope
with capture_run_messages() as messages:
    pass
await agent.run('test')  # Non catturato!

# ✅ Cattura dentro scope
with capture_run_messages() as messages:
    await agent.run('test')  # ✅ Catturato
```

#### 4. Pytest Async Setup

```python
# ❌ Senza anyio
async def test_agent():  # Non eseguito!
    pass

# ✅ Con anyio
pytestmark = pytest.mark.anyio
async def test_agent():  # ✅ Eseguito
    pass
```

### Link Documentazione Ufficiale

**PydanticAI Testing Documentation:**

- Main: https://ai.pydantic.dev/testing/
- TestModel: https://ai.pydantic.dev/api/models/test/#pydantic_ai.models.test.TestModel
- FunctionModel: https://ai.pydantic.dev/api/models/function/#pydantic_ai.models.function.FunctionModel
- Agent.override: https://ai.pydantic.dev/api/agent/#pydantic_ai.agent.Agent.override
- capture_run_messages: https://ai.pydantic.dev/api/messages/#pydantic_ai.capture_run_messages
- ALLOW_MODEL_REQUESTS: https://ai.pydantic.dev/api/models/#pydantic_ai.models.ALLOW_MODEL_REQUESTS

**Testing Tools:**

- pytest: https://docs.pytest.org/en/stable/
- inline-snapshot: https://15r10nk.github.io/inline-snapshot/latest/
- dirty-equals: https://dirty-equals.helpmanual.io/latest/
- anyio: https://anyio.readthedocs.io/en/stable/

---

## Walkthrough Implementazione

### Refactoring e Implementazione MCP Server

Questo progetto è stato refactorizzato per supportare sia Streamlit che MCP (Model Context Protocol).

### 1. Core Logic Decoupling

La logica core RAG è stata estratta in un package `core` separato:

- **`core/rag_service.py`**: Contiene la logica pura per la ricerca nella knowledge base, indipendente da qualsiasi framework agent.
- **`core/agent.py`**: Wrappa il `rag_service` per uso con PydanticAI (usato da Streamlit).

### 2. MCP Server Implementation

Il modulo **`docling_mcp/`** usa la libreria `FastMCP`:

- `docling_mcp/server.py`: FastMCP instance con tool registration
- `docling_mcp/lifespan.py`: Gestisce il lifecycle delle risorse (DB pool, embedder)
- `docling_mcp/tools/`: Tools organizzati per dominio (search.py, documents.py, overview.py)

Tools disponibili:
- `query_knowledge_base`: Ricerca semantica nella knowledge base
- `ask_knowledge_base`: Domande con risposta formattata
- `list_knowledge_base_documents`: Lista documenti
- `get_knowledge_base_document`: Dettagli documento per ID
- `get_knowledge_base_overview`: Statistiche knowledge base

### 3. Application Updates

- **`app.py`**: Aggiornato per importare l'agent da `core.agent`
- **`pyproject.toml`**: Aggiunta dipendenza `fastmcp`
- **`rag_agent.py`**: Eliminato (sostituito da `core/agent.py`)

### Come Usare

#### Running the MCP Server (Cursor / Claude Desktop)

1. Assicurati di avere le dipendenze installate:

   ```bash
   uv sync
   ```

2. Configura il tuo editor. È stato creato un file **`claude_desktop_config.json`** nella root.

   - **Per Cursor**: Vai a Settings > Features > MCP. Aggiungi un nuovo server con:
     - Type: `stdio`
     - Command: `uv`
     - Args: `run --project /path/to/docling-rag-agent python -m docling_mcp.server`
     
   - **Per Claude Desktop**: Copia i contenuti di `claude_desktop_config.json` nel tuo file di configurazione.

#### Running the Streamlit App

Il workflow esistente rimane invariato:

```bash
streamlit run app.py
```

### Verifica

- **Streamlit**: L'app dovrebbe funzionare esattamente come prima, poiché l'interfaccia `core.agent` corrisponde al vecchio `rag_agent`.
- **MCP**: Il server espone `query_knowledge_base` che accetta `query`, `limit`, e `source_filter`.

---

## Best Practices Generali

### Code Quality

1. **Type Hints**: Usa sempre type hints per parametri e return types
2. **Docstrings**: Documenta tutte le funzioni pubbliche con docstrings
3. **Error Handling**: Cattura eccezioni specifiche, non generiche
4. **Logging**: Usa logging strutturato per debug e monitoring

### Performance

1. **Connection Pooling**: Usa il connection pool per database
2. **Embedding Cache**: L'embedder ha cache LRU per query frequenti
3. **HNSW Index**: Usa HNSW invece di IVFFlat per ricerche vettoriali

### Testing

1. **Unit Tests**: Testa business logic con mock models
2. **Integration Tests**: Testa interazioni componenti con FunctionModel
3. **ALLOW_MODEL_REQUESTS=False**: Sempre attivo per evitare chiamate API accidentali

