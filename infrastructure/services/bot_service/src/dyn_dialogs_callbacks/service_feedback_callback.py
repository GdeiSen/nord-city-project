from typing import TYPE_CHECKING

from shared.constants import Dialogs, Variables, CallbackResult

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from shared.entities.dialog import Dialog
    from bot import Bot


OPTION_ALL_OK = 100
OPTION_HAS_COMMENTS = 101
OPTION_QUALITY = 201
OPTION_SPEED = 202


def _build_ddid(dialog: "Dialog", sequence_id: int, item_id: int) -> str:
    return f"{dialog.id:04d}-{sequence_id:04d}-{item_id:04d}"


async def _save_and_deliver_feedback(
    *,
    bot: "Bot",
    update: "Update",
    ticket_id: int,
    dialog: "Dialog",
    sequence_id: int,
    item_id: int,
    answer: str,
    text: str | None = None,
) -> bool:
    user_id = bot.get_user_id(update)
    if user_id is None:
        return False

    audit_context = bot.services.feedback.build_telegram_actor_audit_context(
        telegram_user_id=user_id,
        reason="service_ticket_feedback_submitted_via_telegram",
        meta_updates={
            "ticket_id": int(ticket_id),
            "feedback_ddid": _build_ddid(dialog, sequence_id, item_id),
        },
    )
    saved_feedback = await bot.services.feedback.save_service_ticket_feedback(
        service_ticket_id=int(ticket_id),
        user_id=int(user_id),
        ddid=_build_ddid(dialog, sequence_id, item_id),
        answer=answer,
        text=text,
        _audit_context=audit_context,
    )
    if saved_feedback is None:
        return False

    await bot.services.notification.send_service_ticket_feedback(
        ticket_id=int(ticket_id),
        feedback_answer=saved_feedback.answer,
        feedback_text=saved_feedback.text,
        feedback_id=saved_feedback.id,
        _audit_context=audit_context,
    )
    return True


async def service_feedback_callback(
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
    Handles feedback for completed service tickets.

    The dyn-dialog engine invokes the callback twice on the final step:
    first while processing the answer and then with ``state=True`` to finish
    the dialog. We commit feedback only on the finishing call so the flow
    stays deterministic.
    """

    ticket_id = bot.managers.storage.get(context, Variables.USER_SERVICE_TICKET)

    if ticket_id is None:
        return CallbackResult.continue_()

    if sequence_id == 0 and item_id == 0 and option_id == OPTION_ALL_OK and state:
        await _save_and_deliver_feedback(
            bot=bot,
            update=update,
            ticket_id=int(ticket_id),
            dialog=dialog,
            sequence_id=sequence_id,
            item_id=item_id,
            answer=bot.get_text("service_feedback_all_ok"),
        )
        await bot.send_message(update, context, "service_feedback_thanks", dynamic=False)
        return await bot.managers.navigator.execute(Dialogs.MENU, update, context)

    if sequence_id == 1 and item_id == 1 and option_id in {OPTION_QUALITY, OPTION_SPEED} and state:
        answer_text = (
            bot.get_text("service_feedback_quality_problems")
            if option_id == OPTION_QUALITY
            else bot.get_text("service_feedback_speed_problems")
        )
        await _save_and_deliver_feedback(
            bot=bot,
            update=update,
            ticket_id=int(ticket_id),
            dialog=dialog,
            sequence_id=sequence_id,
            item_id=item_id,
            answer=answer_text,
        )
        await bot.send_message(update, context, "service_feedback_sent_to_recipient", dynamic=False)
        return await bot.managers.navigator.execute(Dialogs.MENU, update, context)

    if sequence_id == 4 and item_id == 4 and answer and state:
        await _save_and_deliver_feedback(
            bot=bot,
            update=update,
            ticket_id=int(ticket_id),
            dialog=dialog,
            sequence_id=sequence_id,
            item_id=item_id,
            answer=bot.get_text("dlg_svc_feedback_btn_other"),
            text=answer,
        )
        await bot.send_message(update, context, "service_feedback_sent_to_recipient", dynamic=False)
        return await bot.managers.navigator.execute(Dialogs.MENU, update, context)

    return CallbackResult.continue_()
