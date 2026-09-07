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
        # 1. Base file touch in ~/.agent-bus
        ok = super().ring(agent_info, message_content)

        # 2. Bridge to Superconductor inbox if active
        sc_inbox = Path.home() / ".superconductor" / "inbox" / "antigravity.msg"
        try:
            sc_inbox.parent.mkdir(parents=True, exist_ok=True)
            with open(sc_inbox, "a", encoding="utf-8") as f:
                f.write(f"{message_content}\n")
        except Exception:
            pass

        return ok
