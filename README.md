# agent-bus-mcp 🚌

> **Universal Multi-Agent Communication Bus & Doorbell Wakeup System**  
> Connect **Claude Code**, **OpenAI Codex**, **Google Antigravity**, and **DeepSeek Harness (DSH)** over standard Model Context Protocol (MCP) and SQLite.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9+-green.svg)](https://python.org)
[![MCP: 2024-11-05](https://img.shields.io/badge/MCP-2024--11--05-orange.svg)](https://modelcontextprotocol.io)
[![Tests: Passing](https://img.shields.io/badge/Tests-6%20passed-brightgreen.svg)](tests/)

---

## 🌟 Why agent-bus-mcp?

Modern AI agents often operate in isolated silos:
- **Claude Code** runs in its own CLI or Chat UI;
- **Google Antigravity** operates in terminal raw mode;
- **OpenAI Codex** and **DeepSeek Harness** have separate runtimes.

Existing orchestration tools rely on fragile PTY keyboard simulation (frequently hanging on carriage returns), single-file overwrites, or lack autonomous push notification.

**`agent-bus-mcp` solves this with a three-layer architecture:**
1. **Universal Addressing & Identity**: Every agent registers a unique ID (`antigravity-lead`, `coordinator`, `deepseek-coder`). Multiple instances never collide.
2. **Persistent Concurrency Engine**: SQLite with Write-Ahead Logging (`WAL`), ACID transactions, status tracking (`unread -> delivered -> read`), and complete audit history.
3. **Heterogeneous Doorbell Subsystem**: Delivers sub-second (0.7s) reactive wakeups to sleeping agents without requiring manual human keystrokes.

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Heterogeneous Agents                     │
│    Antigravity    │    Claude Code    │   DeepSeek / Codex  │
└──────────────┬──────────────────┬─────────────────┬─────────┘
               │ (Standard MCP Tools or CLI)
               ▼
┌─────────────────────────────────────────────────────────────┐
│             agent-bus-mcp Server (JSON-RPC 2.0)             │
│   Tools: bus_send / bus_inbox / bus_history / bus_register  │
└──────────────────────────────┬──────────────────────────────┘
                               │ (ACID Transactions & Status Tracking)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             SQLite WAL Database (~/.agent-bus/bus.db)       │
│  - messages: message_id, from, to, topic, status, timestamps│
│  - agents: agent_id, framework, doorbell_type, last_seen    │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Targeted Doorbell Wakeup)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     Doorbell Drivers                        │
│  - Antigravity Driver (Platform Reactive Task Wakeup)       │
│  - Claude Code Driver (API Chat Turn Injection)             │
│  - DSH / Unix Driver  (FIFO Named Pipe / Socket Signals)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

### 1. One-Click Installation

Clone and run the installer:

```bash
git clone https://github.com/your-username/agent-bus-mcp.git
cd agent-bus-mcp
./install.sh
```

The installer automatically:
- Sets up `~/.agent-bus/` and initializes the SQLite WAL database;
- Installs the global `agent-bus` CLI to `~/.local/bin/agent-bus`;
- Auto-detects and injects MCP configuration into:
  - `~/.claude.json` (Claude Code)
  - `~/.gemini/config/mcp_config.json` (Antigravity)
  - `~/.codex/config.json` (Codex)
  - `~/.dsh/` (DeepSeek Harness)

### 2. Verify Installation

```bash
agent-bus agents
```
Output:
```text
AGENT ID                  FRAMEWORK       STATUS     DOORBELL TARGET
--------------------------------------------------------------------------------
antigravity-lead          antigravity     active     ~/.agent-bus/doorbells/antigravity-lead.bell
coordinator               claude-code     active     ~/.agent-bus/doorbells/coordinator.bell
deepseek-coder            dsh             active     ~/.agent-bus/doorbells/deepseek-coder.bell
codex-lead                codex           active     ~/.agent-bus/doorbells/codex-lead.bell
```

---

## 🛠️ MCP Tools Reference

When connected via MCP, any agent can call these standard tools:

| Tool | Description | Key Arguments |
| :--- | :--- | :--- |
| `bus_send` | Send a message to an agent & ring its doorbell | `to`, `content`, `topic`, `from_agent` |
| `bus_inbox` | Fetch unread messages from SQLite | `agent_name`, `unread_only`, `mark_read` |
| `bus_history` | Query dialogue history between two agents | `agent_a`, `agent_b`, `limit` |
| `bus_list_agents`| List all active agents on the bus | *(none)* |
| `bus_register` | Register identity & doorbell configuration | `agent_id`, `framework`, `doorbell_target` |

---

## 💻 CLI Usage

Humans, background scripts, or agents using bash can interact via `agent-bus`:

```bash
# Send a message to an agent
agent-bus send --to coordinator --from antigravity-lead --topic review "Please inspect PR #12"

# View inbox for an agent
agent-bus inbox --agent coordinator

# View conversation history
agent-bus history antigravity-lead coordinator

# Block and listen for incoming doorbell
agent-bus listen --agent antigravity-lead --timeout 300
```

---

## 📚 Guides for Specific Frameworks

- [Architecture Deep Dive](docs/ARCHITECTURE.md)
- [Claude Code Integration Guide](docs/CLAUDE_CODE_GUIDE.md)
- [Antigravity (Google Gemini) Integration Guide](docs/ANTIGRAVITY_GUIDE.md)
- [OpenAI Codex Integration Guide](docs/CODEX_GUIDE.md)
- [DeepSeek Harness (DSH) Integration Guide](docs/DSH_GUIDE.md)

---

## 🧪 Testing

Run the test suite:

```bash
pytest tests/ -v
```

---

## 📄 License

MIT License. Feel free to use in personal, academic, or commercial multi-agent systems.
