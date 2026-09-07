#!/usr/bin/env python3
"""
Universal Multi-Agent Communication Bus MCP Server
Implements Model Context Protocol (MCP) JSON-RPC 2.0 over stdio.
"""

import sys
import os
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

    def get_tools_schema(self) -> list:
        return [
            {
                "name": "bus_send",
                "description": "Send a message to another agent on the universal agent bus. Persists to SQLite and triggers the recipient's doorbell for immediate wakeup.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Target agent name/id (e.g. 'coordinator', 'antigravity-lead', 'deepseek-coder')"
                        },
                        "content": {
                            "type": "string",
                            "description": "Message content or structured report"
                        },
                        "topic": {
                            "type": "string",
                            "description": "Short topic label (e.g. 'report', 'decision', 'greeting', 'task')",
                            "default": "general"
                        },
                        "from_agent": {
                            "type": "string",
                            "description": "Sender agent name/id (e.g. 'coordinator', 'antigravity-lead')"
                        },
                        "conversation_id": {
                            "type": "string",
                            "description": "Optional correlation or session ID"
                        }
                    },
                    "required": ["to", "content"]
                }
            },
            {
                "name": "bus_inbox",
                "description": "Fetch incoming messages for a specific agent from the persistent SQLite inbox.",
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
                            "description": "Doorbell mechanism ('file', 'socket', 'signal')",
                            "default": "file"
                        },
                        "doorbell_target": {
                            "type": "string",
                            "description": "Target file or port for the doorbell"
                        }
                    },
                    "required": ["agent_id"]
                }
            }
        ]

    def handle_tool_call(self, name: str, args: dict) -> dict:
        if name == "bus_send":
            to_agent = args.get("to")
            content = args.get("content")
            topic = args.get("topic", "general")
            from_agent = args.get("from_agent", "anonymous")
            conversation_id = args.get("conversation_id", "")

            if not to_agent or not content:
                return {"error": "Missing 'to' or 'content'"}

            # 1. Save to DB
            res = self.db.send_message(
                from_agent=from_agent,
                to_agent=to_agent,
                content=content,
                topic=topic,
                conversation_id=conversation_id
            )

            # 2. Ring Doorbell
            agent_info = self.db.get_agent(to_agent)
            if not agent_info:
                agent_info = {"agent_id": to_agent, "framework": "generic", "doorbell_type": "file"}
            self.doorbells.ring(agent_info, content)
            return res

        elif name == "bus_inbox":
            agent_name = args.get("agent_name")
            unread_only = args.get("unread_only", True)
            mark_read = args.get("mark_read", True)
            limit = int(args.get("limit", 10))

            if not agent_name:
                return {"error": "Missing 'agent_name'"}

            msgs = self.db.fetch_inbox(
                agent_name=agent_name,
                unread_only=unread_only,
                mark_read=mark_read,
                limit=limit
            )
            return {"messages": msgs, "count": len(msgs)}

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
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "agent-bus",
                        "version": "1.0.0"
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
