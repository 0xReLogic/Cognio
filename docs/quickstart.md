# Quick Start Guide

Get Cognio up and running in 5 minutes.

## Prerequisites

- Python 3.11 or higher
- Docker (optional, for container deployment)
- 1.1GB free disk space (for default multilingual embedding model)
  - Or 80MB if using lightweight model (all-MiniLM-L6-v2)

## Option 1: Docker (Recommended)

The fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/0xReLogic/Cognio.git
cd Cognio

# Start with docker-compose
docker-compose up -d

# Verify it's running
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

## Option 2: Manual Installation

### 1. Install Dependencies

```bash
# Clone the repository
git clone https://github.com/0xReLogic/Cognio.git
cd Cognio

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Run the Server

```bash
# Start the server
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

On first run, the server will download the embedding model:
- Default: `paraphrase-multilingual-mpnet-base-v2` (~1.1GB, best quality, 100+ languages)
- Alternative: Set `EMBED_MODEL=all-MiniLM-L6-v2` in `.env` (~80MB, faster, English-focused)

Model download takes about 30-60 seconds depending on your connection.

### 3. Verify Installation

```bash
# In another terminal
curl http://localhost:8080/health
```

## Your First Memory

### Save a Memory

```bash
curl -X POST http://localhost:8080/memory/save \
  -H "Content-Type: application/json" \
  -d '{
    "text": "FastAPI is a modern Python web framework for building APIs",
    "project": "LEARNING",
    "tags": ["python", "fastapi", "web"]
  }'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "saved": true,
  "reason": "created",
  "duplicate": false
}
```

### Search for It

```bash
curl "http://localhost:8080/memory/search?q=Python%20web%20framework&limit=3"
```

Response:
```json
{
  "query": "Python web framework",
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "text": "FastAPI is a modern Python web framework for building APIs",
      "score": 0.89,
      "project": "LEARNING",
      "tags": ["python", "fastapi", "web"],
      "created_at": "2025-01-05T10:30:00Z"
    }
  ],
  "total": 1
}
```

Notice how it found the memory even though you searched for "web framework" and the memory says "web framework"!

## Interactive API Documentation

Open your browser and go to:

**http://localhost:8080/docs**

You'll see the Swagger UI where you can:
- Browse all API endpoints
- Try out requests interactively
- See request/response schemas
- Download the OpenAPI spec

## Configuration

Create a `.env` file to customize settings:

```bash
# Copy the example
cp .env.example .env

# Edit with your preferred settings
nano .env
```

### Essential Settings

```bash
# Database location
DB_PATH=./data/memory.db

# Embedding model (choose based on your needs)
# Default: paraphrase-multilingual-mpnet-base-v2 (1.1GB, best quality, 100+ languages)
# Fast: all-MiniLM-L6-v2 (80MB, good for English)
EMBED_MODEL=paraphrase-multilingual-mpnet-base-v2
EMBED_DEVICE=cpu

# Server configuration
API_HOST=0.0.0.0
API_PORT=8080

# Search defaults
DEFAULT_SEARCH_LIMIT=5
SIMILARITY_THRESHOLD=0.7
```

### Optional: Auto-Tagging with LLM

Enable automatic tag generation using AI:

```bash
# Enable auto-tagging
AUTOTAG_ENABLED=true
LLM_PROVIDER=groq

# Groq API (FREE tier: 14,400 requests/day)
# Get key from: https://console.groq.com/keys
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=openai/gpt-oss-120b

# Or use OpenAI (paid)
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your-openai-key-here
# OPENAI_MODEL=gpt-4o-mini
```

### Optional: Text Summarization

```bash
# Enable summarization (default: enabled)
SUMMARIZATION_ENABLED=true

# Method: extractive (fast, no API) or abstractive (better quality, uses LLM)
SUMMARIZATION_METHOD=extractive
```

### Optional: API Authentication

```bash
# Require API key for all requests
API_KEY=your-secret-key-here
```

## Next Steps

### More Examples

Check out the `examples/` directory:
- `examples/basic_usage.py` - Python SDK examples
- `examples/curl_examples.sh` - Command-line examples
- `examples/mcp_config.json` - MCP client configuration

### Full Documentation

- [API Documentation](api.md) - Complete API reference
- [Examples](examples.md) - More use cases and patterns
- [README](../README.md) - Full project documentation

### MCP Integration

To use Cognio with AI clients (Claude Desktop, Cursor, VS Code Copilot, etc):

**Auto-Setup (Recommended):**

```bash
cd mcp-server
npm run setup
```

This automatically configures all 9 supported AI clients:
- Claude Desktop
- Claude Code (CLI)
- VS Code (GitHub Copilot)
- Cursor
- Continue.dev
- Cline
- Windsurf
- Kiro
- Gemini CLI

**Manual Setup:**

See [mcp-server/README.md](../mcp-server/README.md) for client-specific configuration examples.

**After Setup:**

1. Restart your AI client
2. Cognio auto-generates `cognio.md` in your workspace with usage guide
3. Try: `"Search my memories for Docker"` or `"Remember this: FastAPI is awesome"`

### Troubleshooting

**Server won't start?**
- Check if port 8080 is already in use: `lsof -i :8080`
- Try a different port: `API_PORT=8081 uvicorn src.main:app --host 0.0.0.0 --port 8081`

**Can't find saved memories?**
- Check the database exists: `ls -lh data/memory.db`
- Verify with stats endpoint: `curl http://localhost:8080/memory/stats`

**Slow searches?**
- Lower the similarity threshold: `?threshold=0.5`
- Use project filters: `?project=YOUR_PROJECT`

**Need help?**
- [GitHub Issues](https://github.com/0xReLogic/Cognio/issues)
- [GitHub Discussions](https://github.com/0xReLogic/Cognio/discussions)

## What's Next?

Now that you have Cognio running:

1. **Save your first real memories** - Notes, code snippets, learnings
2. **Organize with projects** - Group related memories together
3. **Tag effectively** - Use consistent tags for better filtering
4. **Explore search** - Try semantic queries to find memories by meaning
5. **Export your data** - Backup to JSON or Markdown anytime

Happy remembering! 🧠
