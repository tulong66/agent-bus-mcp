"""
Base doorbell interface for heterogeneous agent wakeups.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseDoorbell(ABC):
    @abstractmethod
    def ring(self, agent_info: Dict[str, Any], message_content: str) -> bool:
        """Trigger wakeup signal for target agent."""
        pass
