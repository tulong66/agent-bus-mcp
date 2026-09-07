"""
Unit and integration tests for agent-bus-mcp.
"""

import sys
import tempfile
import time
from pathlib import Path
import pytest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from agent_bus.db import Database
from agent_bus.server import MCPServer
from agent_bus.doorbells.manager import DoorbellManager


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_bus.db"
        yield Database(db_path)


def test_db_initialization_and_wal(temp_db):
    with temp_db.get_connection() as conn:
        row = conn.execute("PRAGMA journal_mode;").fetchone()
        assert row[0].lower() == "wal"


def test_agent_registration(temp_db):
    res = temp_db.register_agent(
        agent_id="claude-test",
        framework="claude-code",
        doorbell_type="file"
    )
    assert res["status"] == "registered"
    assert res["agent_id"] == "claude-test"

    agent = temp_db.get_agent("claude-test")
    assert agent is not None
    assert agent["framework"] == "claude-code"
    assert agent["status"] == "active"


def test_send_and_fetch_inbox(temp_db):
    temp_db.register_agent("alice", "generic")
    temp_db.register_agent("bob", "generic")

    send_res = temp_db.send_message(
        from_agent="alice",
        to_agent="bob",
        content="Hello Bob!",
        topic="greeting"
    )
    assert send_res["status"] == "delivered"
    assert send_res["message_id"] == 1

    # Fetch unread
    inbox = temp_db.fetch_inbox("bob", unread_only=True, mark_read=True)
    assert len(inbox) == 1
    assert inbox[0]["content"] == "Hello Bob!"
    assert inbox[0]["from"] == "alice"
    assert inbox[0]["status"] == "read"

    # Fetch again, should be empty now
    inbox2 = temp_db.fetch_inbox("bob", unread_only=True)
    assert len(inbox2) == 0

    # Fetch all
    inbox_all = temp_db.fetch_inbox("bob", unread_only=False)
    assert len(inbox_all) == 1


def test_dialogue_history(temp_db):
    temp_db.send_message("alice", "bob", "Message 1")
    temp_db.send_message("bob", "alice", "Message 2")
    temp_db.send_message("alice", "bob", "Message 3")

    history = temp_db.fetch_history("alice", "bob")
    assert len(history) == 3
    assert history[0]["content"] == "Message 1"
    assert history[1]["content"] == "Message 2"
    assert history[2]["content"] == "Message 3"


def test_doorbell_manager():
    dm = DoorbellManager()
    with tempfile.TemporaryDirectory() as tmpdir:
        bell_file = Path(tmpdir) / "test_agent.bell"
        agent_info = {
            "agent_id": "test_agent",
            "framework": "generic",
            "doorbell_type": "file",
            "doorbell_target": str(bell_file)
        }
        ok = dm.ring(agent_info, "Hello bell!")
        assert ok is True
        assert bell_file.exists()
        assert bell_file.stat().st_size > 0


def test_mcp_server_protocol(temp_db):
    server = MCPServer(db=temp_db)

    # 1. initialize
    init_resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    })
    assert init_resp["result"]["serverInfo"]["name"] == "agent-bus"

    # 2. tools/list
    tools_resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    })
    tool_names = [t["name"] for t in tools_resp["result"]["tools"]]
    assert "bus_send" in tool_names
    assert "bus_inbox" in tool_names
    assert "bus_history" in tool_names
    assert "bus_register" in tool_names
    assert "bus_list_agents" in tool_names

    # 3. tools/call bus_send
    call_resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "bus_send",
            "arguments": {
                "from_agent": "system",
                "to": "antigravity-lead",
                "content": "Automated MCP test"
            }
        }
    })
    assert call_resp["result"]["isError"] is False
