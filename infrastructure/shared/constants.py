class Roles:
    LPR = 10011
    MA = 20122
    MANAGER = 10014
    ADMIN = 10012
    SUPER_ADMIN = 10013
    GUEST = 00000



class Dialogs:
    SERVICE = 1
    PROFILE = 2
    POLL = 3
    FEEDBACK = 4
    FEEDBACK_SEND = 5
    FEEDBACK_SET = 6
    DYN_DIALOG = 7
    DYN_DIALOG_ITEM = 8
    DYN_DIALOG_IMAGE_UPLOAD = 9
    DYN_DIALOG_TEXT_INPUT = 10
    DYN_DIALOG_OPTION_SELECT = 11
    DYN_DIALOG_PREV_ITEM = 12
    MENU = 13
    START = 14
    SERVICE_FEEDBACK = 15
    SERVICE_COMPLAINT = 16
    SPACES = 30
    STATS = 31
    TEST = 32
    GUEST_PARKING = 33

class Actions:
    TYPING = 200
    UPLOADING = 201
    SETTING = 202
    CANCELING = 203
    CLEARING = 204
    SELECTING = 205
    END = 206
    SENDING = 207
    EDITING = 208
    BACK = 209
    CANCEL = 210
    CALLBACK = 211

class DialogCallbackResult:
    """Результаты callback-ов dyn_dialog, сигнализирующие особое поведение.
    Deprecated: используйте CallbackResult.
    """
    SKIP_AND_COMPLETE = "_SKIP_AND_COMPLETE"


# --- Единый контракт возвращаемых значений callback ---

from dataclasses import dataclass
from enum import Enum


class CallbackActionResult(str, Enum):
    """Действия, которые callback может вернуть для управления flow dyn_dialog."""
    CONTINUE = "continue"           # перейти к следующему шагу (нормальный flow)
    RETRY_CURRENT = "retry_current" # остаться на текущем шаге (ошибка валидации)
    SKIP_AND_COMPLETE = "skip_and_complete"  # пропустить оставшиеся шаги и завершить


@dataclass
class CallbackResult:
    """
    Унифицированный результат callback динамического диалога.

    Использование:
        return CallbackResult(CallbackActionResult.CONTINUE)
        return CallbackResult(CallbackActionResult.RETRY_CURRENT, sequence_id=0, item_index=2)
        return CallbackResult(CallbackActionResult.SKIP_AND_COMPLETE)
    """
    action: CallbackActionResult
    sequence_id: int | None = None
    item_index: int | None = None

    @classmethod
    def continue_(cls) -> "CallbackResult":
        return cls(CallbackActionResult.CONTINUE)

    @classmethod
    def retry_current(cls, sequence_id: int, item_index: int) -> "CallbackResult":
        return cls(CallbackActionResult.RETRY_CURRENT, sequence_id, item_index)

    @classmethod
    def skip_and_complete(cls) -> "CallbackResult":
        return cls(CallbackActionResult.SKIP_AND_COMPLETE)


class DynDialogItemType:
    """Типы элементов dyn_dialog (type в Item)."""
    SELECT = 0  # Выбор из опций (кнопки)
    TEXT_INPUT = 1  # Ввод текста


class Variables:
    SERVICE_DESCRIPTION = 100
    SERVICE_LOCATION = 101
    SERVICE_IMAGE = 102
    ACTIVE_DIALOG = 103
    ACTIVE_ACTION = 104
    BUFFER_DATA_INPUTT = 105
    BUFFER_MESSAGES = 106
    USER_NAME = 107
    USER_LEGAL_ENTITY = 108
    USER_OBJECT = 109
    BUFFER_POLL = 110
    BUFFER_DIALOG_ANSWER = 111
    ACTIVE_DIALOG_SEQUENCE_ID = 112
    ACTIVE_DIALOG_SEQUENCE_ITEM_INDEX = 113
    ACTIVE_DYN_DIALOG = 114
    ACTIVE_DIALOG_TRACE = 115
    FEEDBACK_BUFFER = 116
    FIRST_START = 117
    HANDLED_DATA = 128
    FALLBACK_DIALOG_TRACE = 129
    USER_SERVICE_TICKET = 130
    SERVICE_FEEDBACK_MESSAGE = 131
    BUFFER_MEDIA_MESSAGES = 132
    GUEST_PARKING_DATA = 133

