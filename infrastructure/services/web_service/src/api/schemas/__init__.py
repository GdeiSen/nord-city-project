# Web Service API Schemas
# Request/Response models matching frontend contract (web/types/index.ts, web/lib/api.ts)

from .common import MessageResponse

from .users import UserResponse, CreateUserRequest, UpdateUserBody
from .auth import UserAuthResponse, CreateAuthRequest, UpdateAuthBody
from .feedbacks import FeedbackResponse, CreateFeedbackRequest, UpdateFeedbackBody
from .rental_objects import ObjectResponse, CreateObjectRequest, UpdateObjectBody
from .polls import PollAnswerResponse, CreatePollRequest, UpdatePollBody
from .service_tickets import (
    ServiceTicketResponse,
    CreateServiceTicketRequest,
    UpdateServiceTicketBody,
    ServiceTicketsStatsResponse,
)
from .audit_log import AuditLogEntryResponse
from .rental_spaces import SpaceResponse, CreateSpaceRequest, UpdateSpaceBody
from .space_views import SpaceViewResponse, CreateSpaceViewRequest, UpdateSpaceViewBody
