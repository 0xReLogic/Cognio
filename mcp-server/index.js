#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.dirname(__dirname);

// Auto-generate cognio.md file for AI context
import fs from 'fs';
const cognioMdPath = path.join(workspaceRoot, 'cognio.md');
const cognioContent = `# Cognio Memory System

This workspace has access to **Cognio** - a semantic memory system via MCP.

## Available Tools (12 total)

### Core Memory Operations
- **save_memory** - Save text with optional project/tags
- **search_memory** - Semantic search across memories
- **list_memories** - Browse all memories with filters
- **get_memory** - Get full content of a specific memory by ID
- **get_memory_stats** - Get statistics and insights
- **archive_memory** - Soft delete a memory by ID
- **delete_memory** - Permanently delete a memory
- **export_memories** - Export to JSON or Markdown

### Project Context Management
- **set_active_project** - Set active project (auto-applies to operations)
- **get_active_project** - Check current active project
- **list_projects** - See all available projects with memory counts

### Utilities
- **summarize_text** - Summarize long text (extractive/abstractive)

## Usage

Use these tools naturally when:
- User asks about past work ("what did we do before?")
- Solving problems worth remembering
- Need to recall project-specific context

## Active Project System

Set a project to auto-filter all operations:
\`\`\`
set_active_project("my-project")
save_memory("solution here")  // auto-saves to my-project
search_memory("past solution") // auto-searches in my-project only
\`\`\`

Keep memories organized by project to avoid context mixing.
`;

try {
  fs.writeFileSync(cognioMdPath, cognioContent, 'utf8');
} catch (error) {
  // Silent fail - not critical
}

// Auto-setup: Generate settings for all AI clients (silent mode)
try {
  const setupScript = path.join(workspaceRoot, 'scripts', 'setup-clients.js');
  execSync(`node "${setupScript}"`, { stdio: 'pipe', cwd: workspaceRoot });
  // Silent - no console output to avoid terminal spam
} catch (error) {
  // Silent error handling
}

// Cognio API base URL and API Key
const COGNIO_API_URL = process.env.COGNIO_API_URL || "http://localhost:8080";
const COGNIO_API_KEY = process.env.COGNIO_API_KEY;

// Active project state (persists during MCP session)
let activeProject = null;

