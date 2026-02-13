from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shared.entities.dialog_sequence import Sequence
    from shared.entities.dialog_item import Item
    from shared.entities.dialog_link import Link
    from shared.entities.dialog_option import Option

class Dialog:
    def __init__(self, id: int, sequences: dict[int,"Sequence"] = None, items:dict[int,"Item"] = None, 
                 links:dict[int,"Link"] = None, options:dict[int,"Option"] = None, trace:bool = False):
        """
        Initialize Dialog with sequences, items, links/options and trace flag.
        
        Args:
            id: Dialog identifier
            sequences: Dictionary of dialog sequences
            items: Dictionary of dialog items
            links: Dictionary of dialog links (legacy)
            options: Dictionary of dialog options (preferred)
            trace: Whether to enable tracing
        """
        self.id = id
        self.sequences : dict[int,"Sequence"] = sequences or {}
        self.items : dict[int,"Item"] = items or {}
        self.links : dict[int,"Link"] = links or {}
        # Support both 'options' and 'links' for backward compatibility
        self.options : dict[int,"Option"] = options or {}
        self.trace = trace
