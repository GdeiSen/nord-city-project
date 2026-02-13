from typing import Dict, List, TYPE_CHECKING
from .base_manager import BaseManager

if TYPE_CHECKING:
    from bot import Bot


class ManagerRegistry:
    """Реестр менеджеров для автоматической регистрации и инициализации"""
    
    def __init__(self, bot: "Bot"):
        """
        Инициализация реестра менеджеров
        
        Args:
            bot: Экземпляр бота
        """
        self.bot = bot
        self._managers: Dict[str, BaseManager] = {}
    
    def register_manager(self, manager: BaseManager) -> None:
        """
        Регистрация менеджера в реестре
        
        Args:
            manager: Экземпляр менеджера
        """
        name = manager.get_name()
        self._managers[name] = manager
        # Создаем атрибут для прямого доступа
        setattr(self, name, manager)
    
    def get_manager(self, name: str) -> BaseManager:
        """
        Получение менеджера по имени
        
        Args:
            name: Имя менеджера
            
        Returns:
            Экземпляр менеджера
        """
        return self._managers.get(name)
    
    def get_all_managers(self) -> List[BaseManager]:
        """Получение списка всех зарегистрированных менеджеров"""
        return list(self._managers.values())
    
    async def initialize_all(self) -> None:
        """Инициализация всех зарегистрированных менеджеров"""
        for name, manager in self._managers.items():
            try:
                await manager.initialize()
                print(f"Manager '{name}' initialized successfully")
            except Exception as e:
                print(f"Error initializing manager '{name}': {e}")
    
    def __getattr__(self, name: str) -> BaseManager:
        """Позволяет обращаться к менеджерам через точечную нотацию"""
        if name in self._managers:
            return self._managers[name]
        raise AttributeError(f"Manager '{name}' not found") 