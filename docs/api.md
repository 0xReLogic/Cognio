# API Documentation

Complete reference for all Cognio API endpoints.

**Base URL**: `http://localhost:8080`

## Table of Contents

- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Health Check](#health-check)
  - [Save Memory](#save-memory)
  - [Search Memories](#search-memories)
  - [List Memories](#list-memories)
  - [Delete Memory](#delete-memory)
  - [Archive Memory](#archive-memory)
  - [Bulk Delete](#bulk-delete)
  - [Statistics](#statistics)
  - [Export](#export)
  - [Summarize Text](#summarize-text)
- [Data Models](#data-models)
- [Error Handling](#error-handling)

## Authentication

Optional API key authentication can be enabled by setting the `API_KEY` environment variable.

When enabled, protected endpoints require the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secret-key-here" ...
```

**Protected endpoints**: `/memory/save`, `/memory/{id}`, `/memory/{id}/archive`, `/memory/bulk-delete`

**Public endpoints**: `/health`, `/memory/search`, `/memory/list`, `/memory/stats`, `/memory/export`

## Endpoints

### Health Check

Check if the server is running.

**Endpoint**: `GET /health`

**Authentication**: None

**Response**:
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

**Example**:
```bash
curl http://localhost:8080/health
```

---

### Save Memory

Store a new memory with automatic embedding generation and duplicate detection.

**Endpoint**: `POST /memory/save`

**Authentication**: Required (if API_KEY is set)

**Request Body**:
```json
{
  "text": "Your memory text here",
  "project": "PROJECT_NAME",
  "tags": ["tag1", "tag2"]
}
```

**Parameters**:
- `text` (string, required): Memory content (max 10,000 characters)
- `project` (string, optional): Project identifier for organization
- `tags` (array of strings, optional): Tags for categorization

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "saved": true,
  "reason": "created",
  "duplicate": false
}
```

**Fields**:
- `id`: UUID of the memory
- `saved`: Always `true` if successful
- `reason`: `"created"` for new, `"duplicate"` if already exists
- `duplicate`: `true` if identical text already saved

**Example**:
```bash
curl -X POST http://localhost:8080/memory/save \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "text": "QRIS refund requires webhook callback validation",
    "project": "SENTINEL",
    "tags": ["qris", "refund", "webhook"]
  }'
```

---

### Search Memories

Semantic search based on meaning, not exact keyword matching.

**Endpoint**: `POST /memory/search`

**Authentication**: None

**Request Body**:
```json
{
  "query": "search query",
  "project": "PROJECT_NAME",
  "tags": ["tag1"],
  "limit": 5,
  "threshold": 0.7,
  "after_date": "2025-01-01",
  "before_date": "2025-12-31"
}
```

**Parameters**:
- `query` (string, required): Search query
- `project` (string, optional): Filter by project
- `tags` (array, optional): Filter by tags (any match)
- `limit` (integer, optional): Max results (default: 5, max: 100)
- `threshold` (float, optional): Min similarity score 0-1 (default: 0.7)
- `after_date` (string, optional): Filter memories after this date (ISO 8601)
- `before_date` (string, optional): Filter memories before this date (ISO 8601)

**Response**:
```json
{
  "query": "search query",
  "results": [
    {
      "id": "550e8400-...",
      "text": "Memory content",
      "score": 0.89,
      "project": "PROJECT",
      "tags": ["tag1", "tag2"],
      "created_at": "2025-01-05T10:30:00Z"
    }
  ],
  "total": 1
}
```

**Example**:
```bash
# Basic search
curl -X POST http://localhost:8080/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how to handle QRIS refunds", "limit": 3}'

# With filters
curl -X POST http://localhost:8080/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "webhook validation",
    "project": "SENTINEL",
    "tags": ["qris"],
    "after_date": "2025-01-01",
    "threshold": 0.6
  }'
```

---

### List Memories

Browse all memories with pagination and filtering.

**Endpoint**: `GET /memory/list`

**Authentication**: None

**Query Parameters**:
- `project` (string, optional): Filter by project
- `tags` (string, optional): Comma-separated tags
- `page` (integer, optional): Page number (default: 1)
- `limit` (integer, optional): Items per page (default: 20, max: 100)
- `sort` (string, optional): `"date"` or `"relevance"` (default: `"date"`)
- `q` (string, optional): Query for relevance sorting (required if sort=relevance)

**Response**:
```json
{
  "memories": [
    {
      "id": "550e8400-...",
      "text": "Memory content",
      "project": "PROJECT",
      "tags": ["tag1"],
      "created_at": "2025-01-05T10:30:00Z",
      "score": 0.85
    }
  ],
  "page": 1,
  "total_pages": 5,
  "total_items": 47
}
```

**Examples**:
```bash
# List all (first page)
curl "http://localhost:8080/memory/list"

# Filter by project
curl "http://localhost:8080/memory/list?project=SENTINEL&limit=10"

# Sort by relevance to query
curl "http://localhost:8080/memory/list?sort=relevance&q=payment&limit=20"

# Multiple filters
curl "http://localhost:8080/memory/list?project=LEARNING&tags=python,fastapi&page=2"
```

---

### Delete Memory

Permanently delete a memory by ID.

**Endpoint**: `DELETE /memory/{id}`

**Authentication**: Required (if API_KEY is set)

**Path Parameters**:
- `id`: Memory UUID

**Response**:
```json
{
  "deleted": true,
  "id": "550e8400-..."
}
```

**Errors**:
- `404`: Memory not found

**Example**:
```bash
curl -X DELETE http://localhost:8080/memory/550e8400-e29b-41d4-a716-446655440000 \
  -H "X-API-Key: your-key"
```

---

### Archive Memory

Soft delete a memory (excludes from search/list but doesn't delete permanently).

**Endpoint**: `POST /memory/{id}/archive`

**Authentication**: Required (if API_KEY is set)

**Path Parameters**:
- `id`: Memory UUID

**Response**:
```json
{
  "deleted": true,
  "id": "550e8400-..."
}
```

**Note**: Archived memories can be restored by database admin if needed.

**Example**:
```bash
curl -X POST http://localhost:8080/memory/550e8400-e29b-41d4-a716-446655440000/archive \
  -H "X-API-Key: your-key"
```

---

### Bulk Delete

Delete multiple memories matching criteria.

**Endpoint**: `POST /memory/bulk-delete`

**Authentication**: Required (if API_KEY is set)

**Request Body**:
```json
{
  "project": "OLD_PROJECT",
  "before_date": "2024-01-01"
}
```

**Parameters**:
- `project` (string, optional): Delete all memories in this project
- `before_date` (string, optional): Delete memories created before this date (ISO 8601)

**Response**:
```json
{
  "deleted_count": 23
}
```

**Example**:
```bash
# Delete all memories in a project
curl -X POST http://localhost:8080/memory/bulk-delete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"project": "OLD_PROJECT"}'

# Delete old memories
curl -X POST http://localhost:8080/memory/bulk-delete \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"before_date": "2024-01-01"}'
```

---

### Statistics

Get aggregate statistics about stored memories.

**Endpoint**: `GET /memory/stats`

**Authentication**: None

**Response**:
```json
{
  "total_memories": 142,
  "total_projects": 5,
  "storage_mb": 12.4,
  "by_project": {
    "SENTINEL": 47,
    "LEARNING": 32,
    "PERSONAL": 63
  },
  "top_tags": ["qris", "webhook", "api", "python", "fastapi"]
}
```

**Fields**:
- `total_memories`: Total count of active (non-archived) memories
- `total_projects`: Number of distinct projects
- `storage_mb`: Database file size in megabytes
- `by_project`: Memory count per project
- `top_tags`: Top 10 most used tags

**Example**:
```bash
curl http://localhost:8080/memory/stats
```

---

### Export

Export all memories to JSON or Markdown format.

**Endpoint**: `GET /memory/export`

**Authentication**: None

**Query Parameters**:
- `format` (string, required): `"json"` or `"markdown"`
- `project` (string, optional): Filter by project

**Response (JSON)**:
```json
{
  "memories": [
    {
      "id": "550e8400-...",
      "text": "Memory content",
      "project": "PROJECT",
      "tags": ["tag1", "tag2"],
      "created_at": "2025-01-05T10:30:00Z"
    }
  ]
}
```

**Response (Markdown)**:
```markdown
# Memory Export

## 550e8400-...
**Project**: SENTINEL
**Tags**: qris, refund
**Created**: 2025-01-05T10:30:00Z

QRIS refund requires webhook callback validation

---
```

**Examples**:
```bash
# Export to JSON
curl "http://localhost:8080/memory/export?format=json" > memories.json

# Export to Markdown
curl "http://localhost:8080/memory/export?format=markdown" > memories.md

# Export specific project
curl "http://localhost:8080/memory/export?format=json&project=SENTINEL" > sentinel.json
```

---

### Summarize Text

Summarize long text using extractive or abstractive methods.

**Endpoint**: `POST /memory/summarize`

**Authentication**: None

**Request Body**:
```json
{
  "text": "Long text to summarize here...",
  "num_sentences": 3
}
```

**Parameters**:
- `text` (string, required): Text to summarize (max 50,000 characters)
- `num_sentences` (integer, optional): Number of sentences in summary (1-10, default: 3)

**Response**:
```json
{
  "summary": "Summarized text here. Main points extracted. Concise overview provided.",
  "original_length": 245,
  "summary_length": 42,
  "method": "abstractive"
}
```

**Fields**:
- `summary`: Generated summary text
- `original_length`: Word count of original text
- `summary_length`: Word count of summary
- `method`: `"extractive"` (clustering-based) or `"abstractive"` (LLM-based)

**Notes**:
- Abstractive summarization requires LLM API key (Groq or OpenAI)
- Falls back to extractive if API unavailable
- Best for texts > 100 words
- Maintains semantic meaning while reducing length

**Example**:
```bash
curl -X POST http://localhost:8080/memory/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Artificial intelligence is transforming technology. Machine learning algorithms process vast amounts of data to identify patterns. Neural networks power breakthrough applications in image recognition and natural language processing.",
    "num_sentences": 2
  }'
```

**Response**:
```json
{
  "summary": "Artificial intelligence is revolutionizing technology through machine learning and neural networks. These technologies enable breakthrough applications in image recognition and natural language processing.",
  "original_length": 35,
  "summary_length": 24,
  "method": "abstractive"
}
```

---

## Data Models

### SaveMemoryRequest
```typescript
{
  text: string;          // Required, max 10000 chars
  project?: string;      // Optional project name
  tags?: string[];       // Optional tags array
}
```

### MemoryResult
```typescript
{
  id: string;            // UUID
  text: string;          // Memory content
  project: string | null;
  tags: string[];
  created_at: string;    // ISO 8601 timestamp
  score?: number;        // 0-1 similarity score (search only)
}
```

### SearchMemoryRequest
```typescript
{
  query: string;         // Required search query
  project?: string;
  tags?: string[];
  limit?: number;        // Default 5, max 100
  threshold?: number;    // Default 0.7, range 0-1
  after_date?: string;   // ISO 8601
  before_date?: string;  // ISO 8601
}
```

## Error Handling

### HTTP Status Codes

- `200 OK`: Successful request
- `400 Bad Request`: Invalid parameters or request body
- `403 Forbidden`: Invalid or missing API key
- `404 Not Found`: Memory not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "detail": "Error message description"
}
```

### Common Errors

**Text too long**:
```json
{
  "detail": "Field required: text exceeds maximum length of 10000"
}
```

**Invalid date format**:
```json
{
  "detail": "Invalid date format: expected ISO 8601"
}
```

**Missing API key**:
```json
{
  "detail": "Invalid or missing API key"
}
```

## Rate Limiting

Currently no rate limiting is enforced. For production deployments, consider adding:
- Per-IP rate limits
- API key quotas
- Request throttling

## Best Practices

### Saving Memories

1. **Keep text concise**: Shorter memories (< 500 chars) search faster
2. **Use consistent projects**: Stick to a naming convention (UPPERCASE, snake_case, etc)
3. **Tag wisely**: 3-5 relevant tags per memory is optimal
4. **Avoid duplicates**: Check search results before saving identical content

### Searching

1. **Start broad**: Use general queries, then filter with project/tags
2. **Adjust threshold**: Lower (0.5-0.6) for more results, higher (0.8-0.9) for precision
3. **Use date filters**: Narrow down large result sets with time ranges
4. **Semantic queries**: Ask questions naturally ("how to X") instead of keywords

### Performance

1. **Pagination**: Use reasonable limit values (10-50 items)
2. **Project filters**: Always filter by project when possible
3. **Export wisely**: Export by project for large databases
4. **Regular cleanup**: Archive or delete old/irrelevant memories

## Interactive Documentation

For a live, interactive API explorer, visit:

**http://localhost:8080/docs**

Features:
- Try all endpoints without writing code
- See real-time request/response examples
- Download OpenAPI specification
- View complete schemas

## SDKs and Tools

### Python SDK Example

```python
import requests

class CognioClient:
    def __init__(self, base_url="http://localhost:8080", api_key=None):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key} if api_key else {}
    
    def save(self, text, project=None, tags=None):
        response = requests.post(
            f"{self.base_url}/memory/save",
            json={"text": text, "project": project, "tags": tags or []},
            headers=self.headers
        )
        return response.json()
    
    def search(self, query, limit=5, **kwargs):
        response = requests.post(
            f"{self.base_url}/memory/search",
            json={"query": query, "limit": limit, **kwargs}
        )
        return response.json()

# Usage
client = CognioClient(api_key="your-key")
client.save("FastAPI is great", project="LEARNING", tags=["python"])
results = client.search("Python framework")
```

See `examples/basic_usage.py` for more examples.

## Support

- **Issues**: [GitHub Issues](https://github.com/0xReLogic/Cognio/issues)
- **Discussions**: [GitHub Discussions](https://github.com/0xReLogic/Cognio/discussions)
- **Documentation**: [README](../README.md)
