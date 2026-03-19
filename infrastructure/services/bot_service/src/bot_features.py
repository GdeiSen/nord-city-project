from dataclasses import dataclass

from shared.constants import Dialogs


@dataclass(frozen=True, slots=True)
class BotFeatureDefinition:
    key: str
    dialog_id: int
    command: str
    label_key: str


BOT_FEATURES: tuple[BotFeatureDefinition, ...] = (
    BotFeatureDefinition(
        key="profile",
        dialog_id=Dialogs.PROFILE,
        command="profile",
        label_key="profile",
    ),
    BotFeatureDefinition(
        key="service",
        dialog_id=Dialogs.SERVICE,
        command="service",
        label_key="service",
    ),
    BotFeatureDefinition(
        key="poll",
        dialog_id=Dialogs.POLL,
        command="poll",
        label_key="polling",
    ),
    BotFeatureDefinition(
        key="feedback",
        dialog_id=Dialogs.FEEDBACK,
        command="feedback",
        label_key="feedback",
    ),
    BotFeatureDefinition(
        key="guest_parking",
        dialog_id=Dialogs.GUEST_PARKING,
        command="guest_parking",
        label_key="guest_parking",
    ),
    BotFeatureDefinition(
        key="spaces",
        dialog_id=Dialogs.SPACES,
        command="spaces",
        label_key="spaces",
    ),
)

BOT_FEATURES_BY_KEY = {feature.key: feature for feature in BOT_FEATURES}
BOT_FEATURES_BY_DIALOG = {feature.dialog_id: feature for feature in BOT_FEATURES}

DEFAULT_MENU_LAYOUT: tuple[tuple[str, ...], ...] = (
    ("profile", "service"),
    ("poll", "feedback"),
    ("guest_parking", "spaces"),
)

LIMITED_MENU_LAYOUT: tuple[tuple[str, ...], ...] = (
    ("profile", "service"),
    ("guest_parking", "spaces"),
)

DEFAULT_BOT_SETTINGS = {
    "features": {
        feature.key: {
            "enabled": True,
        }
        for feature in BOT_FEATURES
    }
}
