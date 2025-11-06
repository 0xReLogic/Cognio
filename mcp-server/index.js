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

// Auto-setup: Generate settings for all AI clients
try {
  const setupScript = path.join(workspaceRoot, 'scripts', 'setup-clients.js');
  execSync(`node "${setupScript}"`, { stdio: 'inherit', cwd: workspaceRoot });
  console.error('[OK] Auto-setup completed - all AI clients configured');
} catch (error) {
  console.error('[WARN] Auto-setup failed:', error.message);
}

// Cognio API base URL
const COGNIO_API_URL = process.env.COGNIO_API_URL || "http://localhost:8080";

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
        description: "Save information to long-term semantic memory with automatic tagging and categorization. IMPORTANT: Always specify a project name to keep memories organized and prevent mixing contexts.",
        inputSchema: {
          type: "object",
          properties: {
            text: {
              type: "string",
              description: "The memory content to save",
            },
            project: {
              type: "string",
              description: "Project name to organize the memory (RECOMMENDED: use current workspace/repo name or topic)",
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
        description: "Search memories using semantic similarity. TIP: Filter by project to avoid mixing contexts from different workspaces.",
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
          },
          required: ["query"],
        },
      },
      {
        name: "list_memories",
        description: "List all memories with optional filtering",
        inputSchema: {
          type: "object",
          properties: {
            project: {
              type: "string",
              description: "Filter by project name",
            },
            tags: {
              type: "array",
              items: { type: "string" },
              description: "Filter by tags",
            },
            limit: {
              type: "number",
              description: "Maximum number of results",
              default: 20,
            },
            offset: {
              type: "number",
              description: "Number of results to skip",
              default: 0,
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
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "save_memory": {
        const result = await cognioRequest("/memory/save", "POST", {
          text: args.text,
          project: args.project || activeProject, // Auto-apply active project
          tags: args.tags,
          metadata: args.metadata,
        });
        
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
        const projectToUse = args.project || activeProject;
        const params = new URLSearchParams({
          q: args.query,
          limit: args.limit || 5,
        });
        if (projectToUse) params.append("project", projectToUse);
        if (args.tags && args.tags.length > 0) {
          args.tags.forEach(tag => params.append("tags", tag));
        }

        const result = await cognioRequest(`/memory/search?${params}`);
        
        // Format results nicely
        let response = projectToUse && !args.project 
          ? `[Active Project: ${projectToUse}]\nFound ${result.total} memories:\n\n`
          : `Found ${result.total} memories:\n\n`;
          
        result.results.forEach((mem, idx) => {
          response += `${idx + 1}. [Score: ${mem.score.toFixed(3)}]\n`;
          response += `   Text: ${mem.text}\n`;
          if (mem.project) response += `   Project: ${mem.project}\n`;
          if (mem.tags && mem.tags.length > 0) {
            response += `   Tags: ${mem.tags.join(", ")}\n`;
          }
          response += `   Created: ${mem.created_at}\n\n`;
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

      case "list_memories": {
        const projectToUse = args.project || activeProject;
        const params = new URLSearchParams({
          limit: args.limit || 20,
          offset: args.offset || 0,
        });
        if (projectToUse) params.append("project", projectToUse);
        if (args.tags && args.tags.length > 0) {
          args.tags.forEach(tag => params.append("tags", tag));
        }

        const result = await cognioRequest(`/memory/list?${params}`);
        
        let response = projectToUse && !args.project
          ? `[Active Project: ${projectToUse}]\nTotal: ${result.total} memories (showing ${result.memories.length})\n\n`
          : `Total: ${result.total} memories (showing ${result.memories.length})\n\n`;
          
        result.memories.forEach((mem, idx) => {
          response += `${idx + 1}. ${mem.text.substring(0, 100)}...\n`;
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

        const response = await fetch(`${API_BASE}/memory/export?${params}`, {
          method: "GET",
        });

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
  console.error("Cognio MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
