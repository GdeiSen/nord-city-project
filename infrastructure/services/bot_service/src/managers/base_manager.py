from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Bot


class BaseManager(ABC):
    """Базовый класс для всех менеджеров"""
    
    def __init__(self, bot: "Bot"):
        """
        Инициализация базового менеджера
        
        Args:
            bot: Экземпляр бота
        """
        self.bot = bot
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Асинхронная инициализация менеджера
        Должна быть реализована в каждом наследнике
        """
        pass
    
    def get_name(self) -> str:
        """Возвращает имя менеджера (имя класса без 'Manager')"""
        class_name = self.__class__.__name__
        if class_name.endswith('Manager'):
            return class_name[:-7].lower()  # Убираем 'Manager' и делаем lowercase
        return class_name.lower() 