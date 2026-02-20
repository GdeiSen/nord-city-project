"""
Pydantic-схемы для валидации RPC-параметров на границе database_service.

Используются для model_data (create) и update_data (update).
Обеспечивают корректный парсинг datetime и других типов из JSON.
"""
from typing import Optional, Type

from pydantic import BaseModel

from .guest_parking import GuestParkingCreateRpc, GuestParkingUpdateRpc

# Реестр: (service, method, param_name) -> schema class
RPC_PARAM_SCHEMAS: dict[tuple[str, str, str], type[BaseModel]] = {
    ("guest_parking", "create", "model_data"): GuestParkingCreateRpc,
    ("guest_parking", "update", "update_data"): GuestParkingUpdateRpc,
}


def get_rpc_schema(service: str, method: str, param_name: str) -> Optional[Type[BaseModel]]:
    """Возвращает схему для валидации RPC-параметра или None."""
    return RPC_PARAM_SCHEMAS.get((service, method, param_name))
