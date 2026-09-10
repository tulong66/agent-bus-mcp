"""
Doorbell driver for Antigravity (Google Gemini CLI / IDE).
Handles reactive wakeup trigger and legacy Superconductor inbox bridge.
"""

import time
from pathlib import Path
from typing import Dict, Any
from .file_touch import FileTouchDoorbell

class AntigravityDoorbell(FileTouchDoorbell):
    def ring(self, agent_info: Dict[str, Any], message_content: str) -> bool:
        agent_id = agent_info.get("agent_id", "antigravity-lead")

        # 1. Base file touch in ~/.agent-bus/doorbells/{agent_id}.bell and inbox/{agent_id}.msg
        ok = super().ring(agent_info, message_content)

        # 2. Trigger FIFO if active
        fifo_path = Path.home() / ".agent-bus" / "doorbells" / f"{agent_id}.fifo"
        if fifo_path.exists():
            try:
                fd = os.open(str(fifo_path), os.O_WRONLY | os.O_NONBLOCK)
                os.write(fd, b"WAKE\n")
                os.close(fd)
            except OSError:
                pass

        return ok

