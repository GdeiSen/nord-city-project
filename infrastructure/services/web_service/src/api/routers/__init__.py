# Explicit API routers — each resource has its own module
from .users import router as users_router
from .auth import router as auth_router
from .feedbacks import router as feedback_router
from .rental_objects import router as rental_objects_router
from .polls import router as poll_router
from .service_tickets import router as service_tickets_router
from .guest_parking import router as guest_parking_router
from .guest_parking_settings import router as guest_parking_settings_router
from .audit_log import router as audit_log_router
from .rental_spaces import router as rental_spaces_router
from .space_views import router as space_views_router
from .storage import router as storage_router
from .notifications import router as notifications_router
from .storage_files import router as storage_files_router
from .localization import router as localization_router
from .bot_settings import router as bot_settings_router

__all__ = [
    "users_router",
    "auth_router",
    "feedback_router",
    "rental_objects_router",
    "poll_router",
    "service_tickets_router",
    "guest_parking_router",
    "guest_parking_settings_router",
    "audit_log_router",
    "rental_spaces_router",
    "space_views_router",
    "storage_router",
    "notifications_router",
    "storage_files_router",
    "localization_router",
    "bot_settings_router",
]
