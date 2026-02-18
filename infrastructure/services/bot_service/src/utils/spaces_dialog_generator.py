from typing import Dict, List, Optional, TYPE_CHECKING
from shared.entities.dialog import Dialog
from utils.dialog_generator import DialogGenerator
from shared.constants import Dialogs
import logging
import json
import os
from shared.models import Object, Space

if TYPE_CHECKING:
    # from services.spaces_service import SpacesService  # Removed: using DatabaseManager instead
    pass

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SpacesDialogGenerator:
    """
    Генератор диалога для отображения информации о доступных объектах 
    недвижимости и помещениях. Использует DialogGenerator для построения 
    структуры диалога на основе данных из базы данных.
    """
    
    def __init__(self, rental_spaces_service: "RentalSpaceService", rental_object_service: "RentalObjectService"):
        """
        Инициализация генератора диалога для работы с помещениями.
        
        Args:
            spaces_service: Сервис для работы с объектами недвижимости и помещениями
        """
        self.rental_spaces_service = rental_spaces_service
        self.rental_object_service = rental_object_service
        self.dialog_id = 30  # ID для диалога о помещениях
        
        # Инициализируем DialogGenerator
        self.generator = DialogGenerator(dialog_id=self.dialog_id, trace=True)
        logger.info(f"Инициализирован SpacesDialogGenerator с dialog_id={self.dialog_id}")
        
    async def generate_dialog(self) -> Optional[Dialog]:
        """
        Генерирует полный диалог для отображения объектов недвижимости и помещений.
        
        Args:
            
        Returns:
            Dialog: Сгенерированный диалог или None в случае ошибки
        """
        try:
            
            # Получаем только доступные объекты (status=ACTIVE)
            objects = await self.rental_object_service.get_available_objects()
            if not objects:
                logger.warning("Не найдено объектов недвижимости")
                return None
                
            logger.info(f"Получено {len(objects)} объектов недвижимости")
            
            # Создаем корневую последовательность
            root_seq_id = self.generator.create_sequence()
            logger.debug(f"Создана корневая последовательность с ID={root_seq_id}")
            
            # Текст для корневого сообщения
            root_text = "В этом разделе вы можете ознакомиться с вакантными помещениями в объектах недвижимости ООО \"Фард Сити\""
            
            # Создаем корневой элемент выбора для главного меню
            root_item_id = self.generator.create_item(
                text=root_text,
                item_type=0  # Тип 0 - выбор из опций
            )
            logger.debug(f"Создан корневой элемент с ID={root_item_id}")
            
            # Добавляем корневой элемент в корневую последовательность
            self.generator.add_item_to_sequence(root_seq_id, root_item_id)
            
            # Создаем опции (кнопки) для выбора объектов недвижимости
            for i, obj in enumerate(objects):
                logger.debug(f"Обработка объекта {i+1}/{len(objects)}: {obj.name}")
                
                # Создаем последовательность для объекта
                obj_seq_id = self.generator.create_sequence()
                
                # Создаем опцию для перехода к объекту
                obj_option_id = self.generator.create_option(
                    text=obj.name,
                    target_sequence_id=obj_seq_id,
                    row=i // 2  # Размещаем кнопки по 2 в ряд
                )
                
                # Добавляем опцию к корневому элементу
                self.generator.add_option_to_item(root_item_id, obj_option_id)
                
                # Создаем последовательность для этого объекта
                await self._create_object_sequence(obj, obj_seq_id)
        
            
            # Создаем финальный объект Dialog
            dialog = self.generator.create_dialog()
            return dialog
            
        except Exception as e:
            logger.error(f"Ошибка при генерации диалога: {e}", exc_info=True)
            return None

    
    async def _create_object_sequence(self, obj: "Object", sequence_id: int) -> None:
        """
        Создает последовательность для отображения информации об объекте и его помещениях.
        
        Args:
            obj: Объект недвижимости
            sequence_id: ID последовательности
        """
        logger.debug(f"Создание последовательности для объекта {obj.name} (ID={sequence_id})")
        
        # Получаем только свободные помещения для этого объекта
        spaces = await self.rental_spaces_service.get_free_spaces_by_object_id(obj.id)

        # Базовое описание объекта
        object_description = f"{obj.name} - {obj.address}\n\n{obj.description}"
        
        if not spaces:
            logger.debug(f"Нет доступных помещений для объекта {obj.name}")
            
            # Если нет помещений, создаем сообщение "Нет доступных помещений"
            no_spaces_text = f"{object_description}\n\nНа данный момент нет свободных помещений."
            
            # Создаем элемент с сообщением
            item_id = self.generator.create_item(
                text=no_spaces_text,
                item_type=0,
                images=obj.photos
            )
            
            # Добавляем элемент в последовательность
            self.generator.add_item_to_sequence(sequence_id, item_id)
            
            return
        
        # Дополняем описание информацией о количестве помещений
        object_description += f"\n\nНа данный момент свободны {len(spaces)} помещений:"
        
        # Группируем помещения по 6 штук (для постраничного отображения)
        space_groups = []
        current_group = []
        
        for space in spaces:
            current_group.append(space)
            if len(current_group) == 6:
                space_groups.append(current_group)
                current_group = []
        
        if current_group:  # Добавляем оставшиеся помещения
            space_groups.append(current_group)
            
        logger.debug(f"Создано {len(space_groups)} страниц для объекта {obj.name}")
        
        # Создаем словарь для хранения ID последовательностей страниц
        page_sequences = {}
        
        # Сначала создаем все последовательности для страниц, чтобы потом можно было правильно ссылаться
        for page in range(len(space_groups)):
            if page == 0:
                page_sequences[page] = sequence_id  # Используем последовательность объекта для первой страницы
            else:
                page_sequences[page] = self.generator.create_sequence()
                
        # Теперь заполняем последовательности содержимым
        for page, group in enumerate(space_groups):
            logger.debug(f"Создание страницы {page+1}/{len(space_groups)} для объекта {obj.name}")
            
            page_sequence_id = page_sequences[page]
            
            # Создаем элемент для текущей страницы
            page_item_id = self.generator.create_item(
                text=object_description,
                item_type=0,
                images=obj.photos
            )
            
            # Добавляем элемент в последовательность страницы
            self.generator.add_item_to_sequence(page_sequence_id, page_item_id)
            
            # Добавляем опции для каждого помещения на странице
            for i, space in enumerate(group):
                # Создаем последовательность для помещения
                space_seq_id = self.generator.create_sequence()
                
                # Создаем опцию для перехода к помещению
                button_text = f"{space.floor} этаж - {space.size} м²"
                space_option_id = self.generator.create_option(
                    text=button_text,
                    target_sequence_id=space_seq_id,
                    row=i // 2  # По 2 кнопки в ряд
                )
                
                # Добавляем опцию к элементу страницы
                self.generator.add_option_to_item(page_item_id, space_option_id)
                
                # Создаем последовательность для этого помещения
                # Используем ID последовательности текущей страницы как родительский
                self._create_space_sequence(space, space_seq_id, page_sequence_id)
            
            # Кнопка "Далее" (к следующей странице)
            if page < len(space_groups) - 1:
                next_page = page + 1
                next_sequence_id = page_sequences[next_page]
                
                next_option_id = self.generator.create_option(
                    text="Далее",
                    target_sequence_id=next_sequence_id,  # Переход к следующей странице
                    row=3
                )
                self.generator.add_option_to_item(page_item_id, next_option_id)
    
    def _create_space_sequence(self, space: "Space", sequence_id: int, parent_sequence_id: int) -> None:
        """
        Создает последовательность для отображения информации о помещении.
        
        Args:
            space: Помещение
            sequence_id: ID последовательности
            parent_sequence_id: ID родительской последовательности (объекта)
        """
        logger.debug(f"Создание последовательности для помещения {space.floor} этаж, {space.size} м² (ID={sequence_id})")
        
        # Создаем текст описания помещения
        space_description = f"Помещение {space.floor} этаж, {space.size} м²\n\n{space.description}"

        back_option_id = self.generator.create_custom_button(
            text="обратно в меню",
            callback_data=Dialogs.MENU,
            row=4
        )
        
        # Добавляем кнопку "обратно в меню" в последовательность
        
        # Создаем элемент с описанием помещения
        space_item_id = self.generator.create_item(
            text=space_description,
            item_type=0,
            images=space.photos
        )

        # Добавляем кнопку "обратно в меню" в последовательность
        self.generator.add_option_to_item(space_item_id, back_option_id)
        
        # Добавляем элемент в последовательность
        self.generator.add_item_to_sequence(sequence_id, space_item_id)