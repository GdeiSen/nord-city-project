from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import datetime
    
class Answer:
    def __init__(self, id: int, user_id: int, dialog_id: int, sequence_id: int, item_id: int, answer: str, created_at: "datetime" = None, updated_at: "datetime" = None):
        self.id = id
        self.user_id = user_id
        self.dialog_id = dialog_id
        self.item_id = item_id
        self.sequence_id = sequence_id
        self.answer = answer
        self.created_at = created_at
        self.updated_at = updated_at
