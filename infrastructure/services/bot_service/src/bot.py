# ./bot.py
import logging
import argparse
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure 'shared' package inside microservices is importable
try:
    MICROSERVICES_DIR = Path(__file__).resolve().parents[3]
except IndexError:
    # Fallback when running inside container where path depth is smaller (/app/src/bot.py)
    MICROSERVICES_DIR = Path(__file__).resolve().parent.parent

if str(MICROSERVICES_DIR) not in sys.path:
    sys.path.append(str(MICROSERVICES_DIR))
from shared.constants import Dialogs, Actions, Variables

# Load environment variables from infrastructure .env (single source of truth)
# Use same root as MICROSERVICES_DIR so we always read infrastructure/.env, not bot_service/.env
ENV_PATH = MICROSERVICES_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH, override=False)
from typing import Callable, Coroutine, Any
from typing import TYPE_CHECKING

# Dialog and callback imports (remain the same)
from dyn_dialogs_callbacks.profile_callback import profile_callback
from dyn_dialogs_callbacks.poll_callback import poll_callback
from dyn_dialogs_callbacks.service_callback import service_callback
from dyn_dialogs_callbacks.feedback_callback import feedback_callback
from dyn_dialogs_callbacks.service_feedback_callback import service_feedback_callback
from dyn_dialogs_callbacks.spaces_callback import spaces_callback
from dialogs import (
    start_app_dialog,
    start_dyn_dialog,
    start_feedback_dialog,
    start_menu_dialog,
    start_profile_dialog,
    start_service_dialog,
    start_poll_dialog,
    start_service_feedback_dialog,
    start_spaces_dialog,
    start_test_dialog
)
from dialogs.stats_dialog import start_stats_dialog

# --- Refactoring Changes: Imports ---
# Import Manager and Service registries
from managers import (
    ManagerRegistry, StorageManager, HeadersManager, MessageManager, 
    EventManager, RouterManager, DatabaseManager
)
from managers.service_manager import ServiceManager

# Import new services
from services.notification_service import NotificationService
from services.service_tickets_stats_service import StatsService
from services.user_service import UserService
from services.feedback_service import FeedbackService
from services.poll_service import PollService
from services.rental_object_service import RentalObjectService
from services.rental_space_service import RentalSpaceService
from services.service_ticket_service import ServiceTicketService
from services.service_ticket_log_service import ServiceTicketLogService
from services.telegram_auth_service import TelegramAuthService

# Telegram-related imports
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Message
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from shared.entities.dialog import Dialog

# Logging setup (remains the same)
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)

# Utils and DynDialogHandlersManager classes (remain the same)
class Utils:
    def __init__(self):
        # These will be initialized inside Bot.__init__ to avoid circular imports
        self.dialog_converter = None
        self.locales_extractor = None

class DynDialogHandlersManager:
    def __init__(self):
        self.handlers: dict[int, Callable[["Bot", Update, ContextTypes.DEFAULT_TYPE, Dialog, int, int, int | None, str | None, int], Coroutine[Any, Any, int | str]]] = {}
        self.default_handler: Callable[["Bot", Update, ContextTypes.DEFAULT_TYPE, Dialog, int, int, int | None, str | None, int], Coroutine[Any, Any, int | str]] | None = None

    def add_handler(self, key: int, handler: Callable[["Bot", Update, ContextTypes.DEFAULT_TYPE, Dialog, int, int, int | None, str | None, int], Coroutine[Any, Any, int | str]]):
        self.handlers[key] = handler

    async def handle(self, key, bot, update: Update, context: ContextTypes.DEFAULT_TYPE, dialog: Dialog, sequence_id: int, item_id: int, option_id: int | None, answer: str | None, state: int):
        if key in self.handlers:
            await self.handlers[key](bot, update, context, dialog, sequence_id, item_id, option_id, answer, state)
        else:
            if self.default_handler:
                await self.default_handler(bot, update, context, dialog, sequence_id, item_id, option_id, answer, state)

