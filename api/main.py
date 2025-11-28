import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.models import IngestRequest, IngestResponse, SearchRequest, SearchResponse, SearchResult
from core.rag_service import (
    close_global_embedder,
    initialize_global_embedder,
    search_knowledge_base_structured,
)
from ingestion.ingest import DocumentIngestionPipeline, IngestionConfig
from utils.db_utils import close_database, get_document, initialize_database, list_documents

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("🚀 Starting RAG API Service...")
    try:
        await initialize_database()
        logger.info("✓ Database initialized")

        # Initialize embedder in background
        asyncio.create_task(initialize_global_embedder())
        logger.info("✓ Embedder initialization started")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("🔄 Shutting down RAG API Service...")
    await close_global_embedder()
    await close_database()
    logger.info("✓ Resources cleaned up")


app = FastAPI(
    title="Docling RAG API",
    description="API Service for Document Ingestion and Semantic Search",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": time.time()}


@app.post("/v1/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Semantic search endpoint.
    """
    try:
        result = await search_knowledge_base_structured(
            query=request.query, limit=request.limit, source_filter=request.source_filter
        )

        # Map to response model
        search_results = [
            SearchResult(
                content=r["content"],
                similarity=r["similarity"],
                source=r["source"],
                title=r["title"],
                metadata=r["metadata"],
            )
            for r in result["results"]
        ]

        return SearchResponse(
            results=search_results,
            count=len(search_results),
            processing_time_ms=result["timing"].get("total_ms", 0),
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/documents")
async def get_documents(limit: int = 100, offset: int = 0):
    """
    List documents in the knowledge base.
    """
    try:
        docs = await list_documents(limit=limit, offset=offset)
        return {"documents": docs, "count": len(docs)}
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/documents/{document_id}")
async def get_document_by_id(document_id: str):
    """
    Get a specific document by ID.
    Returns the full document content and metadata.
    """
    try:
        doc = await get_document(document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        return doc
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/overview")
async def get_overview():
    """
    Get a high-level overview of the knowledge base.
    Returns summary statistics and document list.
    """
    try:
        docs = await list_documents(limit=100, offset=0)

        # Calculate statistics
        total_documents = len(docs)
        total_chunks = sum(doc.get("chunk_count", 0) for doc in docs)
        sources = list(set(doc.get("source", "") for doc in docs))

        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "unique_sources": len(sources),
            "sources": sorted(sources),
            "documents": [
                {
                    "id": doc["id"],
                    "title": doc["title"],
                    "source": doc["source"],
                    "chunk_count": doc.get("chunk_count", 0),
                    "updated_at": doc.get("updated_at"),
                }
                for doc in docs
            ],
        }
    except Exception as e:
        logger.error(f"Failed to get overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_ingestion_task(request: IngestRequest):
    """Background task for ingestion."""
    logger.info(f"Starting ingestion task for {request.documents_folder}")
    try:
        config = IngestionConfig()  # Use defaults or load from env

        pipeline = DocumentIngestionPipeline(
            config=config,
            documents_folder=request.documents_folder,
            clean_before_ingest=request.clean_before_ingest,
            fast_mode=request.fast_mode,
        )

        await pipeline.initialize()
        results = await pipeline.ingest_documents()
        await pipeline.close()

        logger.info(f"Ingestion completed: {len(results)} documents processed")

    except Exception as e:
        logger.error(f"Ingestion task failed: {e}")


@app.post("/v1/ingest", response_model=IngestResponse)
async def trigger_ingestion(request: IngestRequest, background_tasks: BackgroundTasks):
    """
    Trigger document ingestion in the background.
    """
    try:
        background_tasks.add_task(run_ingestion_task, request)
        return IngestResponse(
            status="accepted",
            message="Ingestion task started in background",
            task_id="ingest-" + str(int(time.time())),
        )
    except Exception as e:
        logger.error(f"Failed to trigger ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
