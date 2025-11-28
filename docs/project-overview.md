# Project Overview - docling-rag-agent

## What is docling-rag-agent?

Un sistema RAG (Retrieval Augmented Generation) intelligente che trasforma documenti in una knowledge base conversazionale. Gli utenti possono fare domande in linguaggio naturale e ricevere risposte accurate con citazioni delle fonti, supportate da ricerca semantica su embeddings vettoriali.

## Key Features

### 🔍 Semantic Search
- Vector similarity search usando PGVector (cosine distance)
- OpenAI embeddings (text-embedding-3-small, 1536 dimensions)
- Source filtering per ricerche mirate

### 📚 Multi-Format Support
- **Text:** Markdown, TXT
- **PDF:** Conversione via Docling
- **Office:** Word (.docx), PowerPoint (.pptx), Excel (.xlsx)
- **Web:** HTML


### 💬 Interactive Interfaces
- **Streamlit UI:** Web chat interface con cronologia
- **MCP Server:** Integrazione Cursor/Claude Desktop

### 🎯 Intelligent Chunking
- **HybridChunker:** Token-aware, structure-preserving
- Contestualizzazione automatica (heading hierarchy)
- Chunking semantico per migliore retrieval

### 🚀 Production-Ready
- Docker containerization
- Connection pooling (AsyncPG)
- Batch processing
- Error handling robusto

## Project Type

- **Category:** Backend RAG Application
- **Architecture:** Monolith (service-oriented)
- **Language:** Python 3.10+
- **Framework:** PydanticAI + Streamlit
- **Database:** PostgreSQL + PGVector (Supabase)

## Tech Stack Summary

| Component | Technology |
|-----------|------------|
| Language | Python 3.11 |
| Agent Framework | PydanticAI 0.7.4+ |
| UI | Streamlit 1.31+ |
| Document Processing | Docling 2.55+ |
| Vector DB | PostgreSQL + PGVector |
| LLM | OpenAI GPT-4o-mini |
| Embeddings | text-embedding-3-small |
| MCP | FastMCP 0.1+ |
| Package Manager | UV |
| Deployment | Docker + Compose |

## Repository Structure

```
docling-rag-agent/
├── core/               # RAG business logic
├── ingestion/          # Document processing pipeline
├── utils/              # Database & configuration
├── sql/                # PostgreSQL schema
├── documents/          # Documents to ingest
├── app.py              # Streamlit entry point
├── mcp_server.py       # MCP server entry point
├── pyproject.toml      # Dependencies
├── Dockerfile          # Container definition
└── docker-compose.yml  # Multi-service orchestration
```

## Quick Stats

- **Lines of Code:** ~2,500+ (excluding dependencies)
- **Main Components:** 12 Python modules
- **Database Tables:** 2 (documents, chunks)
- **Docker Services:** 2 (UI, ingestion)
- **Supported Formats:** 7+ file types
- **API Integrations:** 2 (OpenAI LLM + Embeddings)

## Use Cases

### 1. Internal Documentation Search
Organizzazioni possono indicizzare manuali interni, policy, procedure e permettere ricerca conversazionale ai dipendenti.

### 2. Technical Documentation Assistant
Developer possono caricare documentazione tecnica (API docs, guides) e fare domande specifiche durante lo sviluppo.

### 3. Research Paper Analysis
Ricercatori possono indicizzare paper accademici e fare query semantiche su concetti, metodologie, risultati.

### 4. Customer Support Knowledge Base
Team di supporto possono interrogare documentazione prodotto per risposte rapide a ticket clienti.

### 5. Legal Document Review
Avvocati possono ricercare clausole specifiche, precedenti, riferimenti normativi in grandi corpus legali.

## Architecture Highlights

### Layered Design
- **Presentation:** Streamlit + MCP Server
- **Application:** PydanticAI Agent + RAG Service
- **Service:** Embedder + Chunker + DB Utils
- **Data:** PostgreSQL + PGVector

### Key Patterns
- **Service Layer Pattern:** Core logic decoupled da frameworks
- **Connection Pooling:** AsyncPG (5-20 connections)
- **Pipeline Pattern:** Ingestion orchestration
- **Tool-based Agent:** PydanticAI tool registration

### Data Flow
```
Documents → Docling → HybridChunker → Embeddings → PostgreSQL
                                                          ↓
User Query → Agent → RAG Service → Vector Search → Response + Sources
```

## Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL con PGVector (o Supabase account)
- OpenAI API key

### Installation
```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with DATABASE_URL and OPENAI_API_KEY

# Setup database
psql $DATABASE_URL < sql/schema.sql

# Ingest documents
uv run python -m ingestion.ingest --documents documents/

# Run Streamlit UI
uv run streamlit run app.py
```

### Docker Deployment
```bash
# Start UI
docker-compose up -d rag-agent

# Run ingestion
docker-compose --profile ingestion up ingestion
```

## Performance Characteristics

### Ingestion Speed
- **PDF:** ~2-5 secondi per pagina
- **Office:** ~1-3 secondi per documento
- **Batch:** 100 texts embedded per API call
- **Throughput:** ~10-20 documenti/minuto (depending on size)

### Query Speed
- **Embedding:** ~100-200ms (OpenAI API)
- **Vector Search:** ~10-50ms (PGVector with index)
- **Total Latency:** ~200-500ms per query
- **Concurrent Users:** 10-20 (con default connection pool)

### Storage
- **Embeddings:** 1536 floats × 4 bytes = 6KB per chunk
- **Average Document:** 50-100 chunks = 300-600KB
- **1000 Documents:** ~300-600MB (vectors only)
- **PostgreSQL:** GIN + IVFFlat indexes add ~30% overhead

## Limitations & Considerations

### Current Limitations
- No multi-tenancy (single knowledge base)
- No real-time document updates (requires re-ingestion)
- No hybrid search (semantic only, no keyword)
- No document versioning


### Scalability Limits
- Single PostgreSQL instance (vertical scaling only)
- In-memory cache (not distributed)
- Connection pool per instance (not shared)
- IVFFlat index performance degrades >1M vectors

### API Dependencies
- OpenAI API required (no offline mode)
- Rate limits apply (tier-dependent)
- Cost per query: ~$0.0001-0.001 (embedding + LLM)

## Roadmap

### Short Term

- [ ] Document update/delete UI
- [ ] Metadata filtering in UI
- [ ] Export search results

### Medium Term
- [ ] Multi-user authentication
- [ ] Document versioning
- [ ] Hybrid search (semantic + keyword)
- [ ] Advanced analytics dashboard

### Long Term
- [ ] Multi-language support
- [ ] Distributed vector search (Qdrant/Weaviate)
- [ ] Real-time document sync
- [ ] GraphRAG capabilities

## Contributing

Contribuzioni benvenute! Areas needing help:
- Test coverage expansion
- Performance optimization
- Documentation improvements
- New document format support
- UI/UX enhancements

## License

[Specify license - not mentioned in codebase]

## Support

- **Issues:** GitHub Issues
- **Documentation:** `/docs` folder
- **Discussions:** GitHub Discussions

## Credits

Built with:
- [Docling](https://github.com/DS4SD/docling) - Document processing
- [PydanticAI](https://ai.pydantic.dev) - Agent framework
- [PGVector](https://github.com/pgvector/pgvector) - Vector similarity
- [Streamlit](https://streamlit.io) - Web UI
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP protocol

## Contact

[Specify contact information]

---

**Last Updated:** 2025-11-24
**Version:** 0.1.0
**Status:** Production-Ready

