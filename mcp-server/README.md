# Cognio MCP Server

MCP (Model Context Protocol) server wrapper for Cognio semantic memory.

## Quick Setup

Run the auto-setup script to configure all supported AI clients:

```bash
npm run setup
```

This automatically generates MCP configurations for:
- Claude Desktop
- Claude Code (CLI)
- Cursor
- Continue.dev
- Cline
- Windsurf
- Kiro
- VS Code (GitHub Copilot)
- Gemini CLI

## Manual Configuration

If you prefer to configure manually, add Cognio to your client's MCP config:

### VS Code (GitHub Copilot)

Add to `.vscode/mcp.json`:
```json
{
  "servers": {
    "cognio": {
      "command": "node",
      "args": ["/path/to/Cognio/mcp-server/index.js"],
      "env": {
        "COGNIO_API_URL": "http://localhost:8080"
      }
    }
  }
}
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or `%APPDATA%/Claude/claude_desktop_config.json` (Windows):
```json
{
  "mcpServers": {
    "cognio": {
      "command": "node",
      "args": ["/path/to/Cognio/mcp-server/index.js"],
      "env": {
        "COGNIO_API_URL": "http://localhost:8080"
      }
    }
  }
}
```

### Cursor

Add to `~/.cursor/mcp_settings.json`:
```json
{
  "mcpServers": {
    "cognio": {
      "command": "node",
      "args": ["/path/to/Cognio/mcp-server/index.js"],
      "env": {
        "COGNIO_API_URL": "http://localhost:8080"
      }
    }
  }
}
```

### Continue.dev

Add to `~/.continue/config.json`:
```json
{
  "mcpServers": [
    {
      "name": "cognio",
      "command": "node",
      "args": ["/path/to/Cognio/mcp-server/index.js"],
      "env": {
        "COGNIO_API_URL": "http://localhost:8080"
      }
    }
  ]
}
```

### Cline

Add to `~/.cline/mcp.json`:
```json
{
  "mcpServers": {
    "cognio": {
      "command": "node",
      "args": ["/path/to/Cognio/mcp-server/index.js"],
      "env": {
        "COGNIO_API_URL": "http://localhost:8080"
      }
    }
  }
}
```

### Windsurf

Add to `~/.windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "cognio": {
      "command": "node",
      "args": ["/path/to/Cognio/mcp-server/index.js"],
      "env": {
        "COGNIO_API_URL": "http://localhost:8080"
      }
    }
  }
}
```

### Kiro

Add to `~/.kiro/settings/mcp.json`:
```json
{
  "mcpServers": {
    "cognio": {
      "command": "node",
      "args": ["/path/to/Cognio/mcp-server/index.js"],
      "env": {
        "COGNIO_API_URL": "http://localhost:8080"
      }
    }
  }
}
```

### Gemini CLI

Add to `~/gemini/settings.json`:
```json
{
  "mcpServers": {
    "cognio": {
      "command": "node",
      "args": ["/path/to/Cognio/mcp-server/index.js"],
      "env": {
        "COGNIO_API_URL": "http://localhost:8080"
      }
    }
  }
}
```

### Claude Code (CLI)

Add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "cognio": {
      "type": "stdio",
      "command": "node",
      "args": ["/path/to/Cognio/mcp-server/index.js"],
      "env": {
        "COGNIO_API_URL": "http://localhost:8080"
      }
    }
  }
}
```

Note: Claude Code requires `"type": "stdio"` in the config.

## Available Tools

### save_memory
Save information to long-term semantic memory with automatic tagging and categorization.

Parameters:
- `text` (required): The memory content to save
- `project` (optional): Project name for organization. Either provide this or use set_active_project first
- `tags` (optional): Array of tags. If omitted and auto-tagging is enabled with a valid LLM API key (GROQ_API_KEY or OPENAI_API_KEY), tags will be auto-generated
- `metadata` (optional): Key-value metadata object

Notes:
- A project is required (either via parameter or active project context)
- Auto-tagging requires: AUTOTAG_ENABLED=true and a configured LLM API key in .env
- If auto-tagging is disabled or misconfigured, memory saves without tags

### search_memory
Search memories using semantic similarity.

Parameters:
- `query` (required): Search query text
- `project` (optional): Filter by project. If omitted, uses active project (required)
- `tags` (optional): Filter by tags array
- `limit` (optional): Max results (default: 5)

Notes:
- A project context is required (either via parameter or set_active_project)
- Similarity threshold is configurable via SIMILARITY_THRESHOLD in .env (default: 0.4)

### list_memories
List all memories with optional filtering.

Parameters:
- `project` (optional): Filter by project. If omitted, uses active project (required)
- `tags` (optional): Filter by tags array
- `limit` (optional): Max results (default: 20)
- `offset` (optional): Skip results (default: 0)

Notes:
- A project context is required (either via parameter or set_active_project)

### get_memory_stats
Get statistics about stored memories.

No parameters required.

### archive_memory
Archive (soft delete) a memory by ID.

Parameters:
- `memory_id` (required): The memory ID to archive

### delete_memory
Permanently delete a memory by ID.

Parameters:
- `memory_id` (required): The memory ID to delete

### export_memories
Export memories to JSON or Markdown format.

Parameters:
- `format` (optional): Export format - 'json' or 'markdown' (default: json)
- `project` (optional): Filter by project name

### summarize_text
Summarize long text using extractive or abstractive methods.

Parameters:
- `text` (required): The text to summarize
- `num_sentences` (optional): Number of sentences in summary (default: 3, max: 10)

### set_active_project
Set the active project context for all subsequent operations.

Parameters:
- `project` (required): Project name to activate

### get_active_project
Get the currently active project context.

No parameters required.

### list_projects
List all available projects in the database.

No parameters required.

## Environment Variables

- `COGNIO_API_URL`: Base URL for Cognio API (default: http://localhost:8080)

## Configuration

Auto-tagging and other features are configured via `.env` in the Cognio project root:

```bash
# Auto-tagging (requires LLM API key)
AUTOTAG_ENABLED=true
LLM_PROVIDER=groq
GROQ_API_KEY=your-key-here
GROQ_MODEL=openai/gpt-oss-120b

# Or use OpenAI instead
# OPENAI_API_KEY=your-key-here
# OPENAI_MODEL=gpt-3.5-turbo

# Semantic search threshold (lower = more results, default 0.4)
SIMILARITY_THRESHOLD=0.4

# Summarization
SUMMARIZATION_ENABLED=true
SUMMARIZATION_METHOD=abstractive
```

See `.env.example` in the Cognio root directory for complete configuration options.

## Requirements

- Node.js >= 18
- Cognio server running (default: http://localhost:8080)
