import logging
import re
from typing import Any, List
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from shared.clients.bot_client import bot_client
from shared.constants import AuditRetentionClass, Roles
from shared.clients.database_client import db_client
from shared.schemas.poll_answer import PollAnswerSchema
from shared.utils.audit_events import append_business_audit_event
from api.dependencies import get_audit_context, get_current_user, get_optional_current_user
from api.schemas.common import MessageResponse
from api.schemas.polls import (
    CreatePollRequest,
    PollAnswerResponse,
    PollGoogleFormSettingsRequest,
    PollGoogleFormSettingsResponse,
    UpdatePollBody,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/polls", tags=["Polls"])

_GOOGLE_FORM_LINK_REGEX = re.compile(
    r"https?://(?:forms\.gle/[^\s<>\"]+|docs\.google\.com/forms/[^\s<>\"]+)",
    re.IGNORECASE,
)
_ANY_LINK_REGEX = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
_POLL_HEADER_KEY = "poll_header"


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role")
    if role not in (Roles.ADMIN, Roles.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов.",
        )
    return current_user


def _is_valid_google_form_url(url: str) -> bool:
    raw = (url or "").strip()
    if not raw:
        return False
    try:
        parsed = urlparse(raw)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.netloc or "").lower().split(":", 1)[0]
    if host == "forms.gle":
        return bool(parsed.path.strip("/"))
    if host == "docs.google.com":
        return "/forms/" in (parsed.path or "").lower()
    return False


def _extract_google_form_links(text: str) -> list[str]:
    return [match.group(0) for match in _GOOGLE_FORM_LINK_REGEX.finditer(text or "")]


def _resolve_locale_bucket(localization: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    for key in ("RU", "ru"):
        bucket = localization.get(key)
        if isinstance(bucket, dict):
            return key, bucket
    for key, bucket in localization.items():
        if isinstance(bucket, dict) and str(key).lower() == "ru":
            return str(key), bucket
    localization["RU"] = {}
    return "RU", localization["RU"]


async def _get_localization_payload() -> dict[str, Any]:
    localization_response = await bot_client.localization.get_localization()
    if not localization_response.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=localization_response.get("error", "Не удалось получить локализацию из bot_service."),
        )
    data = localization_response.get("data")
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bot_service вернул некорректный формат локализации.",
        )
    return data


@router.post("/", response_model=PollAnswerResponse, status_code=status.HTTP_201_CREATED)
async def create_poll(body: CreatePollRequest, request: Request):
    response = await db_client.poll.create(
        model_data=body.model_dump(),
        model_class=PollAnswerSchema,
        _audit_context=get_audit_context(request, get_optional_current_user(request)),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to create poll answer")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    return response["data"]


@router.get("/", response_model=List[PollAnswerResponse])
async def get_all_polls():
    response = await db_client.poll.get_all(model_class=PollAnswerSchema)
    if not response.get("success"):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=response.get("error", "Failed to fetch poll answers"))
    return response.get("data", [])


@router.get("/settings/google-form", response_model=PollGoogleFormSettingsResponse)
async def get_poll_google_form_settings(_: dict = Depends(_require_admin)):
    localization = await _get_localization_payload()
    locale_key, locale_bucket = _resolve_locale_bucket(localization)
    poll_header = str(locale_bucket.get(_POLL_HEADER_KEY) or "")
    links = _extract_google_form_links(poll_header)

    return PollGoogleFormSettingsResponse(
        locale=locale_key,
        poll_header=poll_header,
        google_form_url=links[-1] if links else "",
    )


@router.put("/settings/google-form", response_model=PollGoogleFormSettingsResponse)
async def update_poll_google_form_settings(
    body: PollGoogleFormSettingsRequest,
    request: Request,
    current_user: dict = Depends(_require_admin),
):
    poll_header = str(body.poll_header or "").strip()
    url = (body.google_form_url or "").strip()

    if not poll_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сообщение опроса не может быть пустым.",
        )

    localization = await _get_localization_payload()
    locale_key, locale_bucket = _resolve_locale_bucket(localization)
    old_poll_header = str(locale_bucket.get(_POLL_HEADER_KEY) or "")
    old_links = _extract_google_form_links(old_poll_header)

    all_links = [match.group(0) for match in _ANY_LINK_REGEX.finditer(poll_header)]
    google_links = _extract_google_form_links(poll_header)

    if len(all_links) != 1 or len(google_links) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сообщение должно содержать ровно одну ссылку, и она должна вести на Google Форму.",
        )

    detected_url = google_links[0].strip()
    if not _is_valid_google_form_url(detected_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажите корректную ссылку на Google Форму (forms.gle или docs.google.com/forms).",
        )

    if url and url != detected_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ссылка в сообщении не совпадает с переданным URL Google Формы.",
        )

    new_poll_header = poll_header
    locale_bucket[_POLL_HEADER_KEY] = new_poll_header
    localization[locale_key] = locale_bucket

    update_response = await bot_client.localization.update_localization(data=localization)
    if not update_response.get("success"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=update_response.get("error", "Не удалось обновить poll_header в локализации."),
        )

    updated_data = update_response.get("data")
    if not isinstance(updated_data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="bot_service вернул некорректный формат после обновления локализации.",
        )

    audit_ctx = get_audit_context(request, current_user)
    audit_response = await append_business_audit_event(
        entity_type="BotConfig",
        entity_id=1,
        event_type="CONFIG_CHANGE",
        event_name="bot_config.poll_google_form_link_updated",
        action="update",
        source_service="web_service",
        audit_context=audit_ctx,
        retention_class=AuditRetentionClass.CRITICAL,
        reason="poll_google_form_link_updated",
        old_data={locale_key: {_POLL_HEADER_KEY: old_poll_header}},
        new_data={locale_key: {_POLL_HEADER_KEY: new_poll_header}},
        meta={
            "config_scope": "poll_google_form_link",
            "replaced_links_count": len(old_links),
            "last_detected_previous_link": old_links[-1] if old_links else "",
            "new_link": detected_url,
        },
        audit_type="smart",
    )
    if not audit_response.get("success"):
        logger.warning("Poll settings updated, but audit append failed: %s", audit_response.get("error"))

    return PollGoogleFormSettingsResponse(
        locale=locale_key,
        poll_header=new_poll_header,
        google_form_url=detected_url,
    )


@router.get("/{entity_id}", response_model=PollAnswerResponse)
async def get_poll_by_id(entity_id: int):
    response = await db_client.poll.get_by_id(
        entity_id=entity_id,
        model_class=PollAnswerSchema,
    )
    if not response.get("success"):
        error = response.get("error", "Poll answer not found")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    if response.get("data") is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll answer not found")
    return response["data"]


@router.put("/{entity_id}", response_model=MessageResponse)
async def update_poll(entity_id: int, body: UpdatePollBody, request: Request):
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    response = await db_client.poll.update(
        entity_id=entity_id,
        update_data=update_data,
        _audit_context=get_audit_context(request, get_optional_current_user(request)),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to update poll answer")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return MessageResponse(message="Poll answer updated successfully", id=entity_id)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poll(entity_id: int, request: Request):
    response = await db_client.poll.delete(
        entity_id=entity_id,
        _audit_context=get_audit_context(request, get_optional_current_user(request)),
    )
    if not response.get("success"):
        error = response.get("error", "Failed to delete poll answer")
        code = status.HTTP_404_NOT_FOUND if "not found" in error.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
