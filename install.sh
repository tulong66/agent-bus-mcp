#!/bin/bash
# ==============================================================================
# Universal Agent Bus MCP (agent-bus-mcp) One-Click Installer
# Supports: Claude Code, OpenAI Codex, Antigravity (Gemini), DeepSeek Harness (DSH)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(which python3 || echo "/opt/homebrew/bin/python3")"

echo "========================================================"
echo "🚀 Installing Universal Multi-Agent Communication Bus (agent-bus-mcp)"
echo "========================================================"

# 1. Ensure runtime directories
BASE_DIR="$HOME/.agent-bus"
mkdir -p "$BASE_DIR/doorbells" "$BASE_DIR/inbox" "$HOME/.local/bin"

# 2. Deploy server script & sync
SERVER_TARGET="$BASE_DIR/server.py"
cp -f "$SCRIPT_DIR/src/agent_bus/server.py" "$SERVER_TARGET"
chmod +x "$SERVER_TARGET"

# 3. Deploy CLI script to ~/.local/bin/agent-bus
CLI_TARGET="$HOME/.local/bin/agent-bus"
cat << BIN_EOF > "$CLI_TARGET"
#!/bin/bash
exec "$PYTHON_BIN" "$SCRIPT_DIR/src/agent_bus/cli.py" "\$@"
BIN_EOF
chmod +x "$CLI_TARGET"
echo "✅ Installed global CLI: $CLI_TARGET"

if [ -d "$HOME/.superconductor/bin" ]; then
  ln -sf "$CLI_TARGET" "$HOME/.superconductor/bin/agent-bus"
  echo "✅ Linked CLI to Superconductor: $HOME/.superconductor/bin/agent-bus"
fi

# 4. Configure Claude Code (~/.claude.json)
CLAUDE_CONFIG="$HOME/.claude.json"
if [ -f "$CLAUDE_CONFIG" ]; then
  "$PYTHON_BIN" - << PY_EOF
import json
path = "$CLAUDE_CONFIG"
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "mcpServers" not in data:
        data["mcpServers"] = {}
    data["mcpServers"]["agent-bus"] = {
        "command": "$PYTHON_BIN",
        "args": ["$SERVER_TARGET"],
        "type": "stdio"
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("✅ Configured Claude Code: ~/.claude.json")
except Exception as e:
    print(f"⚠️ Failed to update ~/.claude.json: {e}")
PY_EOF
fi

# 5. Configure Antigravity (~/.gemini/config/mcp_config.json)
ANTIGRAVITY_CONFIG="$HOME/.gemini/config/mcp_config.json"
if [ -f "$ANTIGRAVITY_CONFIG" ]; then
  "$PYTHON_BIN" - << PY_EOF
import json
path = "$ANTIGRAVITY_CONFIG"
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "mcpServers" not in data:
        data["mcpServers"] = {}
    data["mcpServers"]["agent-bus"] = {
        "command": "$PYTHON_BIN",
        "args": ["$SERVER_TARGET"],
        "type": "stdio"
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("✅ Configured Antigravity: ~/.gemini/config/mcp_config.json")
except Exception as e:
    print(f"⚠️ Failed to update ~/.gemini/config/mcp_config.json: {e}")
PY_EOF
fi

# 6. Configure Codex (~/.codex/config.json if present)
CODEX_CONFIG="$HOME/.codex/config.json"
if [ -f "$CODEX_CONFIG" ]; then
  "$PYTHON_BIN" - << PY_EOF
import json
path = "$CODEX_CONFIG"
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "mcpServers" not in data:
        data["mcpServers"] = {}
    data["mcpServers"]["agent-bus"] = {
        "command": "$PYTHON_BIN",
        "args": ["$SERVER_TARGET"],
        "type": "stdio"
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("✅ Configured OpenAI Codex: ~/.codex/config.json")
except Exception as e:
    print(f"⚠️ Failed to update ~/.codex/config.json: {e}")
PY_EOF
fi

# 7. Configure DeepSeek Harness (DSH)
DSH_DIR="$HOME/.dsh"
if [ -d "$DSH_DIR" ]; then
  mkdir -p "$DSH_DIR/doorbells"
  ln -sf "$SCRIPT_DIR/scripts/dsh-doorbell.sh" "$HOME/.local/bin/dsh-doorbell"
  echo "✅ Configured DeepSeek Harness: ~/.dsh/doorbells"
fi

# 8. Initialize SQLite Database
"$PYTHON_BIN" -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR/src')
from agent_bus.db import Database
db = Database()
db.register_agent('antigravity-lead', 'antigravity')
db.register_agent('coordinator', 'claude-code')
db.register_agent('deepseek-coder', 'dsh')
db.register_agent('codex-lead', 'codex')
print('✅ Initialized SQLite database with active agent registry.')
"

echo ""
echo "🎉 Installation Complete! All agents are now connected to the bus."
echo "👉 Verify anytime with: agent-bus agents"
