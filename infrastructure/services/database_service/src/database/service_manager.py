import logging
from typing import Dict, Any, Type

logger = logging.getLogger(__name__)

class ServiceManager:
    """
    Manages the lifecycle and access to all business logic services.
    It holds a registry of service instances, accessible by a unique string key,
    making them available throughout the application.
    """
    def __init__(self):
        self._services: Dict[str, Any] = {}
        logger.info("ServiceManager initialized.")

    def register(self, service_name: str, service_instance: Any):
        """
        Registers a service instance with a given name.
        If a service with this name already exists, it will be overwritten.

        Args:
            service_name: A unique string key for the service (e.g., 'user', 'feedback').
            service_instance: The instance of the service class to register.
        """
        if service_name in self._services:
            logger.warning(f"Service '{service_name}' is being overwritten.")
        self._services[service_name] = service_instance
        logger.info(f"Registered service: '{service_name}'")

    def get(self, service_name: str) -> Any:
        """
        Retrieves a service instance by its name.

        Args:
            service_name: The string key of the service.

        Returns:
            The service instance.

        Raises:
            KeyError: If no service with the given name has been registered.
        """
        if service_name not in self._services:
            raise KeyError(f"Service '{service_name}' not found. "
                           "Ensure it is registered in DatabaseManager.")
        return self._services[service_name]

    def get_all_services(self) -> Dict[str, Any]:
        """
        Returns a dictionary of all registered services.

        Returns:
            A dictionary mapping service names to service instances.
        """
        return self._services