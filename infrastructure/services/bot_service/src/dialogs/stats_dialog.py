from typing import TYPE_CHECKING
from shared.constants import Dialogs, Actions

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot


async def start_stats_dialog(update: "Update", context: "ContextTypes.DEFAULT_TYPE", bot: "Bot") -> int:
    """
    Displays statistics dialog with ticket metrics and system information.
    
    This function shows comprehensive statistics about service tickets, including
    counts by status, recent activity, and performance metrics. Access is typically
    restricted to authorized users based on their role.
    
    Args:
        update (Update): Telegram update containing user interaction
        context (ContextTypes.DEFAULT_TYPE): Telegram context for session management
        bot (Bot): Main bot instance with access to services and managers
        
    Features:
    - Total ticket counts by status
    - Recent activity summaries
    - Performance metrics
    - Export capabilities for authorized users
    
    Returns:
        int: Dialog constant or Actions.END
    """
    try:
        user_id = bot.get_user_id(update)
        if not user_id:
            return Actions.END
        
        user = await bot.services.user.get_user_by_id(user_id)
        if not user:
            return Actions.END
        
        await bot.services.stats.recreate_stats_message()
        
        return Dialogs.MENU
        
    except Exception as e:
        print(f"Error in start_stats_dialog: {e}")
        return Actions.END