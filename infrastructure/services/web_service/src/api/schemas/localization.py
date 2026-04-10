from typing import Dict

from pydantic import RootModel


class LocalizationDocument(RootModel[Dict[str, Dict[str, str]]]):
    """Full localization payload mirrored from bot_service JSON."""

