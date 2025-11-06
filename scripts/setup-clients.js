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
          "text": "You have access to Cognio memory tools. Search past work when relevant, save useful solutions for later."
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
      "systemMessage": "You have access to Cognio semantic memory. Search past work when relevant, save useful solutions for later."
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
GITHUB COPILOT:
Cognio memory tools configured. Use naturally when needed.
`,

  claude: `
CLAUDE DESKTOP:
Cognio MCP server configured and ready to use.
`,

  cursor: `
CURSOR:
Cognio MCP server configured and ready to use.
`,

  continue: `
CONTINUE.DEV:
Cognio MCP server configured and ready to use.
`,

  cline: `
CLINE:
Cognio MCP server configured and ready to use.
`,

  windsurf: `
WINDSURF:
Cognio MCP server configured at ~/.windsurf/mcp_config.json
`,

  kiro: `
KIRO:
Cognio MCP server configured at ~/.kiro/settings/mcp.json
`,

  claudeCLI: `
CLAUDE CLI:
Cognio MCP server configured at ~/.claude.json
`,

  geminiCLI: `
GEMINI CLI:
Cognio MCP server configured at ~/gemini/settings.json
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