class ServiceTicketStatus:
    NEW = "NEW"
    ACCEPTED = "ACCEPTED"
    ASSIGNED = "ASSIGNED"
    COMPLETED = "COMPLETED"
    IN_PROGRESS = "IN_PROGRESS"


class FeedbackTypes:
    GENERAL = "GENERAL"
    SERVICE_TICKET = "SERVICE_TICKET"


class StorageFileKind:
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"
    OTHER = "OTHER"


class StorageFileCategory:
    DEFAULT = "DEFAULT"
    SYSTEM = "SYSTEM"
    TEMP = "TEMP"


class AuditActorType:
    USER = "USER"
    TELEGRAM_USER = "TELEGRAM_USER"
    SYSTEM = "SYSTEM"
    SERVICE = "SERVICE"


class AuditEventCategory:
    DATA_CHANGE = "DATA_CHANGE"
    BUSINESS_EVENT = "BUSINESS_EVENT"
    DELIVERY_EVENT = "DELIVERY_EVENT"


class AuditRetentionClass:
    CRITICAL = "CRITICAL"
    OPERATIONAL = "OPERATIONAL"
    TECHNICAL = "TECHNICAL"


# Entity types (model __name__) that should be audited
AUDITED_ENTITY_TYPES = frozenset(
    {
        "User",
        "Feedback",
        "Object",
        "PollAnswer",
        "ServiceTicket",
        "Space",
        "SpaceView",
        "GuestParkingRequest",
        "GuestParkingSettings",
        "StorageFile",
        "TelegramChat",
    }
)

# Audit modes: fast (no old/new), smart (diff only), heavy (full old/new)
AUDIT_MODE_FAST = "fast"
AUDIT_MODE_SMART = "smart"
AUDIT_MODE_HEAVY = "heavy"

# Технические поля: update только этих полей от bot_service не пишется в аудит
AUDIT_SKIP_UPDATE_FIELDS = frozenset()

# Дефолтный лимит для find_by_entity, чтобы избежать неограниченных выборок
AUDIT_FIND_BY_ENTITY_DEFAULT_LIMIT = 500

# Максимальный размер JSON для heavy audit (bytes). Превышение → сохранение placeholder.
AUDIT_HEAVY_MAX_JSON_BYTES = 100_000

# Per-entity audit mode. Default: fast. ServiceTicket: smart.
AUDIT_ENTITY_MODES: dict[str, str] = {
    "User": AUDIT_MODE_SMART,
    "Feedback": AUDIT_MODE_SMART,
    "Object": AUDIT_MODE_SMART,
    "PollAnswer": AUDIT_MODE_SMART,
    "ServiceTicket": AUDIT_MODE_SMART,
    "Space": AUDIT_MODE_SMART,
    "SpaceView": AUDIT_MODE_SMART,
    "GuestParkingRequest": AUDIT_MODE_SMART,
    "GuestParkingSettings": AUDIT_MODE_SMART,
    "StorageFile": AUDIT_MODE_FAST,
    "TelegramChat": AUDIT_MODE_SMART,
}

# Retention policy by entity type.
AUDIT_ENTITY_RETENTION_CLASS: dict[str, str] = {
    "User": AuditRetentionClass.CRITICAL,
    "Object": AuditRetentionClass.CRITICAL,
    "Space": AuditRetentionClass.CRITICAL,
    "GuestParkingSettings": AuditRetentionClass.CRITICAL,
    "TelegramChat": AuditRetentionClass.CRITICAL,
    "ServiceTicket": AuditRetentionClass.OPERATIONAL,
    "GuestParkingRequest": AuditRetentionClass.OPERATIONAL,
    "Feedback": AuditRetentionClass.OPERATIONAL,
    "PollAnswer": AuditRetentionClass.OPERATIONAL,
    "SpaceView": AuditRetentionClass.TECHNICAL,
    "StorageFile": AuditRetentionClass.TECHNICAL,
}

AUDIT_RETENTION_DAYS: dict[str, int] = {
    AuditRetentionClass.CRITICAL: 365,
    AuditRetentionClass.OPERATIONAL: 180,
    AuditRetentionClass.TECHNICAL: 45,
}

ASSIGNEE_SYSTEM = 1
