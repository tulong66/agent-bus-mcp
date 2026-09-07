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
        
        # Check if a DSH FIFO or socket is specified in target
        target = agent_info.get("doorbell_target", "")
        if target.endswith(".fifo") and os.path.exists(target):
            try:
                # Non-blocking write to named pipe
                fd = os.open(target, os.O_WRONLY | os.O_NONBLOCK)
                with os.fdopen(fd, "w") as fifo:
                    fifo.write("WAKE\n")
            except OSError:
                pass

        return ok
