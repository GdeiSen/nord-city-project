class DictExtractor:
    def __init__(self, data: dict[str, dict[str, str]]):
        self.data: dict[str, dict[str, str]] = data
        self.group: str = 'RU'

    def get(self, key: str, content: list[str] | None = None, group: None | str = None) -> str | None:
        group = group or self.group

        group_data: dict[str, str] = self.data.get(group, {})

        text = group_data.get(key)

        if text is None:
            return key

        if content:
            for fill in content:
                text = text.replace('{?}', str(fill), 1)
        text = text.replace('{?}', '')
        return text
