# OpenAI Codex Integration Guide

## Overview
OpenAI Codex CLI can be integrated into the multi-agent bus either via MCP server configuration or through shell hooks.

## Configuration

Add to `~/.codex/config.json`:

```json
{
  "mcpServers": {
    "agent-bus": {
      "command": "python3",
      "args": ["~/.agent-bus/server.py"],
      "type": "stdio"
    }
  }
}
```

## CLI Usage

Codex can communicate with other agents via bash tool:
```bash
# Register identity
agent-bus register codex-lead --framework codex

# Send message
agent-bus send --to coordinator --from codex-lead --topic pr_review "PR #42 reviewed and approved."

# Check incoming
agent-bus inbox --agent codex-lead
```
