"""
Database layer for agent-bus-mcp.
Uses SQLite with WAL mode for fast, concurrent, ACID transactions.
"""

import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = Path.home() / ".agent-bus" / "bus.db"


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self) -> None:
        with self.get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    framework TEXT NOT NULL,
                    doorbell_type TEXT DEFAULT 'file',
                    doorbell_target TEXT,
                    status TEXT DEFAULT 'active',
                    last_seen REAL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT,
                    from_agent TEXT NOT NULL,
                    to_agent TEXT NOT NULL,
                    topic TEXT DEFAULT 'general',
                    content TEXT NOT NULL,
                    status TEXT DEFAULT 'unread',
                    created_at REAL,
                    delivered_at REAL,
                    read_at REAL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_to ON messages(to_agent, status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_peers ON messages(from_agent, to_agent);")

    def register_agent(self, agent_id: str, framework: str = "generic", doorbell_type: str = "file", doorbell_target: Optional[str] = None) -> Dict[str, Any]:
        now = time.time()
        if not doorbell_target:
            doorbell_target = str(Path.home() / ".agent-bus" / "doorbells" / f"{agent_id}.bell")

        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO agents (agent_id, framework, doorbell_type, doorbell_target, status, last_seen)
                VALUES (?, ?, ?, ?, 'active', ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    framework=excluded.framework,
                    doorbell_type=excluded.doorbell_type,
                    doorbell_target=excluded.doorbell_target,
                    status='active',
                    last_seen=excluded.last_seen
            """, (agent_id, framework, doorbell_type, doorbell_target, now))

        return {
            "status": "registered",
            "agent_id": agent_id,
            "framework": framework,
            "doorbell_target": doorbell_target
        }

    def send_message(self, from_agent: str, to_agent: str, content: str, topic: str = "general", conversation_id: str = "") -> Dict[str, Any]:
        now = time.time()
        with self.get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO messages (conversation_id, from_agent, to_agent, topic, content, status, created_at, delivered_at)
                VALUES (?, ?, ?, ?, ?, 'delivered', ?, ?)
            """, (conversation_id, from_agent, to_agent, topic, content, now, now))
            msg_id = cur.lastrowid

            # Update sender activity
            conn.execute("""
                INSERT INTO agents (agent_id, framework, last_seen) VALUES (?, 'unknown', ?)
                ON CONFLICT(agent_id) DO UPDATE SET last_seen=excluded.last_seen
            """, (from_agent, now))

        return {
            "status": "delivered",
            "message_id": msg_id,
            "from": from_agent,
            "to": to_agent,
            "topic": topic,
            "timestamp": now
        }

    def fetch_inbox(self, agent_name: str, unread_only: bool = True, mark_read: bool = True, limit: int = 10) -> List[Dict[str, Any]]:
        now = time.time()
        with self.get_connection() as conn:
            if unread_only:
                cur = conn.execute("""
                    SELECT message_id, conversation_id, from_agent, to_agent, topic, content, status, created_at
                    FROM messages
                    WHERE to_agent = ? AND status != 'read'
                    ORDER BY message_id ASC
                    LIMIT ?
                """, (agent_name, limit))
            else:
                cur = conn.execute("""
                    SELECT message_id, conversation_id, from_agent, to_agent, topic, content, status, created_at
                    FROM messages
                    WHERE to_agent = ?
                    ORDER BY message_id DESC
                    LIMIT ?
                """, (agent_name, limit))

            rows = cur.fetchall()
            msg_ids = [r["message_id"] for r in rows]

            if mark_read and msg_ids:
                placeholders = ",".join("?" * len(msg_ids))
                conn.execute(
                    f"UPDATE messages SET status = 'read', read_at = ? WHERE message_id IN ({placeholders})",
                    [now] + msg_ids
                )

        results = []
        for r in rows:
            results.append({
                "message_id": r["message_id"],
                "conversation_id": r["conversation_id"],
                "from": r["from_agent"],
                "to": r["to_agent"],
                "topic": r["topic"],
                "content": r["content"],
                "status": "read" if mark_read else r["status"],
                "created_at": r["created_at"]
            })
        return results

    def fetch_history(self, agent_a: str, agent_b: str, limit: int = 20) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute("""
                SELECT message_id, from_agent, to_agent, topic, content, status, created_at
                FROM messages
                WHERE (from_agent = ? AND to_agent = ?) OR (from_agent = ? AND to_agent = ?)
                ORDER BY message_id DESC
                LIMIT ?
            """, (agent_a, agent_b, agent_b, agent_a, limit))
            rows = cur.fetchall()

        results = []
        for r in reversed(rows):
            results.append({
                "message_id": r["message_id"],
                "from": r["from_agent"],
                "to": r["to_agent"],
                "topic": r["topic"],
                "content": r["content"],
                "status": r["status"],
                "created_at": r["created_at"]
            })
        return results

    def list_agents(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute("""
                SELECT agent_id, framework, doorbell_type, doorbell_target, status, last_seen
                FROM agents
                ORDER BY last_seen DESC
            """)
            rows = cur.fetchall()

        return [
            {
                "agent_id": r["agent_id"],
                "framework": r["framework"],
                "doorbell_type": r["doorbell_type"],
                "doorbell_target": r["doorbell_target"],
                "status": r["status"],
                "last_seen": r["last_seen"]
            }
            for r in rows
        ]

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)
