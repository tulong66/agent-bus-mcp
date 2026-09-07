# Antigravity (Google Gemini) Integration Guide

## Overview
Antigravity operates in either CLI (`agy`) or IDE mode. Because Antigravity runs in non-canonical Raw terminal mode when interactive, `agent-bus-mcp` provides zero-keystroke communication via the **Doorbell + PreInvocation Hook** architecture.

## Configuration

Add to `~/.gemini/config/mcp_config.json`:

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

## Lifecycle Hook Setup

In `~/.superconductor/hooks/antigravity-notify.sh` (or `.agents/hooks.json`):
The `PreInvocation` hook intercepts and injects incoming messages from `~/.agent-bus/inbox/antigravity-lead.msg` directly into the agent's context as `ephemeralMessage`.

## Doorbell Wakeup Setup

Antigravity arms a lightweight background watcher:
```bash
python3 /Users/deepzen/.superconductor/bin/inbox-doorbell.py 600
```
When any agent calls `bus_send(to="antigravity-lead")`, the bell file is touched, the background watcher immediately exits, and Antigravity is awakened reactively within 0.7s!
