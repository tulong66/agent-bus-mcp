"""
Doorbell driver for DeepSeek Harness (DSH).
Supports file touch and Unix domain socket / FIFO signaling.
"""

import os
from pathlib import Path
from typing import Dict, Any
from .file_touch import FileTouchDoorbell


class DSHDoorbell(FileTouchDoorbell):
    def ring(self, agent_info: Dict[str, Any], message_content: str) -> bool:
        ok = super().ring(agent_info, message_content)

        agent_id = agent_info.get("agent_id", "deepseek-coder")
        target = agent_info.get("doorbell_target", "")

        # Check explicit or default FIFO candidates
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
