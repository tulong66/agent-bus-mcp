# Claude Code Integration Guide

## Overview
Claude Code runs as an autonomous agent in either CLI terminal mode or Headless Chat API mode. `agent-bus-mcp` connects Claude Code to other agents seamlessly.

## Configuration

Add `agent-bus` to `~/.claude.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "agent-bus": {
      "command": "/opt/homebrew/bin/python3",
      "args": ["/Users/deepzen/.agent-bus/server.py"],
      "type": "stdio"
    }
  }
}
```

Or run `./install.sh` which configures this automatically.

## Usage in Claude Code

### 1. Sending Messages to Antigravity or DeepSeek
Claude can call the `bus_send` tool directly:
```json
{
  "to": "antigravity-lead",
  "topic": "inspection_report",
  "content": "Inspection completed. 15 modified files, 534 untracked files. Awaiting decision."
}
```

Or via the global CLI inside bash:
```bash
agent-bus send --to antigravity-lead --from coordinator --topic task "Tests passed with 0 errors."
```

### 2. Checking Inbox
```bash
agent-bus inbox --agent coordinator
```
