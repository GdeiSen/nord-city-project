import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.dependencies import get_audit_context, get_current_user
from api.schemas.bot_settings import BotSettingsDocument
from shared.clients.bot_client import bot_client
from shared.constants import AuditRetentionClass, Roles
from shared.utils.audit_events import append_business_audit_event

router = APIRouter(prefix="/bot-settings", tags=["Bot Settings"])
logger = logging.getLogger(__name__)


def _build_settings_diff(
    old_data: dict[str, Any],
    new_data: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    old_changes: dict[str, dict[str, Any]] = {}
    new_changes: dict[str, dict[str, Any]] = {}
    changed_paths: list[str] = []

    scopes = sorted(set(old_data.keys()) | set(new_data.keys()))
    for scope in scopes:
        old_scope = old_data.get(scope)
        new_scope = new_data.get(scope)

        if not isinstance(old_scope, dict) or not isinstance(new_scope, dict):
            if old_scope != new_scope:
                old_changes[scope] = {"_value": old_scope}
                new_changes[scope] = {"_value": new_scope}
                changed_paths.append(scope)
            continue

        keys = sorted(set(old_scope.keys()) | set(new_scope.keys()))
        for key in keys:
            old_value = old_scope.get(key)
            new_value = new_scope.get(key)
            if old_value == new_value:
                continue
            old_changes.setdefault(scope, {})[key] = old_value
            new_changes.setdefault(scope, {})[key] = new_value
            changed_paths.append(f"{scope}.{key}")

    return old_changes, new_changes, changed_paths


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role")
    if role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов.",
        )
    return current_user


@router.get("/", response_model=BotSettingsDocument)
async def get_bot_settings(_: dict = Depends(_require_admin)):
    response = await bot_client.bot_settings.get_settings()
    if not response.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=response.get("error", "Не удалось получить настройки из bot_service."),
        )

    payload = response.get("data")
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bot_service вернул некорректный формат настроек.",
        )
    return BotSettingsDocument.model_validate(payload)


@router.put("/", response_model=BotSettingsDocument)
async def update_bot_settings(
    body: BotSettingsDocument,
    request: Request,
    current_user: dict = Depends(_require_admin),
):
    previous_data: dict[str, Any] | None = None
    previous_response = await bot_client.bot_settings.get_settings()
    if previous_response.get("success") and isinstance(previous_response.get("data"), dict):
        previous_data = previous_response.get("data")

    response = await bot_client.bot_settings.update_settings(data=body.model_dump())
    if not response.get("success"):
        error = str(response.get("error", "Не удалось обновить настройки бота."))
        is_validation_error = error.startswith("validation_error:")
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
                if is_validation_error
                else status.HTTP_502_BAD_GATEWAY
            ),
            detail=error,
        )

    payload = response.get("data")
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bot_service вернул некорректный формат после обновления настроек.",
        )

    if previous_data is not None:
        old_changes, new_changes, changed_paths = _build_settings_diff(previous_data, payload)
        if changed_paths:
            audit_context = get_audit_context(request, current_user)
            audit_response = await append_business_audit_event(
                entity_type="BotConfig",
                entity_id=2,
                event_type="CONFIG_CHANGE",
                event_name="bot_config.settings_updated",
                action="update",
                source_service="web_service",
                audit_context=audit_context,
                retention_class=AuditRetentionClass.CRITICAL,
                reason="bot_settings_updated",
                old_data=old_changes,
                new_data=new_changes,
                meta={
                    "config_scope": "bot_settings",
                    "changed_keys_count": len(changed_paths),
                    "changed_keys_sample": changed_paths[:50],
                },
                audit_type="smart",
            )
            if not audit_response.get("success"):
                logger.warning(
                    "Bot settings updated, but audit append failed: %s",
                    audit_response.get("error"),
                )

    return BotSettingsDocument.model_validate(payload)
