from models.permission import Permission
from .base_service import BaseService


class PermissionService(BaseService):
    model_class = Permission
