#!/usr/bin/env python3
"""
Universal Multi-Agent Communication Bus MCP Server
Implements Model Context Protocol (MCP) JSON-RPC 2.0 over stdio.
"""

import sys
import os
import time
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Ensure package is importable when executed directly
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from agent_bus.db import Database
from agent_bus.doorbells import DoorbellManager


class MCPServer:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.doorbells = DoorbellManager()
        self.current_agent_id = "anonymous"
        self._auto_register()

    def _auto_register(self):
        """Auto-detect host agent runtime environment and bind doorbell/identity."""
        try:
            # 0. Explicit Environment Override
            agent_id = os.environ.get("AGENT_BUS_AGENT_ID")
            framework = os.environ.get("AGENT_BUS_FRAMEWORK")
            if agent_id:
                self.current_agent_id = agent_id
                bell_path = Path.home() / ".agent-bus" / "doorbells" / f"{agent_id}.bell"
                self.db.register_agent(
                    agent_id=agent_id,
                    framework=framework or "custom",
                    doorbell_type="dsh" if "dsh" in (framework or "") else "file",
                    doorbell_target=str(bell_path)
                )
                return

            # 1. Claude Code Detection (UDS Socket + Token)
            cc_sock = os.environ.get("CLAUDE_CODE_MESSAGING_SOCKET")
            cc_token = os.environ.get("CLAUDE_CODE_MESSAGING_TOKEN")
            if cc_sock and os.path.exists(cc_sock):
                self.current_agent_id = "coordinator"
                target = json.dumps({"socket": cc_sock, "token": cc_token or ""})
                self.db.register_agent(
                    agent_id="coordinator",
                    framework="claude-code",
                    doorbell_type="claude",
                    doorbell_target=target
                )
                return

            # 2. DeepSeek Harness (DSH) Detection
            if "DSH_HOME" in os.environ or "DSH_TUI_PERSONA" in os.environ or "DSH_PROFILE" in os.environ:
                self.current_agent_id = "deepseek-coder"
                bell_path = Path.home() / ".agent-bus" / "doorbells" / "deepseek-coder.bell"
                self.db.register_agent(
                    agent_id="deepseek-coder",
                    framework="dsh",
                    doorbell_type="dsh",
                    doorbell_target=str(bell_path)
                )
                return

            # 3. Antigravity Lead Detection
            sc_custom = Path.home() / ".superconductor" / "hooks" / "antigravity-customization"
            if "ANTIGRAVITY" in os.environ or sc_custom.exists():
                self.current_agent_id = "antigravity-lead"
                bell_path = Path.home() / ".agent-bus" / "doorbells" / "antigravity-lead.bell"
                self.db.register_agent(
                    agent_id="antigravity-lead",
                    framework="antigravity",
                    doorbell_type="file",
                    doorbell_target=str(bell_path)
                )
        except Exception:
            pass

    def get_tools_schema(self) -> list:
        return [
            {
                "name": "bus_send",
                "description": "Send a message to another agent. Only 'to' and 'message' are required. The recipient is automatically woken up with message content injected directly into its active turn.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Target agent ID (e.g. 'coordinator', 'deepseek-coder', 'antigravity-lead')"
                        },
                        "message": {
                            "type": "string",
                            "description": "Message content or instruction"
                        },
                        "content": {
                            "type": "string",
                            "description": "Alias for message"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Optional short topic label (default: 'general')",
                            "default": "general"
                        },
                        "from_agent": {
                            "type": "string",
                            "description": "Optional sender agent ID (auto-detected if omitted)"
                        }
                    },
                    "required": ["to"]
                }
            },
            {
                "name": "bus_inbox",
                "description": "Fetch incoming messages for a specific agent from the persistent SQLite inbox. Supports optional blocking wait.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Your agent ID / mailbox name"
                        },
                        "unread_only": {
                            "type": "boolean",
                            "description": "Whether to return unread messages only",
                            "default": True
                        },
                        "mark_read": {
                            "type": "boolean",
                            "description": "Whether to mark returned messages as read",
                            "default": True
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of messages to return",
                            "default": 10
                        },
                        "wait": {
                            "type": "boolean",
                            "description": "Whether to block waiting until at least one message arrives",
                            "default": False
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Maximum wait time in seconds if wait is true (default 60)",
                            "default": 60
                        }
                    },
                    "required": ["agent_name"]
                }
            },
            {
                "name": "bus_wait_message",
                "description": "Long-poll and wait for an incoming message on the bus (up to 45s, safely below client timeout). Returns status 'received' or 'timeout'. Eliminates terminal polling.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Your agent ID to wait for"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Maximum wait time in seconds (default 30, max 45 to protect client RPC timeout)",
                            "default": 30
                        },
                        "mark_read": {
                            "type": "boolean",
                            "description": "Whether to mark the delivered messages as read",
                            "default": True
                        }
                    },
                    "required": ["agent_name"]
                }
            },
            {
                "name": "bus_history",
                "description": "Query chronological dialogue history between two agents from SQLite storage.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_a": {
                            "type": "string",
                            "description": "First agent ID"
                        },
                        "agent_b": {
                            "type": "string",
                            "description": "Second agent ID"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of recent dialogue messages to return",
                            "default": 20
                        }
                    },
                    "required": ["agent_a", "agent_b"]
                }
            },
            {
                "name": "bus_list_agents",
                "description": "List all active registered agents and their statuses on the universal communication bus.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "bus_register",
                "description": "Register or update an agent's identity and doorbell configuration on the bus.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "Agent name/ID to register"
                        },
                        "framework": {
                            "type": "string",
                            "description": "Framework name (e.g. 'antigravity', 'claude-code', 'dsh', 'codex')",
                            "default": "generic"
                        },
                        "doorbell_type": {
                            "type": "string",
                            "description": "Doorbell mechanism ('file', 'claude', 'socket', 'signal')",
                            "default": "file"
                        },
                        "doorbell_target": {
                            "type": "string",
                            "description": "Target file, socket or port for the doorbell"
                        }
                    },
                    "required": ["agent_id"]
                }
            }
        ]

    def handle_tool_call(self, name: str, args: dict) -> dict:
        if name == "bus_send":
            to_agent = args.get("to")
            # If both content and message are provided, pick the longer one (prevents title overwriting body)
            c_cands = [c for c in [args.get("content"), args.get("message"), args.get("text")] if c and isinstance(c, str)]
            content = max(c_cands, key=len) if c_cands else None
            topic = args.get("topic", "general")
            from_agent = args.get("from_agent") or getattr(self, "current_agent_id", "anonymous")
            conversation_id = args.get("conversation_id", "")

            if not to_agent or not content:
                return {"error": "Missing 'to' or 'message'"}

            # 1. Save to DB
            res = self.db.send_message(
                from_agent=from_agent,
                to_agent=to_agent,
                content=content,
                topic=topic,
                conversation_id=conversation_id
            )

            # 2. Ring Doorbell with metadata
            agent_info = self.db.get_agent(to_agent)
            if not agent_info:
                agent_info = {"agent_id": to_agent, "framework": "generic", "doorbell_type": "file"}
            agent_info = dict(agent_info)
            agent_info["from_agent"] = from_agent
            agent_info["topic"] = topic
            self.doorbells.ring(agent_info, content)
            return res

        elif name == "bus_inbox":
            agent_name = args.get("agent_name") or getattr(self, "current_agent_id", "")
            unread_only = args.get("unread_only", True)
            mark_read = args.get("mark_read", True)
            limit = int(args.get("limit", 10))
            wait = bool(args.get("wait", False))
            timeout = min(max(1, int(args.get("timeout", 30))), 45)

            if not agent_name:
                return {"error": "Missing 'agent_name'"}

            if not wait:
                msgs = self.db.fetch_inbox(
                    agent_name=agent_name,
                    unread_only=unread_only,
                    mark_read=mark_read,
                    limit=limit
                )
                return {"messages": msgs, "count": len(msgs)}

            start_t = time.time()
            while True:
                msgs = self.db.fetch_inbox(
                    agent_name=agent_name,
                    unread_only=unread_only,
                    mark_read=mark_read,
                    limit=limit
                )
                if msgs or (time.time() - start_t >= timeout):
                    return {"messages": msgs, "count": len(msgs)}
                time.sleep(0.2)

        elif name == "bus_wait_message":
            agent_name = args.get("agent_name") or getattr(self, "current_agent_id", "")
            timeout = min(max(1, int(args.get("timeout", 30))), 45)
            mark_read = bool(args.get("mark_read", True))

            if not agent_name:
                return {"error": "Missing 'agent_name'"}

            start_t = time.time()
            while time.time() - start_t < timeout:
                msgs = self.db.fetch_inbox(
                    agent_name=agent_name,
                    unread_only=True,
                    mark_read=mark_read,
                    limit=10
                )
                if msgs:
                    return {"status": "received", "messages": msgs, "count": len(msgs)}
                time.sleep(0.2)

            return {"status": "timeout", "messages": [], "count": 0}

        elif name == "bus_history":
            agent_a = args.get("agent_a")
            agent_b = args.get("agent_b")
            limit = int(args.get("limit", 20))

            if not agent_a or not agent_b:
                return {"error": "Missing 'agent_a' or 'agent_b'"}

            history = self.db.fetch_history(agent_a, agent_b, limit)
            return {"dialogue": history, "count": len(history)}

        elif name == "bus_list_agents":
            return {"agents": self.db.list_agents()}

        elif name == "bus_register":
            agent_id = args.get("agent_id")
            framework = args.get("framework", "generic")
            doorbell_type = args.get("doorbell_type", "file")
            doorbell_target = args.get("doorbell_target")
            if not agent_id:
                return {"error": "Missing 'agent_id'"}
            return self.db.register_agent(
                agent_id=agent_id,
                framework=framework,
                doorbell_type=doorbell_type,
                doorbell_target=doorbell_target
            )

        return {"error": f"Unknown tool: {name}"}

    def handle_request(self, req: dict) -> dict:
        method = req.get("method")
        req_id = req.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": req.get("params", {}).get("protocolVersion", "2024-11-05"),
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "agent-bus",
                        "version": "1.1.0"
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": self.get_tools_schema()
                }
            }

        elif method == "tools/call":
            params = req.get("params", {})
            tool_name = params.get("name")
            args = params.get("arguments", {})

            res = self.handle_tool_call(tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(res, ensure_ascii=False, indent=2)
                        }
                    ],
                    "isError": "error" in res
                }
            }

        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {}
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

    def run_stdio(self):
        sys.stderr.write("[agent-bus] Server listening on stdio.\n")
        sys.stderr.flush()
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                if "id" not in req:
                    # Ignore notifications gracefully
                    continue
                resp = self.handle_request(req)
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except Exception as e:
                sys.stderr.write(f"[agent-bus] JSON error: {e}\n")
                sys.stderr.flush()


def main():
    server = MCPServer()
    server.run_stdio()


if __name__ == "__main__":
    main()
