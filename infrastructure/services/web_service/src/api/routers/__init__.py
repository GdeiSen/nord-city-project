# Explicit API routers — each resource has its own module
from .users import router as users_router
from .auth import router as auth_router
from .feedbacks import router as feedback_router
from .rental_objects import router as rental_objects_router
from .polls import router as poll_router
from .service_tickets import router as service_tickets_router
from .audit_log import router as audit_log_router
from .rental_spaces import router as rental_spaces_router
from .space_views import router as space_views_router
from .media import router as media_router

__all__ = [
    "users_router",
    "auth_router",
    "feedback_router",
    "rental_objects_router",
    "poll_router",
    "service_tickets_router",
    "audit_log_router",
    "rental_spaces_router",
    "space_views_router",
    "media_router",
]
