"""
Unit and integration tests for agent-bus-mcp.
"""

import sys
import tempfile
import time
import json
import socket
import threading
from pathlib import Path
import pytest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from agent_bus.db import Database
from agent_bus.server import MCPServer
from agent_bus.doorbells.manager import DoorbellManager
from agent_bus.doorbells.claude import ClaudeDoorbell


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
        doorbell_type="claude"
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


def test_doorbell_manager_and_claude_uds():
    dm = DoorbellManager()
    with tempfile.TemporaryDirectory() as tmpdir:
        sock_path = str(Path(tmpdir) / "test_claude.sock")
        token = "test-token-123"

        received_lines = []
        server_ready = threading.Event()

        def mock_server():
            server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server_sock.bind(sock_path)
            server_sock.listen(1)
            server_ready.set()
            conn, _ = server_sock.accept()
            f = conn.makefile("r")
            for line in f:
                received_lines.append(line.strip())
            conn.close()
            server_sock.close()

        th = threading.Thread(target=mock_server, daemon=True)
        th.start()
        server_ready.wait(timeout=2.0)

        agent_info = {
            "agent_id": "coordinator",
            "framework": "claude-code",
            "doorbell_type": "claude",
            "doorbell_target": json.dumps({"socket": sock_path, "token": token}),
            "from_agent": "antigravity-lead",
            "topic": "task"
        }

        ok = dm.ring(agent_info, "Task for coordinator!")
        assert ok is True
        th.join(timeout=2.0)

        assert len(received_lines) == 2
        auth_msg = json.loads(received_lines[0])
        assert auth_msg["type"] == "auth"
        assert auth_msg["token"] == token

        user_msg = json.loads(received_lines[1])
        assert user_msg["type"] == "user"
        assert "Task for coordinator!" in user_msg["message"]["content"]


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
    assert "bus_wait_message" in tool_names
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


def test_bus_wait_message(temp_db):
    server = MCPServer(db=temp_db)

    def sender():
        time.sleep(0.3)
        temp_db.send_message("lead", "worker", "Delayed message", "ping")

    th = threading.Thread(target=sender, daemon=True)
    th.start()

    call_resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "bus_wait_message",
            "arguments": {
                "agent_name": "worker",
                "timeout": 2
            }
        }
    })
    assert call_resp["result"]["isError"] is False
    content_text = call_resp["result"]["content"][0]["text"]
    res_obj = json.loads(content_text)
    assert res_obj["status"] == "received"
    assert len(res_obj["messages"]) == 1
    assert res_obj["messages"][0]["content"] == "Delayed message"
