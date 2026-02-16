from typing import TYPE_CHECKING
from shared.constants import Dialogs, Variables
import json
from datetime import datetime
from shared.models.service_ticket import ServiceTicket

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes
    from shared.entities.dialog import Dialog
    from bot import Bot

async def service_callback(
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
    Handles service ticket creation and management in the dynamic dialog system.
    
    This callback processes user interactions during service ticket creation,
    collecting information across multiple dialog steps and maintaining ticket
    state throughout the conversation. Uses the modern DDID (Dialog-Dialog-Item-ID)
    system for tracking dialog context.
    
    Process Flow:
    1. Retrieves or creates service ticket for items 97-99 (description, location, phone)
    2. Collects user trace data and dialog interactions for context
    3. Processes specific answers based on item_id:
       - item_id=97: Service description text
       - item_id=98: Service location
       - item_id=99: User phone number
    4. Finalizes ticket creation when state=1 and sends notifications
    
    Args:
        bot (Bot): Main bot instance with access to services and managers
        update (Update): Telegram update containing user interaction
        context (ContextTypes.DEFAULT_TYPE): Telegram context for session management
        dialog (Dialog): Current dialog definition and metadata
        sequence_id (int): Current sequence identifier in dialog flow
        item_id (int): Current item identifier within sequence
        option_id (int | None): Selected option ID from inline keyboard
        answer (str | None): Text input provided by user
        state (int): Dialog completion state (1=complete, 0=continue)
        
    Returns:
        int | str: Next dialog state identifier or completion status
        
    Raises:
        Exception: May raise exceptions from storage operations or API calls
        
    Example:
        Called automatically when user interacts with service ticket dialog items.
        Maintains ticket state in context storage between interactions.
    """
    service_ticket = bot.managers.storage.get(context, Variables.USER_SERVICE_TICKET)
    if (item_id not in [97, 98, 99]):
        service_ticket = None
        bot.managers.storage.set(context, Variables.USER_SERVICE_TICKET, None)
    if (item_id in [97, 98, 99]):
        if (service_ticket is None):
            user_id = update.effective_user.id
            user = await bot.services.user.get_user_by_id(user_id)
            object_id = user.object_id if user else None
            ddid = f"{dialog.id:04d}-{sequence_id:04d}-{item_id:04d}"
            service_ticket = ServiceTicket(
                id=None,
                user_id=user_id,
                object_id=object_id,
                ddid=ddid,
                description=None,
                location=None,
                status="NEW",
                msid=None
            )
            
            active_dialog = bot.managers.storage.get(context, Variables.ACTIVE_DYN_DIALOG)
            active_items = active_dialog.items
            active_options = active_dialog.options
            
            raw_trace = bot.managers.router.get_current_trace(context)
            
            meta = json.loads(service_ticket.meta) if service_ticket.meta else {}
            meta["raw_trace"] = raw_trace
            
            filtered_items = []
            chosen_options = []
            
            for raw_item in raw_trace:
                if (":" not in str(raw_item)):
                    continue
                
                parts = str(raw_item).split(":")
                
                if len(parts) < 2:
                    continue
                
                try:
                    if len(parts) >= 4:
                        trace_dialog_item = int(parts[0])
                        dialog_id = int(parts[1])
                        _sequence_id = int(parts[2])
                        _item_id = int(parts[3])
                        _option_id = int(parts[4]) if len(parts) >= 5 and parts[4].isdigit() else None
                        
                        if _item_id in active_items:
                            item = active_items[_item_id]
                            if item is not None:
                                filtered_items.append({
                                    "id": _item_id,
                                    "text": item.text,
                                    "type": item.type
                                })
                                
                                if _option_id is not None:
                                    if _option_id in active_options:
                                        option = active_options[_option_id]
                                        chosen_options.append({
                                            "item_id": _item_id,
                                            "option_id": _option_id,
                                            "text": option.text
                                        })
                    
                except (ValueError, IndexError):
                    print(f"Failed to process trace item: {raw_item}")
                    continue
            
            formatted_trace = []
            item_to_options = {}
            
            for option in chosen_options:
                item_id = option["item_id"]
                item_to_options[item_id] = option
            
            for i, item in enumerate(filtered_items):
                item_id = item["id"]
                item_text = item["text"]
                
                next_option = None
                if i < len(filtered_items) - 1:
                    next_item_id = filtered_items[i + 1]["id"]
                    if next_item_id in item_to_options:
                        next_option = item_to_options[next_item_id]
                
                if next_option:
                    formatted_trace.append(f"{item_text}: {next_option['text']}")
                else:
                    formatted_trace.append(item_text)
            
            meta["trace"] = formatted_trace
            
            if not service_ticket.description and formatted_trace:
                last_item_option_pair = None
                for i, item in enumerate(filtered_items):
                    item_id = item["id"]
                    if item_id in [97, 98, 99]:
                        break
                    if i < len(filtered_items) - 1:
                        next_item_id = filtered_items[i + 1]["id"]
                        if next_item_id in item_to_options:
                            last_item_option_pair = f"{item['text']} | {item_to_options[next_item_id]['text']}"
                if last_item_option_pair:
                    service_ticket.description = last_item_option_pair
            
            service_ticket.meta = json.dumps(meta, ensure_ascii=False)
        
        if (item_id == 97):
            service_ticket.description = answer
        if (item_id == 98):
            service_ticket.location = answer
        if (item_id == 99):
            meta = json.loads(service_ticket.meta) if service_ticket.meta else {}
            meta["phone_number"] = answer
            service_ticket.meta = json.dumps(meta, ensure_ascii=False)
        
        bot.managers.storage.set(context, Variables.USER_SERVICE_TICKET, service_ticket)
        
    if state == 1:
        saved_ticket = await bot.services.service_ticket.create_service_ticket(service_ticket)
        bot.managers.storage.set(context, Variables.USER_SERVICE_TICKET, None)
        if saved_ticket:
            await bot.services.notification.notify_new_ticket(saved_ticket)
        await bot.send_message(update, context, "service_ticket_completed", dynamic=False)
        return await bot.managers.router.execute(Dialogs.MENU, update, context)

    return Dialogs.DYN_DIALOG_ITEM