class Bot:
    def __init__(self, application: Application, headers_data: dict = None):
        self.application = application
        
        # Initialize utilities
        from utils import DictExtractor, DialogConverter
        from locales.localisation_uni import Data as LocalisationData
        self.utils = Utils()
        self.utils.dialog_converter = DialogConverter()
        self.utils.locales_extractor = DictExtractor(LocalisationData)
        
        self.dyn_dialog_handlers_manager = DynDialogHandlersManager()
        self.dyn_dialogs: dict[int, Dialog] = {}
        
        # --- Refactoring Changes: Initialize Manager and Service Registries ---
        self.managers = ManagerRegistry(self)
        self.services = ServiceManager(self)
        
        # Setup managers and services
        self._setup_managers(headers_data or {})
        self._setup_services()
    
    def _setup_managers(self, headers_data: dict) -> None:
        """
        Set up and register all bot core managers.
        These are low-level components responsible for core functionalities.
        """
        # Register managers in the correct order (considering dependencies)
        self.managers.register_manager(StorageManager(self))
        self.managers.register_manager(HeadersManager(self))
        self.managers.register_manager(EventManager(self))
        self.managers.register_manager(MessageManager(self))
        self.managers.register_manager(RouterManager(self))
        self.managers.register_manager(DatabaseManager(self)) # Database is a core manager
    
        # --- Refactoring Changes: StatsManager and NotificationManager removed ---
        
        if headers_data:
            self.managers.headers.update(headers_data)

    def _setup_services(self) -> None:
        """
        Set up and register all bot services.
        Services represent a higher level of abstraction and contain business logic.
        """
        # Register services that were converted from managers
        self.services.register_service(NotificationService(self))
        self.services.register_service(StatsService(self))
        
        # Register CRUD services
        self.services.register_service(UserService(self))
        self.services.register_service(FeedbackService(self))
        self.services.register_service(PollService(self))
        self.services.register_service(RentalObjectService(self))
        self.services.register_service(RentalSpaceService(self))
        self.services.register_service(ServiceTicketService(self))
        self.services.register_service(ServiceTicketLogService(self))
        self.services.register_service(TelegramAuthService(self))

    async def handle_error(self, code: int, message: str):
        """Simple error handler"""
        print(f"Error {code}: {message}")

    def get_user_id(self, update: Update) -> int | None:
        if update.message and update.message.from_user:
            return update.message.from_user.id
        elif update.callback_query:
            return update.callback_query.from_user.id
        return None

    def get_text(self, key: str, payload: list[str] | None = None, group: str | None = "RU") -> str:
        text = self.utils.locales_extractor.get(key, payload, group) or key
        return text

    async def send_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
        payload: list[str] | None = None,
        parse_mode: ParseMode = ParseMode.HTML,
        dynamic: bool = True,
        refresh = False,
        images: list[str] | None = None
    ) -> None:
        """Delegates sending a message to MessageManager"""
        await self.managers.message.send_message(
            update, context, text, reply_markup, payload, parse_mode, dynamic, refresh, images
        )

    def create_keyboard(self, rows: list[list[tuple[str, int | str]]]) -> InlineKeyboardMarkup:
        keyboard = []
        for row in rows:
            keyboard_row = []
            for item in row:
                text = self.get_text(item[0])
                callback_data = item[1]
                keyboard_row.append(InlineKeyboardButton(text, callback_data=callback_data))
            keyboard.append(keyboard_row)
        return InlineKeyboardMarkup(keyboard)

    async def start_async(self):
        """Async method to start the bot with proper event loop handling"""
        # --- This initialization logic remains the same ---
        self.dyn_dialog_handlers_manager.add_handler(Dialogs.SERVICE, service_callback)
        self.dyn_dialog_handlers_manager.add_handler(Dialogs.PROFILE, profile_callback)
        self.dyn_dialog_handlers_manager.add_handler(Dialogs.POLL, poll_callback)
        self.dyn_dialog_handlers_manager.add_handler(Dialogs.FEEDBACK, feedback_callback)
        self.dyn_dialog_handlers_manager.add_handler(Dialogs.SERVICE_FEEDBACK, service_feedback_callback)
        self.dyn_dialog_handlers_manager.add_handler(Dialogs.SPACES, spaces_callback)
        self.dyn_dialogs = {
            Dialogs.SERVICE: self.utils.dialog_converter.convert("./assets/service_dialog.json"),
            Dialogs.PROFILE: self.utils.dialog_converter.convert("./assets/profile_dialog.json"),
            Dialogs.POLL: self.utils.dialog_converter.convert("./assets/poll_dialog.json"),
            Dialogs.FEEDBACK: self.utils.dialog_converter.convert("./assets/feedback_dialog.json"),
            Dialogs.SERVICE_FEEDBACK: self.utils.dialog_converter.convert("./assets/service_feedback_dialog.json")
        }
        self.managers.router.add_handler(Dialogs.START, start_app_dialog)
        self.managers.router.add_handler(Dialogs.DYN_DIALOG_ITEM, start_dyn_dialog)
        self.managers.router.add_handler(Dialogs.FEEDBACK, start_feedback_dialog)
        self.managers.router.add_handler(Dialogs.MENU, start_menu_dialog)
        self.managers.router.add_handler(Dialogs.PROFILE, start_profile_dialog)
        self.managers.router.add_handler(Dialogs.SERVICE, start_service_dialog)
        self.managers.router.add_handler(Dialogs.POLL, start_poll_dialog)
        self.managers.router.add_handler(Dialogs.SERVICE_FEEDBACK, start_service_feedback_dialog)
        self.managers.router.add_handler(Dialogs.SPACES, start_spaces_dialog)
        self.managers.router.add_handler(Dialogs.STATS, start_stats_dialog)
        self.managers.router.add_handler(Dialogs.TEST, start_test_dialog)
        self.application.add_handler(CommandHandler("start", self.handle_command))
        self.application.add_handler(CommandHandler("menu", self.handle_command))
        self.application.add_handler(CommandHandler("service", self.handle_command))
        self.application.add_handler(CommandHandler("profile", self.handle_command))
        self.application.add_handler(CommandHandler("poll", self.handle_command))
        self.application.add_handler(CommandHandler("feedback", self.handle_command))
        self.application.add_handler(CommandHandler("service_feedback", self.handle_command))
        self.application.add_handler(CommandHandler("spaces", self.handle_command))
        self.application.add_handler(CommandHandler("stats", self.handle_command))
        self.application.add_handler(CommandHandler("test", self.handle_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Initialize and start the application
        await self.application.initialize()
        
        # Initialize managers and services immediately after application initialization
        await self._post_init_hook(self.application)
        
        await self.application.start()
        await self.application.updater.start_polling()
        
        # Keep running indefinitely
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            await self.application.stop()
            await self.application.shutdown()
        
    def start(self):
        """Legacy sync method for backward compatibility."""
        # --- This initialization logic remains the same ---
        self.dyn_dialog_handlers_manager.add_handler(Dialogs.SERVICE, service_callback)
        self.dyn_dialog_handlers_manager.add_handler(Dialogs.PROFILE, profile_callback)
        self.dyn_dialog_handlers_manager.add_handler(Dialogs.POLL, poll_callback)
        self.dyn_dialog_handlers_manager.add_handler(Dialogs.FEEDBACK, feedback_callback)
        self.dyn_dialog_handlers_manager.add_handler(Dialogs.SERVICE_FEEDBACK, service_feedback_callback)
        self.dyn_dialog_handlers_manager.add_handler(Dialogs.SPACES, spaces_callback)
        self.dyn_dialogs = {
            Dialogs.SERVICE: self.utils.dialog_converter.convert("./assets/service_dialog.json"),
            Dialogs.PROFILE: self.utils.dialog_converter.convert("./assets/profile_dialog.json"),
            Dialogs.POLL: self.utils.dialog_converter.convert("./assets/poll_dialog.json"),
            Dialogs.FEEDBACK: self.utils.dialog_converter.convert("./assets/feedback_dialog.json"),
            Dialogs.SERVICE_FEEDBACK: self.utils.dialog_converter.convert("./assets/service_feedback_dialog.json")
        }
        self.managers.router.add_handler(Dialogs.START, start_app_dialog)
        self.managers.router.add_handler(Dialogs.DYN_DIALOG_ITEM, start_dyn_dialog)
        self.managers.router.add_handler(Dialogs.FEEDBACK, start_feedback_dialog)
        self.managers.router.add_handler(Dialogs.MENU, start_menu_dialog)
        self.managers.router.add_handler(Dialogs.PROFILE, start_profile_dialog)
        self.managers.router.add_handler(Dialogs.SERVICE, start_service_dialog)
        self.managers.router.add_handler(Dialogs.POLL, start_poll_dialog)
        self.managers.router.add_handler(Dialogs.SERVICE_FEEDBACK, start_service_feedback_dialog)
        self.managers.router.add_handler(Dialogs.SPACES, start_spaces_dialog)
        self.managers.router.add_handler(Dialogs.STATS, start_stats_dialog)
        self.managers.router.add_handler(Dialogs.TEST, start_test_dialog)
        self.application.add_handler(CommandHandler("start", self.handle_command))
        self.application.add_handler(CommandHandler("menu", self.handle_command))
        self.application.add_handler(CommandHandler("service", self.handle_command))
        self.application.add_handler(CommandHandler("profile", self.handle_command))
        self.application.add_handler(CommandHandler("poll", self.handle_command))
        self.application.add_handler(CommandHandler("feedback", self.handle_command))
        self.application.add_handler(CommandHandler("service_feedback", self.handle_command))
        self.application.add_handler(CommandHandler("spaces", self.handle_command))
        self.application.add_handler(CommandHandler("stats", self.handle_command))
        self.application.add_handler(CommandHandler("test", self.handle_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        self.application.post_init = self._post_init_hook
        self.application.run_polling()


    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            callback_data = update.callback_query.data
            user_id = self.get_user_id(update)
            handler, dialog_type = self.managers.event.get_input_handler(user_id)
            if handler and dialog_type == Actions.CALLBACK:
                self.managers.event.remove_input_handler(user_id)
                self.managers.storage.set(context, Variables.HANDLED_DATA, callback_data)
                await handler(update, context)
                return
            else:
                if ":" in callback_data:
                    action, *params = callback_data.split(":")
                else:
                    action = callback_data
                    params = []
                
                if action == str(Dialogs.DYN_DIALOG_ITEM) and params and params[0] == "-1":
                    action_id = action
                else:
                    try:
                        action_id = int(action)
                    except ValueError:
                        action_id = action
                
                if params:
                    context.user_data['callback_params'] = params
                await self.managers.router.execute(action_id, update, context)
        except Exception as e:
            print(f"Error handling callback: {e}")
            await self.send_message(update, context, "Произошла ошибка при обработке запроса. Разработчик уже уведомлен о проблеме.")
            await self.managers.router.execute(Dialogs.MENU, update, context)
            raise e

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = self.get_user_id(update)
        chat_id = update.message.chat.id if update.message else None
        
        # --- Debug logging remains the same ---
        
        if not user_id:
            return
            
        handler, dialog_type = self.managers.event.get_input_handler(user_id)
        if handler and dialog_type == Actions.TYPING:
            text = update.message.text.strip()
            self.managers.event.remove_input_handler(user_id)
            self.managers.storage.set(context, Variables.HANDLED_DATA, text)
            await handler(update, context)
        else:
            # --- Refactoring Change: Use NotificationService ---
            # Check if this is a message in the admin chat replying to a ticket
            if chat_id and self.services.notification.is_admin_chat(chat_id) and update.message.reply_to_message:
                try:
                    await self.services.notification.handle_admin_reply(update, context)
                except Exception:
                    import traceback
                    traceback.print_exc()

    async def handle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # --- This command handling logic remains the same ---
        try:
            command = update.message.text[1:]
            dialog_map = {
                "start": Dialogs.START,
                "menu": Dialogs.MENU,
                "service": Dialogs.SERVICE,
                "profile": Dialogs.PROFILE,
                "poll": Dialogs.POLL,
                "feedback": Dialogs.FEEDBACK,
                "service_feedback": Dialogs.SERVICE_FEEDBACK,
                "spaces": Dialogs.SPACES,
                "stats": Dialogs.STATS,
                "test": Dialogs.TEST
            }
            if command in dialog_map:
                dialog_id = dialog_map[command]
                self.managers.router.remove_trace_items(context, 0, 0)
                self.managers.router.set_entry_point_item(context, dialog_id)
                await self.managers.router.execute(dialog_id, update, context)
        except Exception as e:
            print(f"Error handling command: {e}")
            await self.managers.router.execute(Dialogs.MENU, update, context)

    def register_input_handler(self, user_id: int, dialog_type: int, handler: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        self.managers.event.register_input_handler(user_id, dialog_type, handler)

    async def _post_init_hook(self, application):
        """
        Post-initialization hook that sets up managers and services after bot startup.
        """
        # --- Refactoring Change: New initialization order ---
        try:
            print("Initializing bot managers...")
            await self.managers.initialize_all()
            print("All managers initialized successfully.")

            print("Initializing bot services...")
            await self.services.initialize_all()
            print("All services initialized successfully.")
            
        except Exception as e:
            print(f"FATAL: Error during post-initialization: {e}")
            import traceback
            traceback.print_exc()
            # In a real scenario, you might want to stop the bot if initialization fails
            # For now, we'll just log the error.
            raise

class Agent:
    def __init__(self):
        self.application: Application | None = None
        self.bot: Bot | None = None

    async def start_async(self, token: str, db_url: str, admin_chat_id: str, chief_engineer_chat_id: str = None):
        self.application = Application.builder().token(token).build()
        
        headers_data = {
            "ADMIN_CHAT_ID": admin_chat_id,
            "DB_URL": db_url # Pass DB URL via headers
        }
        if chief_engineer_chat_id:
            headers_data["CHIEF_ENGINEER_CHAT_ID"] = chief_engineer_chat_id
            
        # --- Refactoring Change: Simplified Bot constructor call ---
        self.bot = Bot(
            self.application,
            headers_data
        )
        await self.bot.start_async()
        
    def start(self, token: str, db_url: str, admin_chat_id: str, chief_engineer_chat_id: str = None):
        """Legacy sync method for backward compatibility"""
        self.application = Application.builder().token(token).build()
        
        headers_data = {
            "ADMIN_CHAT_ID": admin_chat_id,
            "DB_URL": db_url # Pass DB URL via headers
        }
        if chief_engineer_chat_id:
            headers_data["CHIEF_ENGINEER_CHAT_ID"] = chief_engineer_chat_id
            
        # --- Refactoring Change: Simplified Bot constructor call ---
        self.bot = Bot(
            self.application,
            headers_data
        )
        self.bot.start()

def main() -> None:
    # --- This main execution block remains the same ---
    parser = argparse.ArgumentParser(
        description="Telegram бот с подключением к MySQL"
    )
    parser.add_argument(
        "--token", 
        type=str, 
        required=False,
        help="Токен Telegram бота"
    )
    parser.add_argument(
        "--db-url", 
        type=str, 
        required=False,
        help="URL подключения к базе данных"
    )
    parser.add_argument(
        "--admin-chat-id",
        type=str,
        required=False,
        help="ID чата администратора (можно также через переменную окружения ADMIN_CHAT_ID)"
    )
    parser.add_argument(
        "--chief-engineer-chat-id",
        type=str,
        required=False,
        help="ID чата главного инженера (можно также через переменную окружения CHIEF_ENGINEER_CHAT_ID)"
    )
    args = parser.parse_args()
    token = args.token or os.getenv("BOT_TOKEN")
    db_url = args.db_url or os.getenv("DB_URL") or os.getenv("DATABASE_URL")
    admin_chat_id = args.admin_chat_id or os.getenv("ADMIN_CHAT_ID")
    chief_engineer_chat_id = args.chief_engineer_chat_id or os.getenv("CHIEF_ENGINEER_CHAT_ID")
    if not token:
        parser.error("Bot token must be provided via --token argument or BOT_TOKEN environment variable")
    if not admin_chat_id:
        parser.error("Admin chat ID must be provided via --admin-chat-id argument or ADMIN_CHAT_ID environment variable")
    agent = Agent()
    agent.start(token, db_url, admin_chat_id, chief_engineer_chat_id)

if __name__ == "__main__":
    main()