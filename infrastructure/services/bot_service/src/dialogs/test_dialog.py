import logging
from typing import TYPE_CHECKING
from shared.constants import Dialogs, Actions
from telegram.constants import ParseMode

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


logger = logging.getLogger(__name__)


async def start_test_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> int:
    """
    Обработчик диалога тестирования для отображения информации о чате и участниках.
    
    Выводит:
    - ID чата
    - Тип чата
    - Название чата
    - Количество участников
    - Список последних 20 участников с их ID и никами
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст обработчика
        bot: Экземпляр бота
        
    Returns:
        int: Код завершения диалога
    """
    try:
        chat = update.effective_chat
        chat_id = chat.id
        chat_type = chat.type
        chat_title = getattr(chat, 'title', 'N/A')
        
        # Формируем основную информацию о чате
        info_text = f"<b>📊 Информация о чате:</b>\n\n"
        info_text += f"🆔 <b>ID чата:</b> <code>{chat_id}</code>\n"
        info_text += f"📱 <b>Тип чата:</b> {chat_type}\n"
        info_text += f"📝 <b>Название:</b> {chat_title}\n"
        
        # Если это групповой чат или канал, получаем информацию об участниках
        if chat_type in ['group', 'supergroup', 'channel']:
            try:
                # Получаем количество участников
                chat_members_count = await context.bot.get_chat_member_count(chat_id)
                info_text += f"👥 <b>Количество участников:</b> {chat_members_count}\n\n"
                
                # Получаем администраторов чата (они обычно наиболее активны)
                administrators = await context.bot.get_chat_administrators(chat_id)
                
                info_text += f"<b>👑 Администраторы чата ({len(administrators)}):</b>\n"
                
                admin_count = 0
                for admin in administrators:
                    if admin_count >= 20:  # Ограничиваем до 20
                        break
                        
                    user = admin.user
                    user_id = user.id
                    username = f"@{user.username}" if user.username else "Нет ника"
                    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                    status = admin.status
                    
                    # Эмодзи для разных статусов
                    status_emoji = {
                        'creator': '👑',
                        'administrator': '⭐',
                        'member': '👤',
                        'restricted': '🚫',
                        'left': '❌',
                        'kicked': '⛔'
                    }.get(status, '👤')
                    
                    info_text += f"{status_emoji} <code>{user_id}</code> | {username}"
                    if full_name:
                        info_text += f" | {full_name}"
                    info_text += f" | {status}\n"
                    admin_count += 1
                    
            except Exception as e:
                info_text += f"❌ <b>Ошибка получения участников:</b> {str(e)}\n"
                logger.exception("Error getting chat members for chat_id=%s: %s", chat_id, e)
                
        elif chat_type == 'private':
            # Для приватного чата показываем информацию о пользователе
            user = update.effective_user
            if user:
                info_text += f"\n<b>👤 Информация о пользователе:</b>\n"
                info_text += f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
                info_text += f"👤 <b>Ник:</b> @{user.username or 'Нет ника'}\n"
                info_text += f"📝 <b>Имя:</b> {user.first_name or 'N/A'}\n"
                info_text += f"📝 <b>Фамилия:</b> {user.last_name or 'N/A'}\n"
                info_text += f"🌐 <b>Язык:</b> {user.language_code or 'N/A'}\n"
                info_text += f"🤖 <b>Бот:</b> {'Да' if user.is_bot else 'Нет'}\n"
        
        # Добавляем дополнительную техническую информацию
        info_text += f"\n<b>🔧 Техническая информация:</b>\n"
        info_text += f"📅 <b>Дата сообщения:</b> {update.message.date}\n"
        info_text += f"📨 <b>ID сообщения:</b> {update.message.message_id}\n"
        
        # Отправляем информацию
        await context.bot.send_message(
            chat_id=chat_id,
            text=info_text,
            parse_mode=ParseMode.HTML,
            reply_to_message_id=update.message.message_id
        )
        
        return Actions.END
        
    except Exception as e:
        error_text = f"❌ <b>Ошибка выполнения команды /test:</b>\n<code>{str(e)}</code>"
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=error_text,
            parse_mode=ParseMode.HTML,
            reply_to_message_id=update.message.message_id
        )
        logger.exception("Error in start_test_dialog for chat_id=%s: %s", getattr(update.effective_chat, "id", None), e)
        return Actions.END
