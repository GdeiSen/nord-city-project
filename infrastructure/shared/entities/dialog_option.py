class Option:
    """Dialog option entity for representing user choices in dialogs"""
    
    def __init__(self, id: int, text: str = None, sequence_id: int = None, 
                 row: int = 0, callback_data: str = None):
        self.id = id
        self.text = text
        self.sequence_id = sequence_id
        self.row = row or 0
        self.callback_data = callback_data 