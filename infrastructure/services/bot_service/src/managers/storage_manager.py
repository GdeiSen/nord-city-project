from typing import Any, TYPE_CHECKING
from .base_manager import BaseManager

if TYPE_CHECKING:
    from telegram.ext import ContextTypes
    from bot import Bot


class StorageManager(BaseManager):
    """Менеджер для управления локальным хранилищем данных"""
    
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
    
    async def initialize(self) -> None:
        """Инициализация менеджера хранилища"""
        print("StorageManager initialized")
    
    def get(self, context: "ContextTypes.DEFAULT_TYPE", key: int) -> Any:
        """
        Получение значения из хранилища
        
        Args:
            context: Контекст Telegram
            key: Ключ для получения данных
            
        Returns:
            Значение или None если ключ не найден
        """
        if context.user_data:
            return context.user_data.get(key)
        return None
    
    def set(self, context: "ContextTypes.DEFAULT_TYPE", key: int, value: Any) -> None:
        """
        Сохранение значения в хранилище
        
        Args:
            context: Контекст Telegram
            key: Ключ для сохранения данных
            value: Значение для сохранения
        """
        if context.user_data is not None:
            context.user_data[key] = value
    
    def delete(self, context: "ContextTypes.DEFAULT_TYPE", key: int) -> None:
        """
        Удаление значения из хранилища
        
        Args:
            context: Контекст Telegram
            key: Ключ для удаления данных
        """
        if context.user_data and key in context.user_data:
            del context.user_data[key]
    
    def clear(self, context: "ContextTypes.DEFAULT_TYPE") -> None:
        """
        Очистка всех данных из хранилища
        
        Args:
            context: Контекст Telegram
        """
        if context.user_data:
            context.user_data.clear()
    
    def has(self, context: "ContextTypes.DEFAULT_TYPE", key: int) -> bool:
        """
        Проверка наличия ключа в хранилище
        
        Args:
            context: Контекст Telegram
            key: Ключ для проверки
            
        Returns:
            True если ключ существует, False иначе
        """
        if context.user_data:
            return key in context.user_data
        return False
    
    def get_all_keys(self, context: "ContextTypes.DEFAULT_TYPE") -> list:
        """
        Получение всех ключей из хранилища
        
        Args:
            context: Контекст Telegram
            
        Returns:
            Список всех ключей
        """
        if context.user_data:
            return list(context.user_data.keys())
        return [] 