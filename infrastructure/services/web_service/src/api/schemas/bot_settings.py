from typing import Dict

from pydantic import BaseModel


class BotFeatureToggle(BaseModel):
    enabled: bool


class BotSettingsDocument(BaseModel):
    features: Dict[str, BotFeatureToggle]
