from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Request model for semantic search."""

    query: str = Field(..., description="The search query")
    limit: int = Field(5, ge=1, le=20, description="Maximum number of results to return")
    source_filter: Optional[str] = Field(
        None, description="Filter results by source document path/name"
    )


class SearchResult(BaseModel):
    """Single search result item."""

    content: str
    similarity: float
    source: str
    title: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response model for search results."""

    results: List[SearchResult]
    count: int
    processing_time_ms: float


class IngestRequest(BaseModel):
    """Request model to trigger ingestion."""

    clean_before_ingest: bool = Field(False, description="Whether to wipe DB before ingestion")
    fast_mode: bool = Field(False, description="Whether to use fast mode (no OCR)")
    documents_folder: str = Field("documents", description="Folder to scan for documents")


class IngestResponse(BaseModel):
    """Response model for ingestion trigger."""

    status: str
    message: str
    task_id: Optional[str] = None
