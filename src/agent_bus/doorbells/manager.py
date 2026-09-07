"""
Doorbell dispatcher manager.
Routes wakeup requests to appropriate agent doorbell drivers.
"""

from typing import Dict, Any
from .base import BaseDoorbell
from .file_touch import FileTouchDoorbell
from .antigravity import AntigravityDoorbell
from .dsh import DSHDoorbell

class DoorbellManager:
    def __init__(self):
        self._drivers: Dict[str, BaseDoorbell] = {
            "file": FileTouchDoorbell(),
            "antigravity": AntigravityDoorbell(),
            "dsh": DSHDoorbell(),
        }
        self._default = FileTouchDoorbell()

    def ring(self, agent_info: Dict[str, Any], message_content: str) -> bool:
        framework = agent_info.get("framework", "").lower()
        doorbell_type = agent_info.get("doorbell_type", "").lower()

        if "antigravity" in framework or "antigravity" in agent_info.get("agent_id", "").lower():
            driver = self._drivers["antigravity"]
        elif "dsh" in framework or "deepseek" in framework:
            driver = self._drivers["dsh"]
        else:
            driver = self._drivers.get(doorbell_type, self._default)

        return driver.ring(agent_info, message_content)
