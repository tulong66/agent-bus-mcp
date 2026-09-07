"""
Doorbell driver for DeepSeek Harness (DSH).
Supports native Unix domain socket prompt injection (~/.dsh-tui/inject/*.sock),
file touch, and FIFO signaling.
"""

import os
import json
import socket
from pathlib import Path
from typing import Dict, Any
from .file_touch import FileTouchDoorbell


class DSHDoorbell(FileTouchDoorbell):
    def ring(self, agent_info: Dict[str, Any], message_content: str) -> bool:
        ok = super().ring(agent_info, message_content)

        agent_id = agent_info.get("agent_id", "deepseek-coder")
        from_agent = agent_info.get("from_agent", "another agent")
        topic = agent_info.get("topic", "general")

        # 1. Native DSH-TUI Socket Wakeup Channel
        inject_servers_file = Path.home() / ".dsh-tui" / "inject" / "servers.json"
        if inject_servers_file.exists():
            try:
                with open(inject_servers_file, "r", encoding="utf-8") as f:
                    servers = json.load(f)
                if isinstance(servers, list):
                    # Sort by startedAt descending so most recent session is prioritized
                    sorted_servers = sorted(servers, key=lambda x: x.get("startedAt", 0), reverse=True)
                    delivered_any = False
                    for server in sorted_servers:
                        pid = server.get("pid")
                        sock_p = server.get("socketPath")
                        if pid and sock_p and Path(sock_p).exists():
                            try:
                                os.kill(pid, 0)  # probe if alive
                            except OSError:
                                continue

                            try:
                                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                                s.settimeout(2.0)
                                s.connect(sock_p)
                                prompt_text = f"收到来自 {from_agent} 的新消息（主题: {topic}）。请调用 bus_inbox(wait=false) 查收并处理。"
                                s.sendall((json.dumps({"type": "prompt.append", "text": prompt_text}) + "\n").encode("utf-8"))
                                s.sendall((json.dumps({"type": "command.execute", "command": "prompt.submit"}) + "\n").encode("utf-8"))
                                s.close()
                                delivered_any = True
                            except Exception:
                                pass
                    if delivered_any:
                        return True
            except Exception:
                pass

        # 2. Check explicit or default FIFO candidates fallback
        target = agent_info.get("doorbell_target", "")
        fifo_candidates = []
        if target:
            fifo_candidates.append(Path(target))
        fifo_candidates.append(Path.home() / ".agent-bus" / "doorbells" / f"{agent_id}.fifo")
        fifo_candidates.append(Path.home() / ".superconductor" / "inbox" / "dsh.fifo")

        for fifo_p in fifo_candidates:
            if fifo_p.exists():
                try:
                    fd = os.open(str(fifo_p), os.O_WRONLY | os.O_NONBLOCK)
                    with os.fdopen(fd, "w") as fifo:
                        fifo.write("WAKE\n")
                    return True
                except OSError:
                    pass

        return ok

