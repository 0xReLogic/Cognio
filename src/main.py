"""FastAPI application for Cognio server."""

import asyncio
import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import db
from .embeddings import embedding_service
from .memory import memory_service
from .metrics import metrics_service
from .models import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    DeleteMemoryResponse,
    ListMemoriesResponse,
    SaveMemoryRequest,
    SaveMemoryResponse,
    SearchMemoryResponse,
    StatsResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from .summarization import summarize

# Configure logging
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
_INTERNAL_SERVER_ERROR = "Internal server error"
_FILTER_BY_PROJECT_DESC = "Filter by project"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Cognio server...")
    settings.ensure_db_dir()
    db.connect()
    embedding_service.load_model()

    # Start periodic cache save task
    async def periodic_cache_save():
        while True:
            await asyncio.sleep(300)  # Save every 5 minutes
            try:
                embedding_service.save_cache()
            except Exception as e:
                logger.error(f"Error in periodic cache save: {e}")

    cache_task = asyncio.create_task(periodic_cache_save())
    logger.info("Server ready!")

    yield

    # Shutdown
    logger.info("Shutting down...")
    cache_task.cancel()
    embedding_service.save_cache()
    db.close()


# Create FastAPI app
app = FastAPI(
    title="Cognio",
    description="Persistent semantic memory server for MCP",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Web UI
web_ui_path = Path(__file__).parent.parent / "web-ui"
if web_ui_path.exists():
    app.mount("/ui", StaticFiles(directory=str(web_ui_path), html=True), name="ui")
    logger.info("Web UI available at /ui")


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing."""
    start_time = time.time()
    error = False

    try:
        response = await call_next(request)
        if response.status_code >= 400:
            error = True
        return response
    except Exception as e:
        error = True
        logger.error(f"Request error: {e}")
        raise
    finally:
        process_time = time.time() - start_time
        metrics_service.record_request(
            endpoint=f"{request.method} {request.url.path}",
            response_time=process_time,
            error=error,
        )


# Optional API key security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str | None = Security(api_key_header)) -> bool:
    """Verify API key if configured."""
    if settings.api_key and (not api_key or api_key != settings.api_key):
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return True


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "Cognio",
        "version": "0.1.0",
        "description": "Persistent semantic memory server for MCP",
    }


@app.post("/memory/save", response_model=SaveMemoryResponse)
async def save_memory(
    request: SaveMemoryRequest, authenticated: bool = Security(verify_api_key)
) -> SaveMemoryResponse:
    """
    Save a new memory.

    Args:
        request: Memory data with text, optional project and tags

    Returns:
        SaveMemoryResponse with memory ID and status
    """
    try:
        memory_id, is_duplicate, reason = memory_service.save_memory(request)
        return SaveMemoryResponse(id=memory_id, saved=True, reason=reason, duplicate=is_duplicate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving memory: {e}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR)


@app.get("/memory/search", response_model=SearchMemoryResponse)
async def search_memory(
    q: str = Query(..., description="Search query"),
    project: str | None = Query(None, description=_FILTER_BY_PROJECT_DESC),
    tags: str | None = Query(None, description="Comma-separated tags"),
    limit: int = Query(5, ge=1, le=50, description="Maximum results"),
    threshold: float = Query(0.7, ge=0.0, le=1.0, description="Minimum similarity score"),
    after_date: str | None = Query(None, description="Filter memories after date (ISO 8601)"),
    before_date: str | None = Query(None, description="Filter memories before date (ISO 8601)"),
) -> SearchMemoryResponse:
    """
    Search memories using semantic similarity.

    Args:
        q: Search query text
        project: Optional project filter
        tags: Comma-separated tags to filter
        limit: Maximum number of results
        threshold: Minimum similarity score
        after_date: Filter memories after this date
        before_date: Filter memories before this date

    Returns:
        SearchMemoryResponse with matching memories
    """
    try:
        # Parse tags if provided
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        results = memory_service.search_memory(
            query=q,
            project=project,
            tags=tag_list,
            limit=limit,
            threshold=threshold,
            after_date=after_date,
            before_date=before_date,
        )

        return SearchMemoryResponse(query=q, results=results, total=len(results))
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR)


@app.get("/memory/list", response_model=ListMemoriesResponse)
async def list_memories(
    project: str | None = Query(None, description=_FILTER_BY_PROJECT_DESC),
    tags: str | None = Query(None, description="Comma-separated tags"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("date", pattern="^(date|relevance)$", description="Sort order"),
    q: str | None = Query(None, description="Query for relevance sorting"),
) -> ListMemoriesResponse:
    """
    List all memories with pagination.

    Args:
        project: Optional project filter
        tags: Comma-separated tags to filter
        page: Page number (1-indexed)
        limit: Items per page
        sort: Sort order (date or relevance)
        q: Query text for relevance sorting

    Returns:
        ListMemoriesResponse with paginated memories
    """
    try:
        # Parse tags if provided
        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        memories, total = memory_service.list_memories(
            project=project, tags=tag_list, page=page, limit=limit, sort=sort, search_query=q
        )

        total_pages = (total + limit - 1) // limit

        return ListMemoriesResponse(
            memories=memories, page=page, total_pages=total_pages, total_items=total
        )
    except Exception as e:
        logger.error(f"Error listing memories: {e}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR)


@app.delete("/memory/{memory_id}", response_model=DeleteMemoryResponse)
async def delete_memory(
    memory_id: str, authenticated: bool = Security(verify_api_key)
) -> DeleteMemoryResponse:
    """
    Delete a memory by ID (hard delete).

    Args:
        memory_id: Memory UUID

    Returns:
        DeleteMemoryResponse with status
    """
    try:
        deleted = memory_service.delete_memory(memory_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Memory not found")
        return DeleteMemoryResponse(deleted=True, id=memory_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR)


@app.post("/memory/{memory_id}/archive", response_model=DeleteMemoryResponse)
async def archive_memory(
    memory_id: str, authenticated: bool = Security(verify_api_key)
) -> DeleteMemoryResponse:
    """
    Archive a memory by ID (soft delete).

    Archived memories are excluded from search and list operations
    but not permanently deleted from the database.

    Args:
        memory_id: Memory UUID

    Returns:
        DeleteMemoryResponse with status
    """
    try:
        from .database import db

        archived = db.archive_memory(memory_id)
        if not archived:
            raise HTTPException(status_code=404, detail="Memory not found or already archived")
        return DeleteMemoryResponse(deleted=True, id=memory_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving memory: {e}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR)


@app.post("/memory/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_memories(
    request: BulkDeleteRequest, authenticated: bool = Security(verify_api_key)
) -> BulkDeleteResponse:
    """
    Bulk delete memories.

    Args:
        request: Bulk delete criteria (project, before_date)

    Returns:
        BulkDeleteResponse with count of deleted memories
    """
    try:
        count = memory_service.bulk_delete(project=request.project, before_date=request.before_date)
        return BulkDeleteResponse(deleted_count=count)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error bulk deleting memories: {e}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR)


@app.get("/memory/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """
    Get memory statistics.

    Returns:
        StatsResponse with statistics
    """
    try:
        stats = memory_service.get_stats()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR)


@app.get("/memory/export", response_model=None)
async def export_memories(
    format: str = Query("json", pattern="^(json|markdown)$", description="Export format"),
    project: str | None = Query(None, description=_FILTER_BY_PROJECT_DESC),
) -> JSONResponse | PlainTextResponse:
    """
    Export memories to JSON or Markdown.

    Args:
        format: Export format (json or markdown)
        project: Optional project filter

    Returns:
        Exported data
    """
    try:
        data = memory_service.export_memories(format=format, project=project)

        if format == "json":
            return JSONResponse(content=data)
        else:
            return PlainTextResponse(content=data, media_type="text/markdown")
    except Exception as e:
        logger.error(f"Error exporting memories: {e}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/memory/summarize", response_model=SummarizeResponse)
async def summarize_text(request: SummarizeRequest) -> SummarizeResponse:
    """
    Summarize long text using extractive or abstractive methods.

    Args:
        request: Text to summarize and number of sentences

    Returns:
        SummarizeResponse with generated summary and metadata
    """
    try:
        summary = summarize(request.text, num_sentences=request.num_sentences)

        original_words = len(request.text.split())
        summary_words = len(summary.split())

        # Determine method used
        method = "abstractive" if summary_words < request.num_sentences * 10 else "extractive"

        return SummarizeResponse(
            summary=summary,
            original_length=original_words,
            summary_length=summary_words,
            method=method,
        )
    except Exception as e:
        logger.error(f"Error summarizing text: {e}")
        raise HTTPException(status_code=500, detail=_INTERNAL_SERVER_ERROR)


@app.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """
    Get server metrics and statistics.

    Returns:
        Metrics data including request counts, response times, and endpoint stats
    """
    return metrics_service.get_stats()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
