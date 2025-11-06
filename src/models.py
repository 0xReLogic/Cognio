"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field

# Constants
_FILTER_BY_PROJECT_DESC = "Filter by project"


# Request models
class SaveMemoryRequest(BaseModel):
    """Request to save a new memory."""

    text: str = Field(..., max_length=10000, description="Memory text content")
    project: str | None = Field(None, max_length=100, description="Project name")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")


class SearchMemoryParams(BaseModel):
    """Parameters for searching memories."""

    q: str = Field(..., description="Search query")
    project: str | None = Field(None, description=_FILTER_BY_PROJECT_DESC)
    tags: str | None = Field(None, description="Comma-separated tags")
    limit: int = Field(5, ge=1, le=50, description="Maximum results")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity score")


class ListMemoriesParams(BaseModel):
    """Parameters for listing memories."""

    project: str | None = Field(None, description=_FILTER_BY_PROJECT_DESC)
    tags: str | None = Field(None, description="Comma-separated tags")
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    sort: str = Field("date", pattern="^(date|relevance)$", description="Sort order")


class BulkDeleteRequest(BaseModel):
    """Request to bulk delete memories."""

    project: str | None = Field(None, description="Delete by project")
    before_date: str | None = Field(None, description="Delete before date (ISO 8601)")


class ExportParams(BaseModel):
    """Parameters for exporting memories."""

    format: str = Field("json", pattern="^(json|markdown)$", description="Export format")
    project: str | None = Field(None, description=_FILTER_BY_PROJECT_DESC)


class SummarizeRequest(BaseModel):
    """Request to summarize text."""

    text: str = Field(..., max_length=50000, description="Text to summarize")
    num_sentences: int = Field(3, ge=1, le=10, description="Number of sentences in summary")


# Response models
class SaveMemoryResponse(BaseModel):
    """Response from saving a memory."""

    id: str = Field(..., description="Memory UUID")
    saved: bool = Field(..., description="Whether save was successful")
    reason: str = Field(..., description="Status reason (created/duplicate)")
    duplicate: bool = Field(..., description="Whether this is a duplicate")


class MemoryResult(BaseModel):
    """A single memory search result."""

    id: str
    text: str
    summary: str | None = None
    score: float | None = None
    project: str | None = None
    tags: list[str]
    created_at: str


class SearchMemoryResponse(BaseModel):
    """Response from searching memories."""

    query: str
    results: list[MemoryResult]
    total: int


class ListMemoriesResponse(BaseModel):
    """Response from listing memories."""

    memories: list[MemoryResult]
    page: int
    total_pages: int
    total_items: int


class DeleteMemoryResponse(BaseModel):
    """Response from deleting a memory."""

    deleted: bool
    id: str


class BulkDeleteResponse(BaseModel):
    """Response from bulk deleting memories."""

    deleted_count: int


class StatsResponse(BaseModel):
    """Response with memory statistics."""

    total_memories: int
    total_projects: int
    storage_mb: float
    by_project: dict[str, int]
    top_tags: list[str]


class SummarizeResponse(BaseModel):
    """Response from summarizing text."""

    summary: str = Field(..., description="Generated summary")
    original_length: int = Field(..., description="Original text word count")
    summary_length: int = Field(..., description="Summary word count")
    method: str = Field(..., description="Summarization method used (extractive/abstractive)")


# Internal models
class Memory(BaseModel):
    """Internal memory representation."""

    id: str
    text: str
    summary: str | None = None
    text_hash: str
    embedding: list[float] | None = None
    project: str | None = None
    tags: list[str]
    created_at: int
    updated_at: int
