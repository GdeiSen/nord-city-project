# ./services/base_service.py
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot


class BaseService(ABC):
    """Base class for all services"""

    def __init__(self, bot: "Bot"):
        """
        Initialize the base service.

        Args:
            bot: The bot instance, providing access to managers and other components.
        """
        self.bot = bot

    @abstractmethod
    async def initialize(self) -> None:
        """
        Asynchronously initialize the service.
        This method must be implemented in every subclass and is called upon bot startup.
        """
        pass

    def get_name(self) -> str:
        """
        Returns the service name (the class name without 'Service' in lowercase).
        e.g., 'StatsService' becomes 'stats'.
        """
        class_name = self.__class__.__name__
        if class_name.endswith('Service'):
            return class_name[:-7].lower()
        return class_name.lower()