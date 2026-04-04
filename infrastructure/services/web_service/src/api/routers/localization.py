import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.dependencies import get_audit_context, get_current_user
from api.schemas.localization import LocalizationDocument
from shared.clients.bot_client import bot_client
from shared.constants import AuditRetentionClass, Roles
from shared.utils.audit_events import append_business_audit_event

router = APIRouter(prefix="/localization", tags=["Localization"])
logger = logging.getLogger(__name__)


def _build_localization_diff(
    old_data: dict[str, Any],
    new_data: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    old_changes: dict[str, dict[str, Any]] = {}
    new_changes: dict[str, dict[str, Any]] = {}
    changed_paths: list[str] = []

    locales = sorted(set(old_data.keys()) | set(new_data.keys()))
    for locale in locales:
        old_locale = old_data.get(locale)
        new_locale = new_data.get(locale)

        if not isinstance(old_locale, dict) or not isinstance(new_locale, dict):
            if old_locale != new_locale:
                old_changes[locale] = {"_value": old_locale}
                new_changes[locale] = {"_value": new_locale}
                changed_paths.append(locale)
            continue

        keys = sorted(set(old_locale.keys()) | set(new_locale.keys()))
        for key in keys:
            old_value = old_locale.get(key)
            new_value = new_locale.get(key)
            if old_value == new_value:
                continue
            old_changes.setdefault(locale, {})[key] = old_value
            new_changes.setdefault(locale, {})[key] = new_value
            changed_paths.append(f"{locale}.{key}")

    return old_changes, new_changes, changed_paths


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role")
    if role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов.",
        )
    return current_user


@router.get("/", response_model=LocalizationDocument)
async def get_localization(_: dict = Depends(_require_admin)):
    response = await bot_client.localization.get_localization()
    if not response.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=response.get("error", "Не удалось получить локализацию из bot_service."),
        )

    payload = response.get("data")
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bot_service вернул некорректный формат локализации.",
        )
    return LocalizationDocument(root=payload)


@router.put("/", response_model=LocalizationDocument)
async def update_localization(
    body: LocalizationDocument,
    request: Request,
    current_user: dict = Depends(_require_admin),
):
    previous_data: dict[str, Any] | None = None
    previous_response = await bot_client.localization.get_localization()
    if previous_response.get("success") and isinstance(previous_response.get("data"), dict):
        previous_data = previous_response.get("data")

    response = await bot_client.localization.update_localization(data=body.root)
    if not response.get("success"):
        error = str(response.get("error", "Не удалось обновить локализацию."))
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
            detail="bot_service вернул некорректный формат после обновления локализации.",
        )

    if previous_data is not None:
        old_changes, new_changes, changed_paths = _build_localization_diff(previous_data, payload)
        if changed_paths:
            audit_context = get_audit_context(request, current_user)
            audit_response = await append_business_audit_event(
                entity_type="BotConfig",
                entity_id=1,
                event_type="CONFIG_CHANGE",
                event_name="bot_config.localization_updated",
                action="update",
                source_service="web_service",
                audit_context=audit_context,
                retention_class=AuditRetentionClass.CRITICAL,
                reason="bot_localization_updated",
                old_data=old_changes,
                new_data=new_changes,
                meta={
                    "config_scope": "localization",
                    "changed_keys_count": len(changed_paths),
                    "changed_keys_sample": changed_paths[:50],
                    "locales": sorted(new_changes.keys()),
                },
                audit_type="smart",
            )
            if not audit_response.get("success"):
                logger.warning(
                    "Localization updated, but audit append failed: %s",
                    audit_response.get("error"),
                )

    return LocalizationDocument(root=payload)
