#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Cognio API base URL
const COGNIO_API_URL = process.env.COGNIO_API_URL || "http://localhost:8080";

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
        description: "Save information to long-term semantic memory with automatic tagging and categorization",
        inputSchema: {
          type: "object",
          properties: {
            text: {
              type: "string",
              description: "The memory content to save",
            },
            project: {
              type: "string",
              description: "Optional project name to organize the memory",
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
        description: "Search memories using semantic similarity",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "Search query text",
            },
            project: {
              type: "string",
              description: "Optional project filter",
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
          project: args.project,
          tags: args.tags,
          metadata: args.metadata,
        });
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      }

      case "search_memory": {
        const params = new URLSearchParams({
          q: args.query,
          limit: args.limit || 5,
        });
        if (args.project) params.append("project", args.project);
        if (args.tags && args.tags.length > 0) {
          args.tags.forEach(tag => params.append("tags", tag));
        }

        const result = await cognioRequest(`/memory/search?${params}`);
        
        // Format results nicely
        let response = `Found ${result.total} memories:\n\n`;
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
        const params = new URLSearchParams({
          limit: args.limit || 20,
          offset: args.offset || 0,
        });
        if (args.project) params.append("project", args.project);
        if (args.tags && args.tags.length > 0) {
          args.tags.forEach(tag => params.append("tags", tag));
        }

        const result = await cognioRequest(`/memory/list?${params}`);
        
        let response = `Total: ${result.total} memories (showing ${result.memories.length})\n\n`;
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
