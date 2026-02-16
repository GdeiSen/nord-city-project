from typing import TYPE_CHECKING
from datetime import datetime
from shared.models import Feedback
from shared.constants import Dialogs

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot
    from entities.dialog import Dialog

async def feedback_callback(
    bot: "Bot",
    update: "Update",
    context: "ContextTypes.DEFAULT_TYPE",
    dialog: "Dialog",
    sequence_id: "int",
    item_id: "int",
    option_id: "int | None",
    answer: "str | None",
    state: "int",
) -> int | str:
    """
    Handles feedback submission using the new DDID-based system.
    
    Args:
        bot: Bot instance
        update: Telegram update
        context: Telegram context
        dialog: Current dialog
        sequence_id: Sequence ID in dialog
        item_id: Item ID in sequence
        option_id: Selected option ID (if applicable)
        answer: Text answer from user
        state: Current dialog state
        
    Returns:
        Next dialog state or completion code
    """
    user_id = bot.get_user_id(update)
    if user_id:
        user = await bot.services.user.get_user_by_id(user_id)
        if user:
            # Create DDID in format "0000-0000-0000" (dialog_id-sequence_id-item_id)
            ddid = f"{dialog.id:04d}-{sequence_id:04d}-{item_id:04d}"
            
            from shared.models.feedback import Feedback
            feedback = Feedback(user_id=user_id, ddid=ddid, answer=answer or "")
            await bot.services.feedback.create_feedback(feedback)
            
    if state == 1:
        await bot.send_message(update, context, "feedback_completed", dynamic=False)
        return await bot.managers.router.execute(Dialogs.MENU, update, context)
    return True
