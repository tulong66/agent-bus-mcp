"""
Standard file-touch doorbell driver.
Touches a doorbell bell file and appends message to recipient inbox file.
"""

import time
from pathlib import Path
from typing import Dict, Any
from .base import BaseDoorbell

class FileTouchDoorbell(BaseDoorbell):
    def ring(self, agent_info: Dict[str, Any], message_content: str) -> bool:
        agent_id = agent_info["agent_id"]
        target = agent_info.get("doorbell_target")
        
        if target and not target.startswith("{"):
            bell_path = Path(target)
        else:
            bell_path = Path.home() / ".agent-bus" / "doorbells" / f"{agent_id}.bell"
        inbox_path = Path.home() / ".agent-bus" / "inbox" / f"{agent_id}.msg"

        now_ts = time.time()
        try:
            bell_path.parent.mkdir(parents=True, exist_ok=True)
            with open(bell_path, "w", encoding="utf-8") as f:
                f.write(f"{now_ts}\n")
        except Exception:
            return False

        try:
            inbox_path.parent.mkdir(parents=True, exist_ok=True)
            with open(inbox_path, "a", encoding="utf-8") as f:
                f.write(f"{message_content}\n")
        except Exception:
            pass

        return True
