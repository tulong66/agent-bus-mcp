"""
Doorbell driver for Claude Code (CLI / Terminal mode).
Communicates via Claude Code's native Unix Domain Socket messaging protocol
(CLAUDE_CODE_MESSAGING_SOCKET with CLAUDE_CODE_MESSAGING_TOKEN).
"""

import os
import json
import socket
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from .file_touch import FileTouchDoorbell


class ClaudeDoorbell(FileTouchDoorbell):
    """
    Rings Claude Code using native Cross-Session Unix Domain Socket (UDS).
    Falls back to file touch for offline archive and local inbox sync.
    """

    def ring(self, agent_info: Dict[str, Any], message_content: str) -> bool:
        # 1. Base file touch in ~/.agent-bus (archive / fallback)
        ok = super().ring(agent_info, message_content)

        # 2. Resolve socket and token
        sock_path, token = self._resolve_socket_and_token(agent_info)
        if not sock_path or not os.path.exists(sock_path):
            return ok

        # 3. Deliver via Claude Code native UDS
        try:
            from_agent = agent_info.get("from_agent", "agent-bus")
            topic = agent_info.get("topic", "general")
            prompt_text = (
                f"【来自 {from_agent} 的消息】（主题: {topic}）：\n\n"
                f"{message_content}\n\n"
                f"（提示：消息已直接注入当前上下文，无需调用 bus_inbox。任务完成后调用 bus_send(to='{from_agent}', message='...') 回复即可）"
            )

            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(3.0)
            s.connect(sock_path)

            # Protocol: auth line (if token present), then user message line
            if token:
                auth_line = json.dumps({"type": "auth", "token": token}) + "\n"
                s.sendall(auth_line.encode("utf-8"))

            msg_line = json.dumps({
                "type": "user",
                "message": {
                    "role": "user",
                    "content": prompt_text
                }
            }) + "\n"
            s.sendall(msg_line.encode("utf-8"))
            s.close()
            return True
        except Exception:
            # Socket delivery failed, file touch succeeded as fallback
            return ok

    def _resolve_socket_and_token(self, agent_info: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        target = agent_info.get("doorbell_target")
        if target:
            # Check if JSON encoded target {"socket": ..., "token": ...}
            if target.startswith("{"):
                try:
                    d = json.loads(target)
                    return d.get("socket"), d.get("token")
                except Exception:
                    pass
            # Check if socket:token format
            if ":" in target and "/" in target:
                parts = target.rsplit(":", 1)
                if os.path.exists(parts[0]):
                    return parts[0], parts[1]
            elif target.endswith(".sock") and os.path.exists(target):
                # Try to get token from env if matches
                env_sock = os.environ.get("CLAUDE_CODE_MESSAGING_SOCKET")
                env_token = os.environ.get("CLAUDE_CODE_MESSAGING_TOKEN")
                if env_sock == target:
                    return target, env_token
                return target, None

        # Check current process environment
        env_sock = os.environ.get("CLAUDE_CODE_MESSAGING_SOCKET")
        env_token = os.environ.get("CLAUDE_CODE_MESSAGING_TOKEN")
        if env_sock and os.path.exists(env_sock):
            return env_sock, env_token

        # Check /tmp/cc-socks/ for active sockets
        socks_dir = Path("/tmp/cc-socks")
        if socks_dir.exists():
            active_socks = sorted(socks_dir.glob("*.sock"), key=lambda x: x.stat().st_mtime, reverse=True)
            if active_socks:
                # Test connectivity to most recent socket
                for s_path in active_socks:
                    try:
                        test_s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        test_s.settimeout(0.5)
                        test_s.connect(str(s_path))
                        test_s.close()
                        return str(s_path), env_token
                    except Exception:
                        continue

        return None, None
