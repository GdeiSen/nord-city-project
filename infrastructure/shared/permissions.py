class PermissionCodes:
    SITE_ACCESS = "site.access"

    ROLES_MANAGE = "roles.manage"
    USERS_MANAGE = "users.manage"
    LOCALIZATION_MANAGE = "localization.manage"
    NOTIFICATIONS_SEND = "notifications.send"

    BOT_FEATURE_PROFILE = "bot.feature.profile"
    BOT_FEATURE_SERVICE = "bot.feature.service"
    BOT_FEATURE_POLL = "bot.feature.poll"
    BOT_FEATURE_FEEDBACK = "bot.feature.feedback"
    BOT_FEATURE_GUEST_PARKING = "bot.feature.guest_parking"
    BOT_FEATURE_SPACES = "bot.feature.spaces"

    SERVICE_TICKETS_MANAGE = "service_tickets.manage"
    PARKING_MANAGE = "parking.manage"
    PARKING_APPROVE = "parking.approve"


SUPER_ADMIN_ROLE_CODE = "super_admin"
ADMIN_ROLE_CODE = "admin"
EVERYONE_ROLE_CODE = "everyone"


DEFAULT_PERMISSIONS: tuple[dict[str, str], ...] = (
    {
        "code": PermissionCodes.SITE_ACCESS,
        "scope": "site",
        "name": "Доступ к сайту",
        "description": "Позволяет входить в административную панель.",
    },
    {
        "code": PermissionCodes.ROLES_MANAGE,
        "scope": "roles",
        "name": "Управление ролями",
        "description": "Позволяет создавать роли и изменять наборы прав.",
    },
    {
        "code": PermissionCodes.USERS_MANAGE,
        "scope": "users",
        "name": "Управление пользователями",
        "description": "Позволяет просматривать, создавать и редактировать пользователей.",
    },
    {
        "code": PermissionCodes.LOCALIZATION_MANAGE,
        "scope": "localization",
        "name": "Управление локализацией",
        "description": "Позволяет изменять тексты и настройки сообщений бота.",
    },
    {
        "code": PermissionCodes.NOTIFICATIONS_SEND,
        "scope": "notifications",
        "name": "Отправка оповещений",
        "description": "Позволяет отправлять массовые уведомления пользователям.",
    },
    {
        "code": PermissionCodes.BOT_FEATURE_PROFILE,
        "scope": "bot",
        "name": "Бот: профиль",
        "description": "Открывает пользователю профиль и первичную авторизацию в боте.",
    },
    {
        "code": PermissionCodes.BOT_FEATURE_SERVICE,
        "scope": "bot",
        "name": "Бот: обслуживание",
        "description": "Открывает создание заявок на обслуживание через бота.",
    },
    {
        "code": PermissionCodes.BOT_FEATURE_POLL,
        "scope": "bot",
        "name": "Бот: опросы",
        "description": "Открывает пользователю раздел опросов в боте.",
    },
    {
        "code": PermissionCodes.BOT_FEATURE_FEEDBACK,
        "scope": "bot",
        "name": "Бот: обратная связь",
        "description": "Открывает отправку обратной связи через бота.",
    },
    {
        "code": PermissionCodes.BOT_FEATURE_GUEST_PARKING,
        "scope": "bot",
        "name": "Бот: гостевая парковка",
        "description": "Открывает оформление заявок на гостевую парковку через бота.",
    },
    {
        "code": PermissionCodes.BOT_FEATURE_SPACES,
        "scope": "bot",
        "name": "Бот: свободные площади",
        "description": "Открывает просмотр свободных площадей через бота.",
    },
    {
        "code": PermissionCodes.SERVICE_TICKETS_MANAGE,
        "scope": "service_tickets",
        "name": "Управление заявками",
        "description": "Позволяет обрабатывать и администрировать заявки на обслуживание.",
    },
    {
        "code": PermissionCodes.PARKING_MANAGE,
        "scope": "parking",
        "name": "Управление парковкой",
        "description": "Позволяет просматривать и настраивать гостевую парковку.",
    },
    {
        "code": PermissionCodes.PARKING_APPROVE,
        "scope": "parking",
        "name": "Подтверждение парковки",
        "description": "Позволяет подтверждать и отклонять заявки на гостевую парковку.",
    },
)


EVERYONE_DEFAULT_PERMISSIONS = {
    PermissionCodes.BOT_FEATURE_PROFILE,
    PermissionCodes.BOT_FEATURE_SERVICE,
    PermissionCodes.BOT_FEATURE_GUEST_PARKING,
    PermissionCodes.BOT_FEATURE_SPACES,
}

ADMIN_DEFAULT_PERMISSIONS = {
    PermissionCodes.SITE_ACCESS,
    PermissionCodes.USERS_MANAGE,
    PermissionCodes.LOCALIZATION_MANAGE,
    PermissionCodes.NOTIFICATIONS_SEND,
    PermissionCodes.SERVICE_TICKETS_MANAGE,
    PermissionCodes.PARKING_MANAGE,
    PermissionCodes.PARKING_APPROVE,
    PermissionCodes.BOT_FEATURE_PROFILE,
    PermissionCodes.BOT_FEATURE_SERVICE,
    PermissionCodes.BOT_FEATURE_POLL,
    PermissionCodes.BOT_FEATURE_FEEDBACK,
    PermissionCodes.BOT_FEATURE_GUEST_PARKING,
    PermissionCodes.BOT_FEATURE_SPACES,
}
