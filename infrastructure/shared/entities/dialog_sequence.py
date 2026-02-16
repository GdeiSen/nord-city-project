class Sequence:
    def __init__(self, id: int, items_ids: list[int], next_sequence_id: int | None = None, dialog_id: int | None = None):
        self.id = id
        self.dialog_id : int | None = dialog_id
        self.items_ids : list[int] = items_ids
        self.next_sequence_id : int | None = next_sequence_id
