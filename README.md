# Cognio

> Persistent semantic memory server for AI assistants via Model Context Protocol (MCP)

[![CI/CD](https://github.com/0xReLogic/Cognio/actions/workflows/ci.yml/badge.svg)](https://github.com/0xReLogic/Cognio/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.118.0-009688.svg)](https://fastapi.tiangolo.com)

Cognio is a Model Context Protocol (MCP) server that provides persistent semantic memory for AI assistants. Unlike ephemeral chat history, Cognio stores context permanently and enables semantic search across conversations.

**Built for:**
- Personal knowledge base that grows over time
- Multi-project context management
- Research notes and learning journal
- Conversation history with semantic retrieval

## Features

- **Semantic Search**: Find memories by meaning using sentence-transformers
- **Multilingual Support**: Search in 100+ languages seamlessly
- **Persistent Storage**: SQLite-based storage that survives across sessions
- **Project Organization**: Organize memories by project and tags
- **Auto-Tagging**: Automatic tag generation via LLM (GPT-4, Groq, etc)
- **Text Summarization**: Extractive and abstractive summarization for long texts
- **MCP Integration**: One-click setup for VS Code, Claude, Cursor, and more
- **RESTful API**: Standard HTTP API with OpenAPI documentation
- **Export Capabilities**: Export to JSON or Markdown format
- **Docker Support**: Simple deployment with docker-compose

## Quick Start

### 1. Start the Server

```bash
git clone https://github.com/0xReLogic/Cognio.git
cd Cognio
docker-compose up -d
```

Server runs at `http://localhost:8080`

### 2. Auto-Configure AI Clients

The MCP server automatically configures supported AI clients on first start:

**Supported Clients:**
- Claude Desktop
- Claude Code (CLI)
- VS Code (GitHub Copilot)
- Cursor
- Continue.dev
- Cline
- Windsurf
- Kiro
- Gemini CLI

**Quick Setup:**

Run the auto-setup script to configure all clients at once:
```bash
cd mcp-server
npm run setup
```

This generates MCP configs for all 9 supported clients automatically.

**Manual Configuration:**

See [mcp-server/README.md](mcp-server/README.md) for client-specific MCP configuration examples.

On first run, Cognio auto-generates `cognio.md` in your workspace with usage guide for AI tools.

### 3. Test It

```bash
# Save a memory
curl -X POST http://localhost:8080/memory/save \
  -H "Content-Type: application/json" \
  -d '{"text": "Docker allows running apps in containers", "project": "LEARNING"}'

# Search memories
curl "http://localhost:8080/memory/search?q=containers"
```

Or use naturally in your AI client:
```
"Search my memories for Docker information"
"Remember this: FastAPI is a modern Python web framework"
```

## Documentation

- **[API Reference](docs/api.md)** - Complete endpoint documentation
- **[Examples](docs/examples.md)** - Usage patterns and integrations
- **[Quickstart](docs/quickstart.md)** - Installation and configuration

## MCP Tools

When using the MCP server, you have access to 11 specialized tools:

| Tool | Description |
|------|-------------|
| `save_memory` | Save text with optional project/tags (auto-tagging enabled) |
| `search_memory` | Semantic search with project filtering |
| `list_memories` | List memories with pagination and filters |
| `get_memory_stats` | Get storage statistics and insights |
| `archive_memory` | Soft delete a memory (recoverable) |
| `delete_memory` | Permanently delete a memory by ID |
| `export_memories` | Export memories to JSON or Markdown |
| `summarize_text` | Summarize long text (extractive or LLM-based) |
| **`set_active_project`** | **Set active project context (auto-applies to all operations)** |
| **`get_active_project`** | **View currently active project** |
| **`list_projects`** | **List all available projects from database** |

**Active Project Workflow:**
```
1. list_projects() → See: Helios-LoadBalancer (45), Cognio-Memory (23), ...
2. set_active_project("Helios-LoadBalancer")
3. save_memory("Cache TTL is 300s") → Auto-saves to Helios-LoadBalancer
4. search_memory("cache settings") → Auto-searches in Helios-LoadBalancer only
5. list_memories() → Lists only Helios-LoadBalancer memories
```

**Project Isolation:**  
Always specify a `project` name OR use `set_active_project` to keep memories organized and prevent mixing contexts between different workspaces.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/memory/save` | Save new memory |
| POST | `/memory/search` | Semantic search |
| GET | `/memory/list` | List memories with filters |
| DELETE | `/memory/{id}` | Delete memory by ID |
| POST | `/memory/bulk-delete` | Bulk delete by project |
| GET | `/memory/stats` | Get statistics |
| GET | `/memory/export` | Export memories |
| POST | `/memory/summarize` | Summarize long text |

Interactive docs: http://localhost:8080/docs

## Configuration

Environment variables (see `.env.example`):

```bash
# Database
DB_PATH=./data/memory.db

# Embeddings
EMBED_MODEL=paraphrase-multilingual-mpnet-base-v2
EMBED_DEVICE=cpu

# API
API_HOST=0.0.0.0
API_PORT=8080
API_KEY=your-secret-key  # Optional

# Auto-tagging (Optional)
AUTOTAG_ENABLED=true
GROQ_API_KEY=your-groq-key
GROQ_MODEL=openai/gpt-oss-120b 
```

**Auto-Tagging Models:**
- `openai/gpt-oss-120b` - High quality 
- `gpt-4o-mini` - OpenAI, fast and cheap
- `llama-3.3-70b-versatile` - Groq, balanced
- `llama-3.1-8b-instant` - Groq, fastest

See `.env.example` for all available options and recommendations.

## Project Structure

```
cognio/
├── src/                # Core application
│   ├── main.py         # FastAPI app
│   ├── config.py       # Environment config
│   ├── models.py       # Data schemas
│   ├── database.py     # SQLite operations
│   ├── embeddings.py   # Semantic search
│   ├── memory.py       # Memory CRUD
│   ├── autotag.py      # Auto-tagging
│   └── utils.py        # Helpers
│
├── mcp-server/         # MCP integration
│   ├── index.js        # MCP server
│   └── package.json    # Dependencies
│
├── scripts/            # Utilities
│   ├── setup-clients.js  # Auto-config AI clients
│   ├── backup.sh       # Database backup
│   └── migrate.py      # Schema migrations
│
├── tests/              # Test suite
├── docs/               # Documentation
└── examples/           # Usage examples
```

## Development

```bash
# Install dependencies
poetry install

# Run tests
pytest

# Start development server
uvicorn src.main:app --reload
```

## Roadmap

**v0.2.0** (Current)
- [x] Auto-tagging with LLM
- [x] MCP auto-setup for 9 AI clients
- [x] LLM integration
- [x] Text summarization (extractive & abstractive)
- [ ] Web UI for memory management

**v1.0.0**
- [ ] Graph relationships (knowledge graph)
- [ ] Full-text search (hybrid)
- [ ] VSCode extension
- [ ] Obsidian sync

**v2.0.0**
- [ ] Multi-user support
- [ ] PostgreSQL backend option
- [ ] Distributed deployment

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Database**: SQLite with JSON support
- **Embeddings**: sentence-transformers (paraphrase-multilingual-mpnet-base-v2, 768-dim)
- **MCP Server**: Node.js, @modelcontextprotocol/sdk
- **Auto-Tagging**: Api
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Deployment**: Docker, docker-compose

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Save memory | ~20ms | Including embedding |
| Search (1k memories) | ~15ms | Semantic similarity |
| Search (10k memories) | ~50ms | Still fast |
| Model load | ~3s | One-time on startup |

Memory footprint: ~1.5GB RAM (model + app)

## License

MIT License - see [LICENSE](LICENSE)

## Links

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/0xReLogic/Cognio/issues)
- **Releases**: [GitHub Releases](https://github.com/0xReLogic/Cognio/releases)

---

Built for better AI conversations
