import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TYPE_CHECKING
from telegram import InlineKeyboardMarkup, Message
from telegram.constants import ParseMode
from telegram.error import BadRequest, NetworkError, RetryAfter, TimedOut
from shared.constants import Variables
from .base_manager import BaseManager

try:
    import httpx
except ImportError:  # pragma: no cover - optional runtime dependency
    httpx = None

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MessageOperationResult:
    success: bool
    reason: str
    error: str | None = None


class MessageManager(BaseManager):
    """Менеджер для управления отправкой сообщений"""

    MAX_RETRY_ATTEMPTS = 3
    BASE_RETRY_DELAY_SECONDS = 1.0
    
    def __init__(self, bot: "Bot"):
        super().__init__(bot)
    
    async def initialize(self) -> None:
        """Инициализация менеджера сообщений"""
        logger.info("MessageManager initialized")

    def _append_to_buffer(
        self,
        context: "ContextTypes.DEFAULT_TYPE",
        *,
        chat_id: int,
        message_id: int,
    ) -> None:
        buffer_messages = self.bot.managers.storage.get(context, Variables.BUFFER_MESSAGES) or []
        buffer_messages.append({"chat_id": chat_id, "message_id": message_id})
        self.bot.managers.storage.set(context, Variables.BUFFER_MESSAGES, buffer_messages)

    def _build_log_context(self, **kwargs: Any) -> str:
        parts = [f"{key}={value}" for key, value in kwargs.items() if value is not None]
        return ", ".join(parts) if parts else "no-context"

    def _is_retryable_exception(self, exc: Exception) -> bool:
        if self._is_non_retryable_bad_request(exc):
            return False
        if isinstance(exc, (TimedOut, NetworkError, RetryAfter)):
            return True
        if httpx is not None and isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
            return True

        error_text = str(exc).lower()
        retryable_markers = (
            "timed out",
            "timeout",
            "connection reset",
            "temporarily unavailable",
            "temporary failure",
            "server disconnected",
            "connection aborted",
            "network is unreachable",
        )
        return any(marker in error_text for marker in retryable_markers)

    def _is_non_retryable_bad_request(self, exc: Exception) -> bool:
        if not isinstance(exc, BadRequest):
            return False
        error_text = str(exc).lower()
        non_retryable_markers = (
            "wrong type of the web page content",
            "failed to get http url content",
            "message can't be deleted for everyone",
            "query is too old",
            "query id is invalid",
        )
        return any(marker in error_text for marker in non_retryable_markers)

    async def _send_adaptive_photo(
        self,
        *,
        context: "ContextTypes.DEFAULT_TYPE",
        chat_id: int,
        image_ref: dict[str, str | None],
        caption: str,
        reply_markup: InlineKeyboardMarkup | None,
        parse_mode: ParseMode,
    ) -> Message:
        telegram_file_id = str(image_ref.get("telegram_file_id") or "").strip()
        if telegram_file_id:
            try:
                return await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=telegram_file_id,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
            except Exception:
                image_ref["telegram_file_id"] = None
                await self.bot.services.media.persist_storage_file_telegram_file_id(
                    storage_path=image_ref.get("storage_path"),
                    telegram_file_id=None,
                )
        filename, file_content = await self.bot.services.media.download_photo_bytes(str(image_ref.get("url") or ""))
        message = await context.bot.send_photo(
            chat_id=chat_id,
            photo=self.bot.services.media.as_input_file(filename, file_content),
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        photos = getattr(message, "photo", None) or []
        uploaded_file_id = getattr(photos[-1], "file_id", None) if photos else None
        if uploaded_file_id:
            image_ref["telegram_file_id"] = str(uploaded_file_id)
            await self.bot.services.media.persist_storage_file_telegram_file_id(
                storage_path=image_ref.get("storage_path"),
                telegram_file_id=str(uploaded_file_id),
            )
        return message

    def _is_message_not_found(self, exc: Exception) -> bool:
        error_text = str(exc).lower()
        return (
            "message to delete not found" in error_text
            or "message to edit not found" in error_text
            or "message to be replied not found" in error_text
        )

    def _is_message_not_modified(self, exc: Exception) -> bool:
        return "message is not modified" in str(exc).lower()

    def _is_message_cant_be_edited(self, exc: Exception) -> bool:
        return "message can't be edited" in str(exc).lower()

    def _retry_delay(self, exc: Exception, attempt: int) -> float:
        if isinstance(exc, RetryAfter):
            retry_after = getattr(exc, "retry_after", 0) or 0
            return max(float(retry_after), self.BASE_RETRY_DELAY_SECONDS)
        return self.BASE_RETRY_DELAY_SECONDS * attempt

    async def _execute_with_retry(
        self,
        *,
        operation_name: str,
        operation: Callable[[], Awaitable[Any]],
        error_code: int,
        log_context: str,
        max_attempts: int | None = None,
    ) -> tuple[bool, Any, Exception | None]:
        attempts = max_attempts or self.MAX_RETRY_ATTEMPTS
        last_exc: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                return True, await operation(), None
            except Exception as exc:  # noqa: BLE001 - centralized telegram error handling
                last_exc = exc
                retryable = self._is_retryable_exception(exc) and attempt < attempts
                await self.bot.handle_error(
                    error_code,
                    (
                        f"{operation_name} failed "
                        f"(attempt {attempt}/{attempts}, retryable={retryable}) "
                        f"[{log_context}] {type(exc).__name__}: {exc}"
                    ),
                )
                if retryable:
                    await asyncio.sleep(self._retry_delay(exc, attempt))
                    continue
                break

        return False, None, last_exc
    
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
        
        try:
            # Ищем сообщение с клавиатурой (обычно последнее), которое можно отредактировать
            editable_message = None
            
            if update.callback_query and dynamic and not images and not refresh:
                # Пробуем отредактировать текущее сообщение callback
                log_context = self._build_log_context(
                    chat_id=chat_id,
                    callback_message_id=getattr(update.callback_query.message, "message_id", None),
                )
                success, edited_result, exc = await self._execute_with_retry(
                    operation_name="edit callback message",
                    operation=lambda: update.callback_query.edit_message_text(
                        text,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode,
                    ),
                    error_code=1001,
                    log_context=log_context,
                )
                if success:
                    if isinstance(edited_result, Message):
                        editable_message = edited_result
                        new_messages.append(
                            {"chat_id": edited_result.chat_id, "message_id": edited_result.message_id}
                        )
                    else:
                        editable_message = update.callback_query.message
                        if editable_message:
                            new_messages.append(
                                {"chat_id": editable_message.chat.id, "message_id": editable_message.message_id}
                            )
                else:
                    if exc and self._is_message_not_modified(exc):
                        editable_message = update.callback_query.message
                        if editable_message:
                            new_messages.append(
                                {"chat_id": editable_message.chat.id, "message_id": editable_message.message_id}
                            )
                    else:
                        editable_message = None
            
            # Удаляем все старые сообщения, кроме того, которое мы отредактировали
            await self._cleanup_old_messages(context, chat_id, 
                                            skip_message_id=editable_message.message_id if editable_message else None)
            
            # Если не смогли отредактировать или у нас есть изображения, отправляем новые
            if not editable_message:
                # Если есть изображения, отправляем их (нормализуем URL для Telegram)
                if images and len(images) > 0:
                    images = [img for img in images if img]
                    if not images:
                        images = None
                if images and len(images) > 0:
                    # Для одного изображения используем send_photo
                    if len(images) == 1:
                        log_context = self._build_log_context(chat_id=chat_id, image_count=1)
                        image_ref = await self.bot.services.media.prepare_image_ref(images[0])
                        success, message, _ = await self._execute_with_retry(
                            operation_name="send photo",
                            operation=lambda: self._send_adaptive_photo(
                                context=context,
                                chat_id=chat_id,
                                image_ref=image_ref,
                                caption=text[:1024],  # Telegram ограничивает подпись до 1024 символов
                                reply_markup=reply_markup,
                                parse_mode=parse_mode,
                            ),
                            error_code=1001,
                            log_context=log_context,
                        )
                        if message:
                            new_messages.append({"chat_id": message.chat_id, "message_id": message.message_id})
                    # Для нескольких изображений используем media group
                    else:
                        from telegram import InputMediaPhoto
                        image_refs = [await self.bot.services.media.prepare_image_ref(img) for img in images]
                        media = []
                        for index, image_ref in enumerate(image_refs):
                            telegram_file_id = str(image_ref.get("telegram_file_id") or "").strip()
                            is_last = index == len(image_refs) - 1
                            caption_value = text[:1024] if is_last else None
                            parse_mode_value = parse_mode if is_last else None
                            if telegram_file_id:
                                media_item = InputMediaPhoto(
                                    media=telegram_file_id,
                                    caption=caption_value,
                                    parse_mode=parse_mode_value,
                                )
                            else:
                                filename, file_content = await self.bot.services.media.download_photo_bytes(str(image_ref.get("url") or ""))
                                media_item = InputMediaPhoto(
                                    media=self.bot.services.media.as_input_file(filename, file_content),
                                    caption=caption_value,
                                    parse_mode=parse_mode_value,
                                )
                            media.append(media_item)
                        
                        # Отправляем группу медиа
                        log_context = self._build_log_context(chat_id=chat_id, image_count=len(images))
                        success, media_messages, _ = await self._execute_with_retry(
                            operation_name="send media group",
                            operation=lambda: context.bot.send_media_group(
                                chat_id=chat_id,
                                media=media,
                            ),
                            error_code=1001,
                            log_context=log_context,
                        )
                        
                        # Сохраняем ID всех сообщений с медиа
                        for idx, msg in enumerate(media_messages or []):
                            new_messages.append({"chat_id": msg.chat_id, "message_id": msg.message_id})
                            photos = getattr(msg, "photo", None) or []
                            uploaded_file_id = getattr(photos[-1], "file_id", None) if photos else None
                            if uploaded_file_id and idx < len(image_refs):
                                await self.bot.services.media.persist_storage_file_telegram_file_id(
                                    storage_path=image_refs[idx].get("storage_path"),
                                    telegram_file_id=str(uploaded_file_id),
                                )
                        
                        # Если нужна клавиатура, отправляем отдельным сообщением
                        if reply_markup:
                            success, keyboard_message, _ = await self._execute_with_retry(
                                operation_name="send follow-up keyboard message",
                                operation=lambda: context.bot.send_message(
                                    chat_id=chat_id,
                                    text=self.bot.get_text("choose_action"),
                                    reply_markup=reply_markup,
                                    parse_mode=parse_mode,
                                ),
                                error_code=1001,
                                log_context=log_context,
                            )
                            if keyboard_message:
                                new_messages.append(
                                    {"chat_id": keyboard_message.chat_id, "message_id": keyboard_message.message_id}
                                )
                else:
                    # Отправляем новое текстовое сообщение
                    log_context = self._build_log_context(chat_id=chat_id, dynamic=dynamic, refresh=refresh)
                    success, message, _ = await self._execute_with_retry(
                        operation_name="send message",
                        operation=lambda: context.bot.send_message(
                            chat_id=chat_id,
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode=parse_mode,
                        ),
                        error_code=1001,
                        log_context=log_context,
                    )
                    if message:
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
        parse_mode: ParseMode = ParseMode.HTML,
        fallback_to_plain_message: bool = True,
    ) -> Message | None:
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
                log_context = self._build_log_context(
                    chat_id=update.message.chat.id,
                    reply_to_message_id=update.message.message_id,
                )
                success, message, exc = await self._execute_with_retry(
                    operation_name="reply to message",
                    operation=lambda: context.bot.send_message(
                        chat_id=update.message.chat.id,
                        text=text,
                        reply_to_message_id=update.message.message_id,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode,
                    ),
                    error_code=1004,
                    log_context=log_context,
                )
                if success and message:
                    self._append_to_buffer(
                        context,
                        chat_id=message.chat_id,
                        message_id=message.message_id,
                    )
                    return message

                if fallback_to_plain_message:
                    await self.bot.handle_error(
                        1004,
                        (
                            "Reply failed, falling back to plain message "
                            f"[{log_context}] last_error={type(exc).__name__ if exc else 'unknown'}: {exc}"
                        ),
                    )
                    fallback_success, fallback_message, _ = await self._execute_with_retry(
                        operation_name="send fallback message",
                        operation=lambda: context.bot.send_message(
                            chat_id=update.message.chat.id,
                            text=text,
                            reply_markup=reply_markup,
                            parse_mode=parse_mode,
                        ),
                        error_code=1004,
                        log_context=self._build_log_context(
                            chat_id=update.message.chat.id,
                            fallback_from_reply_to=update.message.message_id,
                        ),
                    )
                    if fallback_success and fallback_message:
                        self._append_to_buffer(
                            context,
                            chat_id=fallback_message.chat_id,
                            message_id=fallback_message.message_id,
                        )
                        return fallback_message

                return None
            else:
                logger.warning("Unable to reply: no message to reply to")
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
            success, message, _ = await self._execute_with_retry(
                operation_name="send message to chat",
                operation=lambda: context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                ),
                error_code=1005,
                log_context=self._build_log_context(chat_id=chat_id),
            )
            if not success or not message:
                return None
            
            self._append_to_buffer(
                context,
                chat_id=message.chat_id,
                message_id=message.message_id,
            )
            
            return message
        except Exception as e:
            await self.bot.handle_error(1005, f"Error sending message to chat {chat_id}: {str(e)}")
            return None
    
    async def edit_message_detailed(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        payload: list[str] | None = None,
        parse_mode: ParseMode = ParseMode.HTML
    ) -> MessageOperationResult:
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
            Детализированный результат операции редактирования.
        """
        text = self.bot.get_text(text, payload, 'RU')
        log_context = self._build_log_context(chat_id=chat_id, message_id=message_id)

        for attempt in range(1, self.MAX_RETRY_ATTEMPTS + 1):
            try:
                await self.bot.application.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
                return MessageOperationResult(success=True, reason="edited")
            except Exception as exc:  # noqa: BLE001 - centralized telegram error handling
                if self._is_message_not_modified(exc):
                    return MessageOperationResult(success=True, reason="not_modified")
                if self._is_message_not_found(exc) or self._is_message_cant_be_edited(exc):
                    return MessageOperationResult(
                        success=False,
                        reason="not_found" if self._is_message_not_found(exc) else "cant_edit",
                        error=str(exc),
                    )

                retryable = self._is_retryable_exception(exc) and attempt < self.MAX_RETRY_ATTEMPTS
                await self.bot.handle_error(
                    1006,
                    (
                        f"Error editing message "
                        f"(attempt {attempt}/{self.MAX_RETRY_ATTEMPTS}, retryable={retryable}) "
                        f"[{log_context}] {type(exc).__name__}: {exc}"
                    ),
                )
                if retryable:
                    await asyncio.sleep(self._retry_delay(exc, attempt))
                    continue
                return MessageOperationResult(
                    success=False,
                    reason="retry_exhausted" if self._is_retryable_exception(exc) else "error",
                    error=str(exc),
                )

        return MessageOperationResult(success=False, reason="error", error="Unknown edit failure")

    async def edit_message(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        payload: list[str] | None = None,
        parse_mode: ParseMode = ParseMode.HTML
    ) -> bool:
        result = await self.edit_message_detailed(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
            payload=payload,
            parse_mode=parse_mode,
        )
        return result.success
    
    async def delete_message_detailed(
        self,
        chat_id: int | str,
        message_id: int
    ) -> MessageOperationResult:
        """
        Удаляет сообщение
        
        Args:
            chat_id: ID чата
            message_id: ID сообщения для удаления
            
        Returns:
            Детализированный результат операции удаления.
        """
        log_context = self._build_log_context(chat_id=chat_id, message_id=message_id)

        for attempt in range(1, self.MAX_RETRY_ATTEMPTS + 1):
            try:
                await self.bot.application.bot.delete_message(
                    chat_id=chat_id,
                    message_id=message_id,
                )
                return MessageOperationResult(success=True, reason="deleted")
            except Exception as exc:  # noqa: BLE001 - centralized telegram error handling
                if self._is_message_not_found(exc):
                    return MessageOperationResult(success=True, reason="not_found")
                retryable = self._is_retryable_exception(exc) and attempt < self.MAX_RETRY_ATTEMPTS
                await self.bot.handle_error(
                    1007,
                    (
                        f"Error deleting message "
                        f"(attempt {attempt}/{self.MAX_RETRY_ATTEMPTS}, retryable={retryable}) "
                        f"[{log_context}] {type(exc).__name__}: {exc}"
                    ),
                )
                if retryable:
                    await asyncio.sleep(self._retry_delay(exc, attempt))
                    continue
                return MessageOperationResult(
                    success=False,
                    reason="retry_exhausted" if self._is_retryable_exception(exc) else "error",
                    error=str(exc),
                )

        return MessageOperationResult(success=False, reason="error", error="Unknown delete failure")

    async def delete_message(
        self,
        chat_id: int | str,
        message_id: int
    ) -> bool:
        result = await self.delete_message_detailed(chat_id=chat_id, message_id=message_id)
        return result.success
    
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
                        await self.delete_message(
                            chat_id=msg_chat_id,
                            message_id=msg_id,
                        )
                except Exception as e:
                    # Игнорируем ошибки при удалении, так как сообщение могло быть уже удалено
                    pass
                    
            # Очищаем буфер сообщений
            if skip_message_id is None:
                self.bot.managers.storage.set(context, Variables.BUFFER_MESSAGES, [])
        except Exception as e:
            await self.bot.handle_error(1011, f"Error in cleanup_old_messages: {str(e)}") 
