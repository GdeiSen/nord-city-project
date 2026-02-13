from typing import Dict, List, Callable, Any, Coroutine, TYPE_CHECKING
from .base_manager import BaseManager

if TYPE_CHECKING:
    from bot import Bot


class EventManager(BaseManager):
    """Менеджер для управления событиями и обработчиками ввода"""
    
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
        self._events: Dict[str, List[Callable[..., Coroutine[Any, Any, Any]]]] = {}
        self._input_handlers: Dict[int, Callable[..., Coroutine[Any, Any, Any]]] = {}
        self._active_dialog_type: Dict[int, int] = {}  # user_id -> dialog_state
    
    async def initialize(self) -> None:
        """Инициализация менеджера событий"""
        print("EventManager initialized")
    
    def on(self, event_name: str, handler: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        """
        Регистрация обработчика события
        
        Args:
            event_name: Имя события
            handler: Асинхронная функция-обработчик
        """
        if event_name not in self._events:
            self._events[event_name] = []
        self._events[event_name].append(handler)
    
    def off(self, event_name: str, handler: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        """
        Удаление обработчика события
        
        Args:
            event_name: Имя события
            handler: Функция-обработчик для удаления
        """
        if event_name in self._events and handler in self._events[event_name]:
            self._events[event_name].remove(handler)
    
    async def once(self, event_name: str, handler: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        """
        Регистрация одноразового обработчика события
        
        Args:
            event_name: Имя события
            handler: Асинхронная функция-обработчик
        """
        async def one_time_handler(*args, **kwargs):
            result = await handler(*args, **kwargs)
            self.off(event_name, one_time_handler)
            return result
            
        self.on(event_name, one_time_handler)
    
    async def emit(self, event_name: str, *args, **kwargs) -> List[Any]:
        """
        Генерация события
        
        Args:
            event_name: Имя события
            *args, **kwargs: Аргументы для передачи обработчикам
            
        Returns:
            Список результатов всех обработчиков
        """
        results = []
        if event_name in self._events:
            for handler in self._events[event_name]:
                try:
                    result = await handler(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    print(f"Error in event handler for '{event_name}': {e}")
        return results
    
    def register_input_handler(self, user_id: int, dialog_type: int, handler: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        """
        Регистрация обработчика ввода для пользователя
        
        Args:
            user_id: ID пользователя
            dialog_type: Тип диалога (текстовый ввод, фото и т.д.)
            handler: Асинхронная функция-обработчик
        """
        self._input_handlers[user_id] = handler
        self._active_dialog_type[user_id] = dialog_type
    
    def remove_input_handler(self, user_id: int) -> None:
        """
        Удаление обработчика ввода для пользователя
        
        Args:
            user_id: ID пользователя
        """
        if user_id in self._input_handlers:
            del self._input_handlers[user_id]
        if user_id in self._active_dialog_type:
            del self._active_dialog_type[user_id]
    
    def get_input_handler(self, user_id: int) -> tuple[Callable[..., Coroutine[Any, Any, Any]] | None, int | None]:
        """
        Получение активного обработчика ввода для пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Кортеж (функция-обработчик, тип диалога) или (None, None)
        """
        handler = self._input_handlers.get(user_id)
        dialog_type = self._active_dialog_type.get(user_id)
        return handler, dialog_type
    
    def has_input_handler(self, user_id: int) -> bool:
        """
        Проверка наличия активного обработчика ввода для пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если обработчик существует, False иначе
        """
        return user_id in self._input_handlers
    
    def get_all_events(self) -> List[str]:
        """
        Получение списка всех зарегистрированных событий
        
        Returns:
            Список имен событий
        """
        return list(self._events.keys())
    
    def get_event_handlers_count(self, event_name: str) -> int:
        """
        Получение количества обработчиков для события
        
        Args:
            event_name: Имя события
            
        Returns:
            Количество зарегистрированных обработчиков
        """
        return len(self._events.get(event_name, []))
    
    def clear_all_events(self) -> None:
        """Очистка всех зарегистрированных событий"""
        self._events.clear()
    
    def clear_all_input_handlers(self) -> None:
        """Очистка всех обработчиков ввода"""
        self._input_handlers.clear()
        self._active_dialog_type.clear() 