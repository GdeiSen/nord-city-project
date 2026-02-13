from typing import Dict, List, Optional, Any, Union
from shared.entities.dialog import Dialog
from shared.entities.dialog_sequence import Sequence
from shared.entities.dialog_question import Question
from shared.entities.dialog_option import Option

class DialogGenerator:
    """
    Генератор динамических диалогов, реализующий паттерны Фабричный метод и Строитель.
    Позволяет создавать сложные диалоговые структуры с последовательностями, элементами и опциями.
    """
    
    def __init__(self, dialog_id: int = 1, trace: bool = True):
        """
        Инициализация генератора диалогов.
        
        Args:
            dialog_id: Уникальный идентификатор диалога
            trace: Включить трассировку диалога
        """
        self.dialog_id = dialog_id
        self.trace = trace
        
        # Счетчики для генерации уникальных ID
        self._sequence_counter = 0
        self._item_counter = 0
        self._option_counter = 0
        
        # Хранилища компонентов диалога
        self.sequences: Dict[int, Sequence] = {}
        self.items: Dict[int, Question] = {}
        self.options: Dict[int, Option] = {}
        
        # Текущий рабочий контекст для строителя
        self._current_sequence_id: Optional[int] = None
        self._current_item_id: Optional[int] = None
    
    def create_dialog(self) -> Dialog:
        """
        Фабричный метод для создания объекта диалога из накопленных компонентов.
        
        Returns:
            Dialog: Готовый объект диалога
        """
        return Dialog(
            id=self.dialog_id,
            sequences=self.sequences,
            items=self.items,
            options=self.options,
            trace=self.trace
        )
    
    def create_sequence(self, items_ids: List[int] = None, next_sequence_id: Optional[int] = None) -> int:
        """
        Создает новую последовательность и возвращает её идентификатор.
        
        Args:
            items_ids: Список ID элементов в последовательности
            next_sequence_id: ID следующей последовательности (для автоматического перехода)
            
        Returns:
            int: ID созданной последовательности
        """
        sequence_id = self._get_next_sequence_id()
        items_ids = items_ids or []
        
        sequence = Sequence(
            id=sequence_id,
            items_ids=items_ids,
            next_sequence_id=next_sequence_id,
            dialog_id=self.dialog_id
        )
        
        self.sequences[sequence_id] = sequence
        self._current_sequence_id = sequence_id
        return sequence_id
    
    def create_item(self, text: str, options_ids: List[int] = None, item_type: int = 0, images: List[str] = None) -> int:
        """
        Создает новый элемент диалога и возвращает его идентификатор.
        
        Args:
            text: Текст элемента (вопрос/сообщение)
            options_ids: Список ID опций для этого элемента
            item_type: Тип элемента (0 - выбор из опций, 1 - ввод текста)
            images: Список URL или путей к изображениям
            
        Returns:
            int: ID созданного элемента
        """
        item_id = self._get_next_item_id()
        options_ids = options_ids or []
        
        item = Question(
            id=item_id,
            text=text,
            options_ids=options_ids,
            type=item_type,
            dialog_id=self.dialog_id,
            images=images
        )
        
        self.items[item_id] = item
        self._current_item_id = item_id
        return item_id
    
    def create_option(self, text: str, target_sequence_id: Optional[int] = None, row: int = 0) -> int:
        """
        Создает новую опцию (вариант ответа) и возвращает её идентификатор.
        
        Args:
            text: Текст опции
            target_sequence_id: ID последовательности, на которую переходит диалог при выборе этой опции
            row: Номер строки для размещения опции в клавиатуре
            
        Returns:
            int: ID созданной опции
        """
        option_id = self._get_next_option_id()
        
        option = Option(
            id=option_id,
            text=text,
            sequence_id=target_sequence_id,
            row=row
        )
        
        self.options[option_id] = option
        return option_id
    
    def create_custom_button(self, text: str, callback_data: str, row: int = 0) -> int:
        """
        Создает новую опцию (кнопку) с произвольным callback_data и возвращает её идентификатор.
        
        Args:
            text: Текст кнопки
            callback_data: Произвольные данные для callback
            row: Номер строки для размещения кнопки в клавиатуре
            
        Returns:
            int: ID созданной опции
        """
        option_id = self._get_next_option_id()
        
        option = Option(
            id=option_id,
            text=text,
            sequence_id=None,  # Не привязываем к последовательности
            row=row,
            callback_data=callback_data  # Устанавливаем произвольный callback_data
        )
        
        self.options[option_id] = option
        return option_id
    
    def add_item_to_sequence(self, sequence_id: int, item_id: int) -> None:
        """
        Добавляет существующий элемент в указанную последовательность.
        
        Args:
            sequence_id: ID последовательности
            item_id: ID элемента
            
        Raises:
            ValueError: Если последовательность с указанным ID не существует
        """
        if sequence_id not in self.sequences:
            raise ValueError(f"Sequence with ID {sequence_id} does not exist")
            
        if item_id not in self.items:
            raise ValueError(f"Item with ID {item_id} does not exist")
            
        if item_id not in self.sequences[sequence_id].items_ids:
            self.sequences[sequence_id].items_ids.append(item_id)
    
    def add_option_to_item(self, item_id: int, option_id: int) -> None:
        """
        Добавляет существующую опцию к указанному элементу.
        
        Args:
            item_id: ID элемента
            option_id: ID опции
            
        Raises:
            ValueError: Если элемент или опция с указанным ID не существуют
        """
        if item_id not in self.items:
            raise ValueError(f"Item with ID {item_id} does not exist")
            
        if option_id not in self.options:
            raise ValueError(f"Option with ID {option_id} does not exist")
            
        if self.items[item_id].options_ids is None:
            self.items[item_id].options_ids = []
            
        if option_id not in self.items[item_id].options_ids:
            self.items[item_id].options_ids.append(option_id)
    
    def link_option_to_sequence(self, option_id: int, sequence_id: int) -> None:
        """
        Устанавливает целевую последовательность для опции.
        
        Args:
            option_id: ID опции
            sequence_id: ID последовательности
            
        Raises:
            ValueError: Если опция или последовательность с указанным ID не существуют
        """
        if option_id not in self.options:
            raise ValueError(f"Option with ID {option_id} does not exist")
            
        if sequence_id not in self.sequences:
            raise ValueError(f"Sequence with ID {sequence_id} does not exist")
            
        self.options[option_id].sequence_id = sequence_id
    
    def set_next_sequence(self, sequence_id: int, next_sequence_id: int) -> None:
        """
        Устанавливает следующую последовательность для автоматического перехода.
        
        Args:
            sequence_id: ID текущей последовательности
            next_sequence_id: ID следующей последовательности
            
        Raises:
            ValueError: Если последовательность с указанным ID не существует
        """
        if sequence_id not in self.sequences:
            raise ValueError(f"Sequence with ID {sequence_id} does not exist")
            
        if next_sequence_id not in self.sequences:
            raise ValueError(f"Next sequence with ID {next_sequence_id} does not exist")
            
        self.sequences[sequence_id].next_sequence_id = next_sequence_id
    
    def create_text_input_item(self, text: str) -> int:
        """
        Создает элемент для ввода текста пользователем.
        
        Args:
            text: Текст с инструкцией для пользователя
            
        Returns:
            int: ID созданного элемента
        """
        return self.create_item(text=text, item_type=1)
    
    def create_select_item(self, text: str, options: List[Dict[str, Any]] = None) -> int:
        """
        Создает элемент с выбором из нескольких вариантов и возвращает его ID.
        Также автоматически создает опции из переданного списка.
        
        Args:
            text: Текст вопроса/заголовка
            options: Список словарей с опциями в формате:
                    [{"text": "Опция 1", "sequence_id": 1, "row": 0}, ...]
                    
        Returns:
            int: ID созданного элемента
        """
        item_id = self.create_item(text=text, item_type=0)
        
        if options:
            options_ids = []
            for opt in options:
                option_id = self.create_option(
                    text=opt["text"], 
                    target_sequence_id=opt.get("sequence_id"),
                    row=opt.get("row", 0)
                )
                options_ids.append(option_id)
                
            self.items[item_id].options_ids = options_ids
            
        return item_id
    
    def start_sequence_builder(self) -> 'SequenceBuilder':
        """
        Начинает построение новой последовательности с использованием паттерна Строитель.
        
        Returns:
            SequenceBuilder: Объект строителя последовательности
        """
        return SequenceBuilder(self)
    
    def from_json(self, json_data: Dict[str, Any]) -> 'DialogGenerator':
        """
        Создает диалог из JSON-данных, совместимых с форматом service_dialog.json.
        
        Args:
            json_data: Словарь с данными диалога
            
        Returns:
            DialogGenerator: Этот же объект для цепочки вызовов
        """
        self.dialog_id = json_data.get("id", 1)
        self.trace = json_data.get("trace", True)
        
        # Сначала создаем все последовательности
        for seq_data in json_data.get("sequences", []):
            seq_id = seq_data.get("id")
            items_ids = seq_data.get("items_ids", [])
            
            if seq_id is not None:
                # Устанавливаем счетчик последовательностей, если ID больше текущего счетчика
                self._sequence_counter = max(self._sequence_counter, seq_id + 1)
                
                # Создаем последовательность с заданным ID
                self.sequences[seq_id] = Sequence(
                    id=seq_id,
                    items_ids=items_ids,
                    dialog_id=self.dialog_id
                )
        
        # Создаем все вопросы/элементы
        for item_data in json_data.get("items", []):
            item_id = item_data.get("id")
            text = item_data.get("text", "")
            options_ids = item_data.get("options_ids", [])
            item_type = item_data.get("type", 0)
            
            if item_id is not None:
                # Устанавливаем счетчик элементов, если ID больше текущего счетчика
                self._item_counter = max(self._item_counter, item_id + 1)
                
                # Создаем элемент с заданным ID
                self.items[item_id] = Question(
                    id=item_id,
                    text=text,
                    options_ids=options_ids,
                    type=item_type,
                    dialog_id=self.dialog_id
                )
        
        # Создаем все опции
        for option_data in json_data.get("options", []):
            option_id = option_data.get("id")
            text = option_data.get("text", "")
            sequence_id = option_data.get("sequence_id")
            row = option_data.get("row", 0)
            
            if option_id is not None:
                # Устанавливаем счетчик опций, если ID больше текущего счетчика
                self._option_counter = max(self._option_counter, option_id + 1)
                
                # Создаем опцию с заданным ID
                self.options[option_id] = Option(
                    id=option_id,
                    text=text,
                    sequence_id=sequence_id,
                    row=row
                )
        
        return self
    
    def _get_next_sequence_id(self) -> int:
        """Возвращает следующий доступный ID для последовательности"""
        seq_id = self._sequence_counter
        self._sequence_counter += 1
        return seq_id
    
    def _get_next_item_id(self) -> int:
        """Возвращает следующий доступный ID для элемента"""
        item_id = self._item_counter
        self._item_counter += 1
        return item_id
    
    def _get_next_option_id(self) -> int:
        """Возвращает следующий доступный ID для опции"""
        option_id = self._option_counter
        self._option_counter += 1
        return option_id


