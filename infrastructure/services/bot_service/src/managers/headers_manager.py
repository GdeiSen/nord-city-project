from typing import Dict, TYPE_CHECKING
from .base_manager import BaseManager

if TYPE_CHECKING:
    from bot import Bot


class HeadersManager(BaseManager):
    """Менеджер для управления заголовками и конфигурацией"""
    
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self.headers: Dict[str, str] = {}
    
    async def initialize(self) -> None:
        """Инициализация менеджера заголовков"""
        print("HeadersManager initialized")
    
    def set(self, key: str, value: str) -> None:
        """
        Установка значения заголовка
        
        Args:
            key: Ключ заголовка
            value: Значение заголовка
        """
        self.headers[key] = value
    
    def get(self, key: str) -> str:
        """
        Получение значения заголовка
        
        Args:
            key: Ключ заголовка
            
        Returns:
            Значение заголовка или None
        """
        return self.headers.get(key)
    
    def get_all(self) -> Dict[str, str]:
        """
        Получение всех заголовков
        
        Returns:
            Словарь со всеми заголовками
        """
        return self.headers.copy()
    
    def clear(self) -> None:
        """Очистка всех заголовков"""
        self.headers.clear()
    
    def has(self, key: str) -> bool:
        """
        Проверка наличия заголовка
        
        Args:
            key: Ключ заголовка
            
        Returns:
            True если заголовок существует, False иначе
        """
        return key in self.headers
    
    def delete(self, key: str) -> None:
        """
        Удаление заголовка
        
        Args:
            key: Ключ заголовка для удаления
        """
        if key in self.headers:
            del self.headers[key]
    
    def update(self, headers: Dict[str, str]) -> None:
        """
        Обновление нескольких заголовков
        
        Args:
            headers: Словарь с заголовками для обновления
        """
        self.headers.update(headers) 