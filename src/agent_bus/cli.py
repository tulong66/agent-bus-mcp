#!/usr/bin/env python3
"""
CLI entry point for agent-bus-mcp.
"""

import sys
import os
import argparse
import time
from pathlib import Path

# Ensure package importability
current_dir = Path(__file__).resolve().parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from agent_bus.db import Database
from agent_bus.doorbells import DoorbellManager


def cmd_send(args, db: Database, doorbells: DoorbellManager):
    res = db.send_message(
        from_agent=args.sender,
        to_agent=args.to,
        content=args.content,
        topic=args.topic,
        conversation_id=args.conv
    )
    agent_info = db.get_agent(args.to)
    if not agent_info:
        agent_info = {"agent_id": args.to, "framework": "generic", "doorbell_type": "file"}
    doorbells.ring(agent_info, args.content)
    print(f"✅ Delivered message #{res['message_id']} from [{args.sender}] -> [{args.to}] (topic: {args.topic})")


def cmd_inbox(args, db: Database):
    unread_only = not args.all
    msgs = db.fetch_inbox(
        agent_name=args.agent,
        unread_only=unread_only,
        mark_read=not args.no_mark_read,
        limit=args.limit
    )
    if not msgs:
        status_str = "unread " if unread_only else ""
        print(f"Inbox empty: No {status_str}messages for [{args.agent}].")
        return

    print(f"📬 === Inbox for [{args.agent}] ({len(msgs)} messages) ===")
    for m in msgs:
        ts_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(m['created_at']))
        print(f"\n[#{m['message_id']}] From: {m['from']} | Topic: {m['topic']} | Time: {ts_str}")
        print(m['content'])


def cmd_history(args, db: Database):
    history = db.fetch_history(args.agent_a, args.agent_b, limit=args.limit)
    if not history:
        print(f"No dialogue history found between [{args.agent_a}] and [{args.agent_b}].")
        return

    print(f"📜 === Dialogue History: [{args.agent_a}] <-> [{args.agent_b}] ({len(history)} messages) ===")
    for m in history:
        ts_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(m['created_at']))
        print(f"\n[#{m['message_id']}] {m['from']} -> {m['to']} [{m['topic']}] ({ts_str}):")
        print(m['content'])


def cmd_agents(args, db: Database):
    agents = db.list_agents()
    print(f"{'AGENT ID':<25} {'FRAMEWORK':<15} {'STATUS':<10} {'DOORBELL TARGET'}")
    print("-" * 80)
    for a in agents:
        print(f"{a['agent_id']:<25} {a['framework']:<15} {a['status']:<10} {a.get('doorbell_target') or '-'}")


def cmd_register(args, db: Database):
    res = db.register_agent(
        agent_id=args.agent_id,
        framework=args.framework,
        doorbell_type=args.doorbell_type,
        doorbell_target=args.doorbell_target
    )
    print(f"✅ Registered agent [{res['agent_id']}] ({res['framework']}) with target: {res['doorbell_target']}")


def cmd_listen(args, db: Database):
    agent_id = args.agent
    bell_file = Path.home() / ".agent-bus" / "doorbells" / f"{agent_id}.bell"
    inbox_file = Path.home() / ".agent-bus" / "inbox" / f"{agent_id}.msg"

    bell_file.parent.mkdir(parents=True, exist_ok=True)
    if not bell_file.exists():
        bell_file.touch()

    start_mtime = bell_file.stat().st_mtime

    timeout = args.timeout
    start_t = time.time()
    print(f"👂 Listening for doorbells on [{agent_id}] (timeout {timeout}s)...", flush=True)
    while time.time() - start_t < timeout:
        if bell_file.exists() and bell_file.stat().st_mtime > start_mtime:
            print(f"🔔 Doorbell rung for [{agent_id}]!", flush=True)
            msgs = db.fetch_inbox(agent_name=agent_id, unread_only=True, mark_read=True)
            if msgs:
                for m in msgs:
                    ts_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(m['created_at']))
                    print(f"\n【来自 {m['from']} 的实时消息】（主题: {m['topic']} | 时间: {ts_str}）\n{m['content']}", flush=True)
            elif inbox_file.exists():
                try:
                    content = inbox_file.read_text(encoding="utf-8").strip()
                    if content:
                        print(f"\n【收件箱内容】：\n{content}", flush=True)
                except Exception:
                    pass
            sys.exit(0)
        time.sleep(0.1)
    print("⏰ Listen timeout.", flush=True)
    sys.exit(1)



def main():
    parser = argparse.ArgumentParser(description="Universal Multi-Agent Communication Bus CLI")
    subparsers = parser.add_subparsers(dest="command")

    # send
    p_send = subparsers.add_parser("send", help="Send a message to another agent")
    p_send.add_argument("--to", required=True, help="Target agent ID")
    p_send.add_argument("--from", dest="sender", default="user", help="Sender agent ID (default: user)")
    p_send.add_argument("--topic", default="general", help="Message topic")
    p_send.add_argument("--conv", default="", help="Conversation ID")
    p_send.add_argument("content", help="Message body")

    # inbox
    p_inbox = subparsers.add_parser("inbox", help="View messages in an agent's inbox")
    p_inbox.add_argument("--agent", required=True, help="Agent ID to check")
    p_inbox.add_argument("--all", action="store_true", help="Include already read messages")
    p_inbox.add_argument("--no-mark-read", action="store_true", help="Do not mark messages as read")
    p_inbox.add_argument("--limit", type=int, default=10, help="Max messages to fetch")

    # history
    p_hist = subparsers.add_parser("history", help="View conversation history between two agents")
    p_hist.add_argument("agent_a", help="First agent ID")
    p_hist.add_argument("agent_b", help="Second agent ID")
    p_hist.add_argument("--limit", type=int, default=20, help="Max history messages")

    # agents
    subparsers.add_parser("agents", help="List registered agents on the bus")

    # register
    p_reg = subparsers.add_parser("register", help="Register or update an agent")
    p_reg.add_argument("agent_id", help="Agent ID")
    p_reg.add_argument("--framework", default="generic", help="Agent framework (antigravity, claude-code, dsh, codex)")
    p_reg.add_argument("--doorbell-type", default="file", help="Doorbell type (file, socket, signal)")
    p_reg.add_argument("--doorbell-target", help="Doorbell target file/port")

    # listen
    p_lis = subparsers.add_parser("listen", help="Block until a doorbell rings for an agent")
    p_lis.add_argument("--agent", required=True, help="Agent ID to listen for")
    p_lis.add_argument("--timeout", type=float, default=600.0, help="Timeout in seconds")

    args = parser.parse_args()
    db = Database()
    doorbells = DoorbellManager()

    if args.command == "send":
        cmd_send(args, db, doorbells)
    elif args.command == "inbox":
        cmd_inbox(args, db)
    elif args.command == "history":
        cmd_history(args, db)
    elif args.command == "agents":
        cmd_agents(args, db)
    elif args.command == "register":
        cmd_register(args, db)
    elif args.command == "listen":
        cmd_listen(args, db)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
