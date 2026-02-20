"""
Shared Pydantic schemas for transport and API.
Used by all services - web, bot, database (for output serialization).
"""
from .user import UserSchema
from .object import ObjectSchema
from .space import SpaceSchema
from .service_ticket import ServiceTicketSchema
from .feedback import FeedbackSchema
from .poll_answer import PollAnswerSchema
from .guest_parking import GuestParkingSchema
from .audit_log import AuditLogSchema
from .space_view import SpaceViewSchema
from .service_tickets_stats import ServiceTicketsStatsSchema
from .otp_code import OtpCodeSchema
from .enrichment import UserSummary, ObjectSummary
