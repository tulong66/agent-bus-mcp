"""
Doorbell dispatcher manager.
Routes wakeup requests to appropriate agent doorbell drivers.
"""

from typing import Dict, Any
from .base import BaseDoorbell
from .file_touch import FileTouchDoorbell
from .antigravity import AntigravityDoorbell
from .dsh import DSHDoorbell
from .claude import ClaudeDoorbell


class DoorbellManager:
    def __init__(self):
        self._drivers: Dict[str, BaseDoorbell] = {
            "file": FileTouchDoorbell(),
            "antigravity": AntigravityDoorbell(),
            "dsh": DSHDoorbell(),
            "claude": ClaudeDoorbell(),
            "claude-code": ClaudeDoorbell(),
        }
        self._default = FileTouchDoorbell()

    def ring(self, agent_info: Dict[str, Any], message_content: str) -> bool:
        framework = agent_info.get("framework", "").lower()
        doorbell_type = agent_info.get("doorbell_type", "").lower()
        agent_id = agent_info.get("agent_id", "").lower()
        target = str(agent_info.get("doorbell_target") or "")

        if "antigravity" in framework or "antigravity" in agent_id:
            driver = self._drivers["antigravity"]
        elif (
            "claude" in framework
            or "claude" in agent_id
            or "coordinator" in agent_id
            or doorbell_type in ("claude", "claude-code")
            or ".sock" in target
        ):
            driver = self._drivers["claude"]
        elif "dsh" in framework or "deepseek" in framework:
            driver = self._drivers["dsh"]
        else:
            driver = self._drivers.get(doorbell_type, self._default)

        return driver.ring(agent_info, message_content)
