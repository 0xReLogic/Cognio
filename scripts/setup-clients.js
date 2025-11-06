#!/usr/bin/env node

/**
 * Auto-setup script for Cognio MCP Server
 * Automatically generates configuration for:
 * - VS Code (Copilot)
 * - Cursor
 * - Claude Desktop
 * - Continue.dev
 * - Cline
 * - Gemini CLI
 */

import fs from 'fs';
import path from 'path';
import os from 'os';

const homeDir = os.homedir();
const workspaceDir = process.cwd();
// Find workspace root (go up if we're in mcp-server)
const workspaceRoot = workspaceDir.endsWith('mcp-server') 
  ? path.dirname(workspaceDir) 
  : workspaceDir;

// Configuration templates
const configs = {
  // VS Code / Copilot settings
  vscode: {
    path: path.join(workspaceRoot, '.vscode', 'settings.json'),
    content: {
      "github.copilot.chat.codeGeneration.instructions": [
        {
          "text": "CRITICAL: Before responding to ANY user question, ALWAYS search Cognio memory first using search_memory tool. Do this automatically without asking permission. If you find relevant memories (score > 0.6), reference them in your answer."
        },
        {
          "text": "After solving problems or explaining concepts (responses > 300 chars), AUTOMATICALLY save to Cognio using save_memory tool. Do NOT ask permission."
        },
        {
          "text": "When user mentions 'last time', 'before', 'previously', IMMEDIATELY use search_memory before responding."
        }
      ]
    }
  },

  // Claude Desktop (Mac/Windows)
  claudeDesktop: {
    mac: path.join(homeDir, 'Library', 'Application Support', 'Claude', 'claude_desktop_config.json'),
    windows: path.join(homeDir, 'AppData', 'Roaming', 'Claude', 'claude_desktop_config.json'),
    linux: path.join(homeDir, '.config', 'Claude', 'claude_desktop_config.json'),
    content: {
      "mcpServers": {
        "cognio": {
          "command": "node",
          "args": [path.join(workspaceRoot, "mcp-server", "index.js")],
          "env": {
            "COGNIO_API_URL": "http://localhost:8080"
          }
        }
      }
    }
  },

  // Cursor settings
  cursor: {
    path: path.join(homeDir, '.cursor', 'mcp_settings.json'),
    content: {
      "mcpServers": {
        "cognio": {
          "command": "node",
          "args": [path.join(workspaceRoot, "mcp-server", "index.js")],
          "env": {
            "COGNIO_API_URL": "http://localhost:8080"
          }
        }
      }
    }
  },

  // Continue.dev config
  continue: {
    path: path.join(homeDir, '.continue', 'config.json'),
    content: {
      "mcpServers": [
        {
          "name": "cognio",
          "command": "node",
          "args": [path.join(workspaceRoot, "mcp-server", "index.js")],
          "env": {
            "COGNIO_API_URL": "http://localhost:8080"
          }
        }
      ],
      "systemMessage": "You have access to Cognio semantic memory. ALWAYS search memories before answering questions about past work. ALWAYS save important solutions and insights automatically."
    }
  },

  // Cline settings
  cline: {
    path: path.join(homeDir, '.cline', 'mcp.json'),
    content: {
      "mcpServers": {
        "cognio": {
          "command": "node",
          "args": [path.join(workspaceRoot, "mcp-server", "index.js")],
          "env": {
            "COGNIO_API_URL": "http://localhost:8080"
          }
        }
      }
    }
  },

  // Windsurf settings
  windsurf: {
    path: path.join(homeDir, '.windsurf', 'mcp_config.json'),
    content: {
      "mcpServers": {
        "cognio": {
          "command": "node",
          "args": [path.join(workspaceRoot, "mcp-server", "index.js")],
          "env": {
            "COGNIO_API_URL": "http://localhost:8080"
          }
        }
      }
    }
  },

  // Kiro settings
  kiro: {
    path: path.join(homeDir, '.kiro', 'settings', 'mcp.json'),
    content: {
      "mcpServers": {
        "cognio": {
          "command": "node",
          "args": [path.join(workspaceRoot, "mcp-server", "index.js")],
          "env": {
            "COGNIO_API_URL": "http://localhost:8080"
          }
        }
      }
    }
  },

  // Claude CLI settings
  claudeCLI: {
    path: path.join(homeDir, '.claude.json'),
    content: {
      "mcpServers": {
        "cognio": {
          "command": "node",
          "args": [path.join(workspaceRoot, "mcp-server", "index.js")],
          "env": {
            "COGNIO_API_URL": "http://localhost:8080"
          }
        }
      }
    }
  },

  // Gemini CLI settings
  geminiCLI: {
    path: path.join(homeDir, 'gemini', 'settings.json'),
    content: {
      "mcpServers": {
        "cognio": {
          "command": "node",
          "args": [path.join(workspaceRoot, "mcp-server", "index.js")],
          "env": {
            "COGNIO_API_URL": "http://localhost:8080"
          }
        }
      }
    }
  }
};

