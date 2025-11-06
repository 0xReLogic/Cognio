# Cognio MCP Server

MCP (Model Context Protocol) server wrapper for Cognio semantic memory.

## Quick Setup

Run the auto-setup script to configure all supported AI clients:

```bash
npm run setup
```

This automatically generates MCP configurations for:
- Claude Desktop
- Cursor
- Continue.dev
- Cline
- Windsurf
- Kiro
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

## Available Tools

### save_memory
Save information to long-term semantic memory with automatic tagging.

Parameters:
- `text` (required): The memory content
- `project` (optional): Project name for organization
- `tags` (optional): Array of tags (auto-generated if not provided)
- `metadata` (optional): Key-value metadata object

### search_memory
Search memories using semantic similarity.

Parameters:
- `query` (required): Search query text
- `project` (optional): Filter by project
- `tags` (optional): Filter by tags array
- `limit` (optional): Max results (default: 5)

### list_memories
List all memories with optional filtering.

Parameters:
- `project` (optional): Filter by project
- `tags` (optional): Filter by tags array
- `limit` (optional): Max results (default: 20)
- `offset` (optional): Skip results (default: 0)

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

## Requirements

- Node.js >= 18
- Cognio server running (default: http://localhost:8080)
