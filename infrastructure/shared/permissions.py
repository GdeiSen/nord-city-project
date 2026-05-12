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
    {"code": PermissionCodes.SITE_ACCESS, "scope": "site", "name": "Доступ к сайту"},
    {"code": PermissionCodes.ROLES_MANAGE, "scope": "roles", "name": "Управление ролями"},
    {"code": PermissionCodes.USERS_MANAGE, "scope": "users", "name": "Управление пользователями"},
    {"code": PermissionCodes.LOCALIZATION_MANAGE, "scope": "localization", "name": "Управление локализацией"},
    {"code": PermissionCodes.NOTIFICATIONS_SEND, "scope": "notifications", "name": "Отправка оповещений"},
    {"code": PermissionCodes.BOT_FEATURE_PROFILE, "scope": "bot", "name": "Бот: профиль"},
    {"code": PermissionCodes.BOT_FEATURE_SERVICE, "scope": "bot", "name": "Бот: обслуживание"},
    {"code": PermissionCodes.BOT_FEATURE_POLL, "scope": "bot", "name": "Бот: опросы"},
    {"code": PermissionCodes.BOT_FEATURE_FEEDBACK, "scope": "bot", "name": "Бот: обратная связь"},
    {"code": PermissionCodes.BOT_FEATURE_GUEST_PARKING, "scope": "bot", "name": "Бот: гостевая парковка"},
    {"code": PermissionCodes.BOT_FEATURE_SPACES, "scope": "bot", "name": "Бот: свободные площади"},
    {"code": PermissionCodes.SERVICE_TICKETS_MANAGE, "scope": "service_tickets", "name": "Управление заявками"},
    {"code": PermissionCodes.PARKING_MANAGE, "scope": "parking", "name": "Управление парковкой"},
    {"code": PermissionCodes.PARKING_APPROVE, "scope": "parking", "name": "Подтверждение парковки"},
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