class SequenceBuilder:
    """
    Строитель последовательности диалога, реализующий паттерн Builder.
    Позволяет создавать последовательности диалога с помощью цепочки методов.
    """
    
    def __init__(self, generator: DialogGenerator):
        """
        Инициализация строителя последовательности.
        
        Args:
            generator: Экземпляр генератора диалогов
        """
        self.generator = generator
        self.sequence_id = generator.create_sequence()
        self.current_item_id = None
    
    def add_select_item(self, text: str) -> 'SequenceBuilder':
        """
        Добавляет элемент с выбором из нескольких вариантов.
        
        Args:
            text: Текст вопроса/заголовка
            
        Returns:
            SequenceBuilder: Этот же объект для цепочки вызовов
        """
        item_id = self.generator.create_item(text=text, item_type=0)
        self.generator.add_item_to_sequence(self.sequence_id, item_id)
        self.current_item_id = item_id
        return self
    
    def add_text_input_item(self, text: str) -> 'SequenceBuilder':
        """
        Добавляет элемент для ввода текста пользователем.
        
        Args:
            text: Текст с инструкцией для пользователя
            
        Returns:
            SequenceBuilder: Этот же объект для цепочки вызовов
        """
        item_id = self.generator.create_item(text=text, item_type=1)
        self.generator.add_item_to_sequence(self.sequence_id, item_id)
        self.current_item_id = item_id
        return self
    
    def add_option(self, text: str, target_sequence_id: Optional[int] = None, row: int = 0) -> 'SequenceBuilder':
        """
        Добавляет опцию к текущему элементу.
        
        Args:
            text: Текст опции
            target_sequence_id: ID последовательности, на которую переходит диалог при выборе этой опции
            row: Номер строки для размещения опции в клавиатуре
            
        Returns:
            SequenceBuilder: Этот же объект для цепочки вызовов
            
        Raises:
            ValueError: Если не выбран текущий элемент
        """
        if self.current_item_id is None:
            raise ValueError("No active item selected. Add an item first.")
            
        option_id = self.generator.create_option(text, target_sequence_id, row)
        self.generator.add_option_to_item(self.current_item_id, option_id)
        return self
    
    def set_next_sequence(self, next_sequence_id: int) -> 'SequenceBuilder':
        """
        Устанавливает следующую последовательность для автоматического перехода.
        
        Args:
            next_sequence_id: ID следующей последовательности
            
        Returns:
            SequenceBuilder: Этот же объект для цепочки вызовов
        """
        self.generator.set_next_sequence(self.sequence_id, next_sequence_id)
        return self
    
    def build(self) -> int:
        """
        Завершает построение последовательности и возвращает её ID.
        
        Returns:
            int: ID построенной последовательности
        """
        return self.sequence_id
    