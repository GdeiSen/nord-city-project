class Item:
    def __init__(self, id: int, text: str, dialog_id: int | None = None, options_ids: list[int] | None = None, type: int | None = -1, images: list[str] | None = None):
        self.id = id
        self.text = text
        self.type = type
        self.options_ids : list[int] | None = options_ids
        self.dialog_id : int | None = dialog_id
        self.images : list[str] | None = images