// Instructions for each platform
const instructions = {
  copilot: `
GITHUB COPILOT INSTRUCTIONS:
- Auto-search Cognio before EVERY response
- Auto-save after solving problems
- Use search_memory when user asks "have I..." or "last time..."
- Use save_memory after explaining complex concepts
`,

  claude: `
CLAUDE DESKTOP INSTRUCTIONS:
System message to add:

"You have access to Cognio, a semantic memory system. Usage rules:
1. ALWAYS search_memory first when user asks about past work
2. ALWAYS save_memory after helping with substantial problems
3. When user says 'remember', 'last time', 'before' → search first
4. Auto-save solutions, decisions, and learnings without asking"
`,

  cursor: `
CURSOR INSTRUCTIONS:
Add to .cursorrules file:

# Cognio Auto-Memory
- Before answering questions, search Cognio memories
- After solving problems, save solutions to Cognio
- Keywords: "remember", "last time" → auto-search
- Auto-save: solutions, decisions, learnings
`,

  continue: `
CONTINUE.DEV INSTRUCTIONS:
System message already configured in config.json
The assistant will automatically use Cognio for:
- Searching past work
- Saving solutions
- Building knowledge base
`,

  cline: `
CLINE INSTRUCTIONS:
MCP server configured. Remind Cline:
"Use Cognio memory tools automatically:
- search_memory before answering past-work questions
- save_memory after solving problems
- No need to ask permission"
`,

  windsurf: `
WINDSURF INSTRUCTIONS:
MCP server configured at ~/.windsurf/mcp_config.json
Access via: Windsurf Settings > Manage MCPs > View raw config
Remind Windsurf to use Cognio automatically for memory operations.
`,

  kiro: `
KIRO INSTRUCTIONS:
MCP server configured at ~/.kiro/settings/mcp.json
Kiro will auto-detect the server on next start.
Use naturally: "search memories" or "remember this"
`,

  claudeCLI: `
CLAUDE CLI INSTRUCTIONS:
Config at ~/.claude.json
Start claude with: claude --scope user
Test with: "search my cognio memories"
Auto-save is enabled for important responses.
`,

  geminiCLI: `
GEMINI CLI INSTRUCTIONS:
Config at ~/gemini/settings.json
List MCP servers: gemini /mcp list
Cognio tools will appear automatically.
Use: "search cognio for..." or "save to cognio..."
`
};

function ensureDirectoryExists(filePath) {
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function mergeConfig(existingConfig, newConfig) {
  if (!existingConfig) return newConfig;
  
  // Deep merge for objects
  const merged = { ...existingConfig };
  
  for (const [key, value] of Object.entries(newConfig)) {
    if (typeof value === 'object' && !Array.isArray(value) && merged[key]) {
      merged[key] = mergeConfig(merged[key], value);
    } else {
      merged[key] = value;
    }
  }
  
  return merged;
}

function setupConfig(name, config) {
  try {
    let configPath = config.path;
    
    // Handle platform-specific paths (Claude Desktop)
    if (name === 'claudeDesktop') {
      const platform = os.platform();
      if (platform === 'darwin') configPath = config.mac;
      else if (platform === 'win32') configPath = config.windows;
      else configPath = config.linux;
    }

    ensureDirectoryExists(configPath);

    let existingConfig = {};
    if (fs.existsSync(configPath)) {
      const content = fs.readFileSync(configPath, 'utf8');
      existingConfig = JSON.parse(content);
    }

    const mergedConfig = mergeConfig(existingConfig, config.content);
    fs.writeFileSync(configPath, JSON.stringify(mergedConfig, null, 2));
    
    console.log(`[OK] ${name}: ${configPath}`);
    return true;
  } catch (error) {
    console.log(`[WARN] ${name}: ${error.message}`);
    return false;
  }
}

function main() {
  console.log('\n=== Cognio MCP Auto-Setup ===\n');
  console.log('Configuring clients for automatic Cognio integration...\n');

  const results = {
    vscode: setupConfig('vscode', configs.vscode),
    claudeDesktop: setupConfig('claudeDesktop', configs.claudeDesktop),
    cursor: setupConfig('cursor', configs.cursor),
    continue: setupConfig('continue', configs.continue),
    cline: setupConfig('cline', configs.cline),
    windsurf: setupConfig('windsurf', configs.windsurf),
    kiro: setupConfig('kiro', configs.kiro),
    claudeCLI: setupConfig('claudeCLI', configs.claudeCLI),
    geminiCLI: setupConfig('geminiCLI', configs.geminiCLI)
  };

  console.log('\n[SUMMARY]\n');
  
  if (results.vscode) {
    console.log('VS Code / Copilot:');
    console.log(instructions.copilot);
  }
  
  if (results.claudeDesktop) {
    console.log('Claude Desktop:');
    console.log(instructions.claude);
  }
  
  if (results.cursor) {
    console.log('Cursor:');
    console.log(instructions.cursor);
  }
  
  if (results.continue) {
    console.log('Continue.dev:');
    console.log(instructions.continue);
  }
  
  if (results.cline) {
    console.log('Cline:');
    console.log(instructions.cline);
  }

  if (results.windsurf) {
    console.log('Windsurf:');
    console.log(instructions.windsurf);
  }

  if (results.kiro) {
    console.log('Kiro:');
    console.log(instructions.kiro);
  }

  if (results.claudeCLI) {
    console.log('Claude CLI:');
    console.log(instructions.claudeCLI);
  }

  if (results.geminiCLI) {
    console.log('Gemini CLI:');
    console.log(instructions.geminiCLI);
  }

  console.log('\n[INFO] Next Steps:');
  console.log('1. Start Cognio server: npm start (or python -m uvicorn src.main:app)');
  console.log('2. Restart your IDE/client');
  console.log('3. Test with: "search my memories for..." or "remember this..."');
  console.log('\nCognio will now work automatically in the background!\n');
}

main();
