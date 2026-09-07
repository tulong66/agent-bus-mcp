# agent-bus-mcp: System Architecture

## 1. Overview

`agent-bus-mcp` is a decentralized, persistent, heterogeneous communication bus designed for multi-agent software engineering teams. It allows autonomous agents running on different runtimes (Claude Code, OpenAI Codex, Google Antigravity, DeepSeek Harness) to discover each other, send structured messages, and trigger reactive wakeups with sub-second latency.

## 2. Core Architectural Pillars

```
+-------------------------------------------------------------------------+
|                              Agent Tier                                 |
|  [ Antigravity Lead ]   [ Claude Coordinator ]   [ DeepSeek Specialist ]|
+-----------|-------------------------|-------------------------|---------+
            | (MCP Tool / CLI)        | (MCP Tool / CLI)        |
            +-------------------------+-------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------+
|                           MCP Protocol Layer                            |
|             JSON-RPC 2.0 over stdio (Model Context Protocol)             |
|       Tools: bus_send, bus_inbox, bus_history, bus_register, etc.       |
+-------------------------------------|-----------------------------------+
                                      |
                     +----------------+----------------+
                     |                                 |
                     v                                 v
+------------------------------------+ +----------------------------------+
|           Storage Engine           | |        Doorbell Subsystem        |
|  - SQLite 3 with WAL journal mode  | |  - Heterogeneous Wakeup Drivers  |
|  - ACID transactional consistency  | |  - Antigravity Reactive Wakeup   |
|  - Complete audit history trail    | |  - Chat UI API direct injection  |
|  - Zero multi-process collisions   | |  - DSH FIFO / Socket signals     |
+------------------------------------+ +----------------------------------+
```

### Pillar 1: Protocol Standard (MCP JSON-RPC 2.0)
Rather than requiring LLMs to craft fragile shell commands or parse raw strings, `agent-bus-mcp` exposes clean, standard Tool Call interfaces (`bus_send`, `bus_inbox`, `bus_history`). Any model capable of tool use can participate natively.

### Pillar 2: Storage & Concurrency (SQLite WAL)
- Location: `~/.agent-bus/bus.db`
- **WAL Mode (`PRAGMA journal_mode=WAL;`)**: Allows concurrent readers and writers across different processes without database locking errors.
- **Addressing**: Every message is indexed by `(to_agent, status)` and `(from_agent, to_agent)`. Multiple instances of the same model runtime will never collide or overwrite each other's messages.
- **Auditability**: Messages are marked as `delivered` and `read` with microsecond-level timestamps, preserving the full conversation history.

### Pillar 3: Heterogeneous Doorbell Wakeup
LLMs in terminal or chat interfaces enter an `idle` state between turns. Without an active trigger, messages written to disk remain unread until human intervention.
`agent-bus-mcp` solves this via **Doorbell Drivers**:
- **Antigravity Driver**: Touches target bell files and bridges into the platform background task runner. Antigravity detects task completion and automatically resumes execution with high priority (measured wakeup latency: **< 0.7 seconds**).
- **Claude Code Driver**: Leverages Chat UI turn dispatch or pre-invocation polling.
- **DeepSeek Harness Driver**: Writes wake tokens into Unix named pipes (`.fifo`) or domain sockets.
