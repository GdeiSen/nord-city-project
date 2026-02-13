from typing import TYPE_CHECKING
from datetime import datetime
from shared.constants import Dialogs, Variables

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from bot import Bot
    from shared.entities.dialog import Dialog


async def poll_callback(
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
    Handles poll responses and stores them using the new DDID-based system.
    
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
            # Use option ID as answer value if answer not provided
            answer_value = answer
            if answer_value is None and option_id is not None:
                answer_value = str(option_id)
            elif answer_value is None:
                answer_value = ""  # Empty string instead of None
                
            # Create DDID in format "0000-0000-0000" (dialog_id-sequence_id-item_id)
            ddid = f"{dialog.id:04d}-{sequence_id:04d}-{item_id:04d}"
            
            # Find existing poll answer by DDID or create new one
            existing_answers = await bot.services.poll.find_poll_answers(
                user_id=user_id,
                ddid=ddid
            )
            
            if existing_answers:
                # Update existing answer
                answer_id = existing_answers[0].id
                update_data = {
                    'answer': answer_value
                }
                await bot.services.poll.update_poll(answer_id, update_data)
            else:
                from shared.models.poll_answer import PollAnswer
                answer_obj = PollAnswer(user_id=user_id, ddid=ddid, answer=answer_value)
                await bot.services.poll.create_poll(answer_obj)
            
    if state == 1:
        await bot.send_message(update, context, "poll_completed", dynamic=False)
        # Clear trace before transitioning to menu to avoid element access errors
        bot.managers.storage.set(context, Variables.ACTIVE_DIALOG_TRACE, [])
        return await bot.managers.router.execute(Dialogs.MENU, update, context)
