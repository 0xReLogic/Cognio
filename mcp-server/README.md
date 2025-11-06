# Cognio MCP Server

MCP (Model Context Protocol) server wrapper for Cognio semantic memory.

## Installation

```bash
npm install -g cognio-mcp-server
```

Or use directly with npx:

```bash
npx cognio-mcp-server
```

## Usage

Add to your MCP configuration (e.g., `.vscode/mcp.json`):

```json
{
  "servers": {
    "cognio": {
      "command": "npx",
      "args": [
        "-y",
        "cognio-mcp-server"
      ],
      "env": {
        "COGNIO_API_URL": "http://localhost:8080"
      }
    }
  }
}
```

Or use local path during development:

```json
{
  "servers": {
    "cognio": {
      "command": "node",
      "args": [
        "/workspaces/Cognio/mcp-server/index.js"
      ],
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

## Environment Variables

- `COGNIO_API_URL`: Base URL for Cognio API (default: http://localhost:8080)

## Requirements

- Node.js >= 18
- Cognio server running (default: http://localhost:8080)
