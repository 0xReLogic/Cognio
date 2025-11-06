#!/usr/bin/env node

/**
 * Auto-setup script for Cognio MCP Server
 * Automatically generates configuration for all supported AI clients
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
  claude: `CLAUDE DESKTOP: Ready to use`,
  cursor: `CURSOR: Ready to use`,
  continue: `CONTINUE.DEV: Ready to use`,
  cline: `CLINE: Ready to use`,
  windsurf: `WINDSURF: Ready to use`,
  kiro: `KIRO: Ready to use`,
  geminiCLI: `GEMINI CLI: Ready to use`
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
    claudeDesktop: setupConfig('claudeDesktop', configs.claudeDesktop),
    cursor: setupConfig('cursor', configs.cursor),
    continue: setupConfig('continue', configs.continue),
    cline: setupConfig('cline', configs.cline),
    windsurf: setupConfig('windsurf', configs.windsurf),
    kiro: setupConfig('kiro', configs.kiro),
    geminiCLI: setupConfig('geminiCLI', configs.geminiCLI)
  };

  console.log('\n[SUMMARY]\n');
  console.log('✓ cognio.md auto-generated (AI context for all tools)\n');
  
  Object.entries(results).forEach(([name, success]) => {
    if (success) console.log(`✓ ${name}`);
  });

  console.log('\n[NEXT STEPS]');
  console.log('1. Start Cognio: python -m uvicorn src.main:app --port 8080');
  console.log('2. Restart your AI client');
  console.log('3. cognio.md provides context to all AI tools\n');
}

main();