// Helper function to make API calls to Cognio
async function cognioRequest(endpoint, method = "GET", body = null) {
  const url = `${COGNIO_API_URL}${endpoint}`;
  const options = {
    method,
    headers: {
      "Content-Type": "application/json",
    },
  };

  // Add API key if provided
  if (COGNIO_API_KEY) {
    options.headers["X-API-Key"] = COGNIO_API_KEY;
  }

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Cognio API error: ${response.status} - ${error}`);
  }

  return response.json();
}

// Create MCP server
const server = new Server(
  {
    name: "cognio-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "save_memory",
        description: "Save information to long-term semantic memory with automatic tagging and categorization. Best practice: set an active project first with set_active_project to keep memories organized and avoid context mixing. If not using active project, you must provide a project parameter. Tags are optional — when auto-tagging is enabled and configured, tags will be generated automatically if not provided.",
        inputSchema: {
          type: "object",
          properties: {
            text: {
              type: "string",
              description: "The memory content to save",
            },
            project: {
              type: "string",
              description: "Project name to organize the memory (REQUIRED unless active project is set; RECOMMENDED: use current workspace/repo name or topic)",
            },
            tags: {
              type: "array",
              items: { type: "string" },
              description: "Optional tags for categorization (auto-generated if not provided)",
            },
            metadata: {
              type: "object",
              description: "Optional metadata as key-value pairs",
            },
          },
          required: ["text"],
        },
      },
      {
        name: "search_memory",
        description: "Search memories using semantic similarity. Use default (detailed=false) for quick exploration or when context is sufficient; it shows previews with IDs and saves input tokens. Use detailed=true only when you need the full text of results. For a specific item, use get_memory(id) after getting the ID from search. TIP: Filter by project to avoid mixing contexts from different workspaces.",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "Search query text",
            },
            project: {
              type: "string",
              description: "Filter by project name (RECOMMENDED to avoid cross-project results)",
            },
            tags: {
              type: "array",
              items: { type: "string" },
              description: "Optional tags to filter by",
            },
            limit: {
              type: "number",
              description: "Maximum number of results (default: 5)",
              default: 5,
            },
            detailed: {
              type: "boolean",
              description: "Return full text (true) or truncated preview with IDs (false, default). Use default to save input tokens; set true only when full text is necessary.",
              default: false,
            },
          },
          required: ["query"],
        },
      },
      {
        name: "list_memories",
        description: "List all memories with optional filtering. Best practice: set an active project first to avoid mixing contexts from different workspaces. Use default (full_text=false) for quick browsing; set full_text=true only when you need complete content. For many items, consider using search_memory with relevant keywords instead.",
        inputSchema: {
          type: "object",
          properties: {
            project: {
              type: "string",
              description: "Filter by project name (REQUIRED unless active project is set; RECOMMENDED to avoid cross-project results)",
            },
            tags: {
              type: "array",
              items: { type: "string" },
              description: "Filter by tags",
            },
            page: {
              type: "number",
              description: "Page number (1-indexed)",
              default: 1,
            },
            limit: {
              type: "number",
              description: "Maximum number of results",
              default: 20,
            },
            offset: {
              type: "number",
              description: "Number of results to skip (legacy; will be converted to page)",
              default: 0,
            },
            full_text: {
              type: "boolean",
              description: "If true, return full text in output (no truncation). Use default to save input tokens; set true only when full text is necessary.",
              default: false,
            },
          },
        },
      },
      {
        name: "get_memory_stats",
        description: "Get statistics about stored memories",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "archive_memory",
        description: "Archive (soft delete) a memory by ID",
        inputSchema: {
          type: "object",
          properties: {
            memory_id: {
              type: "string",
              description: "The ID of the memory to archive",
            },
          },
          required: ["memory_id"],
        },
      },
      {
        name: "summarize_text",
        description: "Summarize long text using extractive or abstractive methods",
        inputSchema: {
          type: "object",
          properties: {
            text: {
              type: "string",
              description: "The text to summarize",
            },
            num_sentences: {
              type: "number",
              description: "Number of sentences in summary (default: 3, max: 10)",
            },
          },
          required: ["text"],
        },
      },
      {
        name: "export_memories",
        description: "Export memories to JSON or Markdown format. Useful for backups or analyzing memory content.",
        inputSchema: {
          type: "object",
          properties: {
            format: {
              type: "string",
              description: "Export format: 'json' or 'markdown'",
              enum: ["json", "markdown"],
              default: "json",
            },
            project: {
              type: "string",
              description: "Optional: filter by project name",
            },
          },
        },
      },
      {
        name: "delete_memory",
        description: "Permanently delete a memory by ID. Use archive_memory instead for soft delete.",
        inputSchema: {
          type: "object",
          properties: {
            memory_id: {
              type: "string",
              description: "The ID of the memory to delete",
            },
          },
          required: ["memory_id"],
        },
      },
      {
        name: "set_active_project",
        description: "Set the active project context. All subsequent operations (save/search/list) will default to this project unless explicitly overridden. Like switching git branches - keeps you focused on one project at a time.",
        inputSchema: {
          type: "object",
          properties: {
            project: {
              type: "string",
              description: "Project name to activate (e.g., 'Helios-LoadBalancer', 'Cognio-Memory')",
            },
          },
          required: ["project"],
        },
      },
      {
        name: "get_active_project",
        description: "Get the currently active project context. Returns the project name that's currently active, or null if none set.",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "list_projects",
        description: "List all available projects in the database. Useful for discovering projects before setting one as active.",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "get_memory",
        description: "Get a single memory by ID to view its full content. Use this when you need to read the complete text of a specific memory.",
        inputSchema: {
          type: "object",
          properties: {
            memory_id: {
              type: "string",
              description: "The ID of the memory to retrieve",
            },
          },
          required: ["memory_id"],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "save_memory": {
        // Require either explicit project or active project
        if (!args.project && !activeProject) {
          return {
            content: [
              {
                type: "text",
                text: "ERROR: Must set active project first or specify project parameter.\n\nUse set_active_project(\"project-name\") to enable memory operations.",
              },
            ],
            isError: true,
          };
        }
        
        console.error(`[Cognio] Saving memory to project: ${args.project || activeProject}`);
        const result = await cognioRequest("/memory/save", "POST", {
          text: args.text,
          project: args.project || activeProject,
          tags: args.tags,
          metadata: args.metadata,
        });
        console.error(`[Cognio] Memory saved successfully - ID: ${result.id}`);
        
        let message = JSON.stringify(result, null, 2);
        if (!args.project && activeProject) {
          message += `\n\n[INFO] Auto-saved to active project: ${activeProject}`;
        }
        
        return {
          content: [
            {
              type: "text",
              text: message,
            },
          ],
        };
      }

      case "search_memory": {
        // Require active project for search
        if (!activeProject && !args.project) {
          return {
            content: [
              {
                type: "text",
                text: "ERROR: Must set active project first or specify project parameter.\n\nUse set_active_project(\"project-name\") to search memories.",
              },
            ],
            isError: true,
          };
        }

        const projectToUse = args.project || activeProject;
        const detailed = args.detailed === true;
        console.error(`[Cognio] Searching memories - query: "${args.query}", project: ${projectToUse}, detailed: ${detailed}`);
        const params = new URLSearchParams({
          q: args.query,
          limit: String(args.limit || 5),
        });
        if (projectToUse) params.append("project", projectToUse);
        if (args.tags && args.tags.length > 0) {
          params.append("tags", args.tags.join(","));
        }

        const result = await cognioRequest(`/memory/search?${params}`);
        console.error(`[Cognio] Search completed - found ${result.total} results`);
        
        // Format results nicely
        let response = projectToUse && !args.project 
          ? `[Active Project: ${projectToUse}]\nFound ${result.total} memories:\n\n`
          : `Found ${result.total} memories:\n\n`;
          
        result.results.forEach((mem, idx) => {
          const scoreText = typeof mem.score === 'number' ? mem.score.toFixed(3) : 'N/A';
          response += `${idx + 1}. [Score: ${scoreText}] [ID: ${mem.id}]\n`;
          // Truncate text if not detailed
          const preview = detailed ? mem.text : `${mem.text.substring(0, 120)}${mem.text.length > 120 ? '…' : ''}`;
          response += `   Text: ${preview}\n`;
          if (mem.project) response += `   Project: ${mem.project}\n`;
          if (mem.tags && mem.tags.length > 0) {
            response += `   Tags: ${mem.tags.join(", ")}\n`;
          }
          response += `   Created: ${mem.created_at}\n`;
          if (!detailed) {
            response += `   (Use get_memory("${mem.id}") for full text)\n`;
          }
          response += `\n`;
        });
        if (!detailed) {
          response += `Tip: Use detailed=true for full text or get_memory(id) for specific items.`;
        }

        return {
          content: [
            {
              type: "text",
              text: response,
            },
          ],
        };
      }

      case "list_memories": {
        // Require active project for list
        if (!activeProject && !args.project) {
          return {
            content: [
              {
                type: "text",
                text: "ERROR: Must set active project first or specify project parameter.\n\nUse set_active_project(\"project-name\") to list memories.",
              },
            ],
            isError: true,
          };
        }

        const projectToUse = args.project || activeProject;
        const limit = Number.isFinite(args?.limit) ? Number(args.limit) : 20;
        const page = Number.isFinite(args?.page)
          ? Number(args.page)
          : (Number.isFinite(args?.offset) ? Math.floor(Number(args.offset) / limit) + 1 : 1);
        const params = new URLSearchParams({
          limit: String(limit),
          page: String(page),
          sort: "date",
        });
        if (projectToUse) params.append("project", projectToUse);
        if (args.tags && args.tags.length > 0) {
          params.append("tags", args.tags.join(","));
        }

        const result = await cognioRequest(`/memory/list?${params}`);
        
        const total = (typeof result.total_items === 'number') ? result.total_items : (result.total ?? 0);
        let response = projectToUse && !args.project
          ? `[Active Project: ${projectToUse}]\nTotal: ${total} memories (page ${result.page} of ${result.total_pages}, showing ${result.memories.length})\n\n`
          : `Total: ${total} memories (page ${result.page} of ${result.total_pages}, showing ${result.memories.length})\n\n`;
          
        result.memories.forEach((mem, idx) => {
          const text = args.full_text ? mem.text : `${mem.text.substring(0, 100)}${mem.text.length > 100 ? '...' : ''}`;
          response += `${idx + 1}. ${text}\n`;
          if (mem.project) response += `   Project: ${mem.project}\n`;
          if (mem.tags && mem.tags.length > 0) {
            response += `   Tags: ${mem.tags.join(", ")}\n`;
          }
          response += `   ID: ${mem.id}\n\n`;
        });

        return {
          content: [
            {
              type: "text",
              text: response,
            },
          ],
        };
      }

      case "get_memory_stats": {
        const result = await cognioRequest("/memory/stats");
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "archive_memory": {
        const result = await cognioRequest(
          `/memory/${args.memory_id}/archive`,
          "POST"
        );
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "summarize_text": {
        const result = await cognioRequest("/memory/summarize", "POST", {
          text: args.text,
          num_sentences: args.num_sentences || 3,
        });
        
        const response = `Summary:\n${result.summary}\n\nStats:\n- Original: ${result.original_length} words\n- Summary: ${result.summary_length} words\n- Method: ${result.method}`;
        
        return {
          content: [
            {
              type: "text",
              text: response,
            },
          ],
        };
      }

      case "export_memories": {
        const format = args.format || "json";
        const params = new URLSearchParams();
        if (args.project) params.append("project", args.project);
        params.append("format", format);

        const url = `${COGNIO_API_URL}/memory/export?${params}`;
        const options = {
          method: "GET",
          headers: {},
        };

        // Add API key if provided
        if (COGNIO_API_KEY) {
          options.headers["X-API-Key"] = COGNIO_API_KEY;
        }

        const response = await fetch(url, options);

        if (!response.ok) {
          throw new Error(`Export failed: ${response.statusText}`);
        }

        const exportData = await response.text();
        return {
          content: [
            {
              type: "text",
              text: `[EXPORT] Format: ${format}\n${args.project ? `Project: ${args.project}\n` : ''}\n${exportData}`,
            },
          ],
        };
      }

      case "delete_memory": {
        const result = await cognioRequest(`/memory/${args.memory_id}`, "DELETE");
        return {
          content: [
            {
              type: "text",
              text: `[OK] Memory ${args.memory_id} permanently deleted`,
            },
          ],
        };
      }

      case "set_active_project": {
        activeProject = args.project;
        return {
          content: [
            {
              type: "text",
              text: `[OK] Active project set to: ${activeProject}\n\nAll save/search/list operations will now default to this project unless you specify a different one.`,
            },
          ],
        };
      }

      case "get_active_project": {
        return {
          content: [
            {
              type: "text",
              text: activeProject 
                ? `Current active project: ${activeProject}` 
                : `No active project set. Use set_active_project to activate one.`,
            },
          ],
        };
      }

      case "list_projects": {
        const stats = await cognioRequest("/memory/stats");
        const projectsObj = stats.memories_by_project || {};
        const entries = Object.entries(projectsObj);
        const list = entries
          .sort((a, b) => b[1] - a[1])
          .map(([name, count]) => ({ name, count }));

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(list),
            },
          ],
        };
      }

      case "get_memory": {
        console.error(`[Cognio] Retrieving memory by ID: ${args.memory_id}`);
        const result = await cognioRequest(`/memory/${args.memory_id}`);
        
        let response = `Memory Details:\n\n`;
        response += `ID: ${result.id}\n`;
        response += `Text: ${result.text}\n`;
        if (result.project) response += `Project: ${result.project}\n`;
        if (result.tags && result.tags.length > 0) {
          response += `Tags: ${result.tags.join(", ")}\n`;
        }
        response += `Created: ${new Date(result.created_at * 1000).toISOString()}\n`;
        response += `Updated: ${new Date(result.updated_at * 1000).toISOString()}\n`;
        
        return {
          content: [
            {
              type: "text",
              text: response,
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // Silent mode - no console output
}

main().catch((error) => {
  // Silent error handling
  process.exit(1);
});
