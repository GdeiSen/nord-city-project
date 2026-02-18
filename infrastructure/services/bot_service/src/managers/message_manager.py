from typing import List, Optional, TYPE_CHECKING
from telegram import InlineKeyboardMarkup, Message
from telegram.constants import ParseMode
from shared.constants import Variables
from shared.utils.media_urls import to_public_media_url
from .base_manager import BaseManager

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


class MessageManager(BaseManager):
    """Менеджер для управления отправкой сообщений"""
    
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
    
    async def initialize(self) -> None:
        """Инициализация менеджера сообщений"""
        print("MessageManager initialized")
    
    async def send_message(
        self,
        update: "Update",
        context: "ContextTypes.DEFAULT_TYPE",
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        payload: list[str] | None = None,
        parse_mode: ParseMode = ParseMode.HTML,
        dynamic: bool = True,
        refresh: bool = False,
        images: list[str] | None = None
    ) -> None:
        """
        Отправка сообщения с автоматическим управлением буфером
        
        Args:
            update: Обновление Telegram
            context: Контекст Telegram
            text: Текст сообщения
            reply_markup: Клавиатура
            payload: Данные для подстановки в текст
            parse_mode: Режим парсинга
            dynamic: Динамическое управление сообщениями
            refresh: Принудительное обновление
            images: Список изображений
        """
        text = self.bot.get_text(text, payload, 'RU')
        
        # Получаем chat_id из обновления
        chat_id = None
        if update.message:
            chat_id = update.message.chat.id
        elif update.callback_query and update.callback_query.message:
            chat_id = update.callback_query.message.chat.id
            
        if not chat_id:
            return
            
        # Массив для хранения новых сообщений
        new_messages = []
        
        # Получаем текущие сообщения в буфере
        current_messages = self.bot.managers.storage.get(context, Variables.BUFFER_MESSAGES) or []
        
        try:
            # Ищем сообщение с клавиатурой (обычно последнее), которое можно отредактировать
            editable_message = None
            
            if update.callback_query and dynamic and not images and not refresh:
                # Пробуем отредактировать текущее сообщение callback
                try:
                    message = await update.callback_query.edit_message_text(
                        text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                    new_messages.append({"chat_id": message.chat_id, "message_id": message.message_id})
                    editable_message = message
                except Exception as e:
                    # Если не удалось отредактировать, будем отправлять заново
                    print(f"Could not edit message: {str(e)}")
                    editable_message = None
            
            # Удаляем все старые сообщения, кроме того, которое мы отредактировали
            await self._cleanup_old_messages(context, chat_id, 
                                            skip_message_id=editable_message.message_id if editable_message else None)
            
            # Если не смогли отредактировать или у нас есть изображения, отправляем новые
            if not editable_message:
                # Если есть изображения, отправляем их (нормализуем URL для Telegram)
                if images and len(images) > 0:
                    images = [to_public_media_url(img) or img for img in images]
                    images = [img for img in images if img and (img.startswith("http://") or img.startswith("https://"))]
                    if not images:
                        images = None
                if images and len(images) > 0:
                    # Для одного изображения используем send_photo
                    if len(images) == 1:
                        message = await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=images[0],
                            caption=text[:1024],  # Telegram ограничивает подпись до 1024 символов
                            reply_markup=reply_markup,
                            parse_mode=parse_mode
                        )
                        new_messages.append({"chat_id": message.chat_id, "message_id": message.message_id})
                    # Для нескольких изображений используем media group
                    else:
                        from telegram import InputMediaPhoto
                        media = [InputMediaPhoto(media=img) for img in images[:-1]]
                        # Последнее изображение с подписью
                        media.append(InputMediaPhoto(media=images[-1], caption=text[:1024], parse_mode=parse_mode))
                        
                        # Отправляем группу медиа
                        media_messages = await context.bot.send_media_group(
                            chat_id=chat_id,
                            media=media
                        )
                        
                        # Сохраняем ID всех сообщений с медиа
                        for msg in media_messages:
                            new_messages.append({"chat_id": msg.chat_id, "message_id": msg.message_id})
                        
                        # Если нужна клавиатура, отправляем отдельным сообщением
                        if reply_markup:
                            keyboard_message = await context.bot.send_message(
                                chat_id=chat_id,
                                text="Выберите действие:",
                                reply_markup=reply_markup,
                                parse_mode=parse_mode
                            )
                            new_messages.append({"chat_id": keyboard_message.chat_id, "message_id": keyboard_message.message_id})
                else:
                    # Отправляем новое текстовое сообщение
                    message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                    new_messages.append({"chat_id": message.chat_id, "message_id": message.message_id})
            
            # Сохраняем новые сообщения в буфер
            if dynamic:
                self.bot.managers.storage.set(context, Variables.BUFFER_MESSAGES, new_messages)
                
        except Exception as e:
            await self.bot.handle_error(1001, f"Error in send_message: {str(e)}")
    
    async def reply_message(
        self,
        update: "Update",
        context: "ContextTypes.DEFAULT_TYPE",
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        payload: list[str] | None = None,
        parse_mode: ParseMode = ParseMode.HTML
    ) -> Message:
        """
        Отправляет ответ на конкретное сообщение
        
        Args:
            update: Обновление Telegram
            context: Контекст Telegram
            text: Текст сообщения
            reply_markup: Клавиатура
            payload: Данные для подстановки в текст
            parse_mode: Режим парсинга
            
        Returns:
            Отправленное сообщение
        """
        try:
            text = self.bot.get_text(text, payload, 'RU')
            if update.message:
                message = await context.bot.send_message(
                    chat_id=update.message.chat.id,
                    text=text,
                    reply_to_message_id=update.message.message_id,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                
                # Сохраняем сообщение в буфер
                buffer_messages = self.bot.managers.storage.get(context, Variables.BUFFER_MESSAGES) or []
                buffer_messages.append({"chat_id": message.chat_id, "message_id": message.message_id})
                self.bot.managers.storage.set(context, Variables.BUFFER_MESSAGES, buffer_messages)
                
                return message
            else:
                print("Unable to reply: no message to reply to")
                return None
        except Exception as e:
            await self.bot.handle_error(1004, f"Error replying to message: {str(e)}")
            return None
    
    async def send_to_chat(
        self,
        context: "ContextTypes.DEFAULT_TYPE",
        chat_id: int | str,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        payload: list[str] | None = None,
        parse_mode: ParseMode = ParseMode.HTML
    ) -> Message:
        """
        Отправляет сообщение в конкретный чат по его ID
        
        Args:
            context: Контекст Telegram
            chat_id: ID чата
            text: Текст сообщения
            reply_markup: Клавиатура
            payload: Данные для подстановки в текст
            parse_mode: Режим парсинга
            
        Returns:
            Отправленное сообщение
        """
        try:
            text = self.bot.get_text(text, payload, 'RU')
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            
            # Сохраняем сообщение в буфер
            buffer_messages = self.bot.managers.storage.get(context, Variables.BUFFER_MESSAGES) or []
            buffer_messages.append({"chat_id": message.chat_id, "message_id": message.message_id})
            self.bot.managers.storage.set(context, Variables.BUFFER_MESSAGES, buffer_messages)
            
            return message
        except Exception as e:
            await self.bot.handle_error(1005, f"Error sending message to chat {chat_id}: {str(e)}")
            return None
    
    async def edit_message(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        payload: list[str] | None = None,
        parse_mode: ParseMode = ParseMode.HTML
    ) -> bool:
        """
        Редактирует существующее сообщение
        
        Args:
            chat_id: ID чата
            message_id: ID сообщения для редактирования
            text: Новый текст сообщения
            reply_markup: Клавиатура
            payload: Данные для подстановки в текст
            parse_mode: Режим парсинга
            
        Returns:
            True если редактирование прошло успешно, False в противном случае
        """
        try:
            text = self.bot.get_text(text, payload, 'RU')
            print(f"Attempting to edit message {message_id} in chat {chat_id}")
            print(f"New text length: {len(text)} characters")
            
            await self.bot.application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            print(f"Successfully edited message {message_id}")
            return True
        except Exception as e:
            print(f"Error editing message {message_id} in chat {chat_id}: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            
            # Проверяем специфичные ошибки Telegram
            error_str = str(e).lower()
            if "message is not modified" in error_str:
                print("Message content is identical, treating as success")
                return True
            elif "message to edit not found" in error_str:
                print("Message not found, likely deleted")
                return False
            elif "message can't be edited" in error_str:
                print("Message too old to edit (48h limit)")
                return False
            else:
                print(f"Unknown edit error: {e}")
                return False
    
    async def delete_message(
        self,
        chat_id: int | str,
        message_id: int
    ) -> bool:
        """
        Удаляет сообщение
        
        Args:
            chat_id: ID чата
            message_id: ID сообщения для удаления
            
        Returns:
            True если удаление прошло успешно, False в противном случае
        """
        try:
            await self.bot.application.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id
            )
            return True
        except Exception as e:
            print(f"Error deleting message {message_id} in chat {chat_id}: {str(e)}")
            return False
    
    async def _cleanup_old_messages(self, context: "ContextTypes.DEFAULT_TYPE", chat_id: int, skip_message_id: int = None) -> None:
        """
        Очищает предыдущие сообщения из чата.
        
        Args:
            context: Контекст обработчика
            chat_id: ID чата для очистки
            skip_message_id: ID сообщения, которое не нужно удалять (например, отредактированное)
        """
        try:
            # Получаем сохраненные сообщения
            buffer_messages = self.bot.managers.storage.get(context, Variables.BUFFER_MESSAGES) or []
            
            if not buffer_messages:
                return
                
            # Пытаемся удалить все сообщения, кроме skip_message_id
            for msg_info in buffer_messages:
                try:
                    msg_chat_id = msg_info.get("chat_id")
                    msg_id = msg_info.get("message_id")
                    
                    if (msg_chat_id and msg_id and msg_chat_id == chat_id and 
                        (skip_message_id is None or msg_id != skip_message_id)):
                        await context.bot.delete_message(
                            chat_id=msg_chat_id, 
                            message_id=msg_id
                        )
                except Exception as e:
                    # Игнорируем ошибки при удалении, так как сообщение могло быть уже удалено
                    pass
                    
            # Очищаем буфер сообщений
            if skip_message_id is None:
                self.bot.managers.storage.set(context, Variables.BUFFER_MESSAGES, [])
        except Exception as e:
            await self.bot.handle_error(1011, f"Error in cleanup_old_messages: {str(e)}") 