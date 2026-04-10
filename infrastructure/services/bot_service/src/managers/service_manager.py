# ./managers/service_manager.py
import logging
from typing import Dict, List, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from bot import Bot
    from services.base_service import BaseService


logger = logging.getLogger(__name__)


class ServiceManager:
    """A registry for services to manage their lifecycle and access."""

    def __init__(self, bot: "Bot"):
        """
        Initializes the service manager.

        Args:
            bot: The bot instance.
        """
        self.bot = bot
        self._services: Dict[str, "BaseService"] = {}

    def register_service(self, service: "BaseService") -> None:
        """
        Registers a service instance in the manager.

        Args:
            service: An instance of a class derived from BaseService.
        """
        # Получаем имя класса и преобразуем к snake_case без суффикса 'Service'
        def camel_to_snake(name):
            s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        class_name = service.__class__.__name__
        if class_name.endswith('Service'):
            class_name = class_name[:-7]
        name = camel_to_snake(class_name)
        if name in self._services:
            logger.warning("Service '%s' is already registered. Overwriting.", name)
        self._services[name] = service
        setattr(self, name, service)

    def get_service(self, name: str) -> "BaseService":
        """
        Retrieves a registered service by its name.

        Args:
            name: The name of the service (e.g., 'stats').

        Returns:
            An instance of the service.
            
        Raises:
            AttributeError: If the service is not found.
        """
        service = self._services.get(name)
        if not service:
            raise AttributeError(f"Service '{name}' not found in ServiceManager")
        return service

    def get_all_services(self) -> List["BaseService"]:
        """Returns a list of all registered services."""
        return list(self._services.values())

    async def initialize_all(self) -> None:
        """Initializes all registered services by calling their 'initialize' method."""
        logger.info("Initializing services...")
        for name, service in self._services.items():
            try:
                await service.initialize()
                logger.info("Service '%s' initialized successfully.", name)
            except Exception as e:
                logger.exception("Error initializing service '%s': %s", name, e)
        logger.info("All services initialized.")

    def __getattr__(self, name: str) -> "BaseService":
        """
        Allows accessing services using dot notation (e.g., bot.services.stats).
        
        Raises:
            AttributeError: If the service is not found.
        """
        if name in self._services:
            return self._services[name]
        raise AttributeError(f"Service '{name}' not found in ServiceManager.")
