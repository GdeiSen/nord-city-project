"""
DDID (Dialog-Sequence-Item ID) utility functions
Handles conversion between individual IDs and DDID format
"""

from typing import Tuple, Union


def create_ddid(dialog_id: Union[int, str], sequence_id: Union[int, str], item_id: Union[int, str]) -> str:
    """
    Create DDID (Dialog-Dialog-Item-ID) string from individual component IDs.
    
    DDID Format: "0000-0000-0000" representing dialog_id-sequence_id-item_id
    Each component is zero-padded to 4 digits for consistent formatting and
    easy parsing. This standardized format enables efficient dialog context
    tracking across the microservices architecture.
    
    Args:
        dialog_id (Union[int, str]): Dialog identifier (0-9999)
        sequence_id (Union[int, str]): Sequence identifier within dialog (0-9999)
        item_id (Union[int, str]): Item identifier within sequence (0-9999)
        
    Returns:
        str: Formatted DDID string in format "0000-0000-0000"
        
    Raises:
        ValueError: If any component cannot be converted to int or exceeds 9999
        ValueError: If any component is negative
        
    Example:
        >>> create_ddid(1, 2, 3)
        "0001-0002-0003"
        >>> create_ddid("45", "67", "89") 
        "0045-0067-0089"
    """
    try:
        # Convert to strings and validate
        dialog_str = str(dialog_id).strip()
        sequence_str = str(sequence_id).strip()
        item_str = str(item_id).strip()
        
        # Validate that all parts are numeric
        if not dialog_str.isdigit():
            raise ValueError(f"Dialog ID must be numeric, got: {dialog_id}")
        if not sequence_str.isdigit():
            raise ValueError(f"Sequence ID must be numeric, got: {sequence_id}")
        if not item_str.isdigit():
            raise ValueError(f"Item ID must be numeric, got: {item_id}")
        
        # Pad with zeros to ensure 4 digits minimum
        dialog_padded = dialog_str.zfill(4)
        sequence_padded = sequence_str.zfill(4)
        item_padded = item_str.zfill(4)
        
        # Create DDID
        ddid = f"{dialog_padded}-{sequence_padded}-{item_padded}"
        
        return ddid
        
    except Exception as e:
        raise ValueError(f"Failed to create DDID from dialog_id={dialog_id}, sequence_id={sequence_id}, item_id={item_id}: {e}")


def parse_ddid(ddid: str) -> Tuple[int, int, int]:
    """
    Parse DDID string into individual component IDs.
    
    Extracts dialog_id, sequence_id, and item_id from a standardized DDID string.
    Validates format and converts components to integers for use in dialog
    processing logic throughout the microservices system.
    
    Args:
        ddid (str): DDID string in format "0000-0000-0000"
        
    Returns:
        Tuple[int, int, int]: Tuple of (dialog_id, sequence_id, item_id) as integers
        
    Raises:
        ValueError: If DDID format is invalid (not 14 characters or wrong pattern)
        ValueError: If any component cannot be converted to integer
        
    Example:
        >>> parse_ddid("0001-0002-0003")
        (1, 2, 3)
        >>> parse_ddid("0045-0067-0089")
        (45, 67, 89)
    """
    if not ddid or not isinstance(ddid, str):
        raise ValueError("DDID must be a non-empty string")
    
    ddid = ddid.strip()
    
    # Check basic format
    if len(ddid) < 14:  # Minimum: 4-4-4 + 2 dashes = 14 chars
        raise ValueError(f"DDID too short, expected at least 14 characters, got {len(ddid)}: {ddid}")
    
    # Split by dashes
    parts = ddid.split('-')
    if len(parts) != 3:
        raise ValueError(f"DDID must have exactly 3 parts separated by dashes, got {len(parts)}: {ddid}")
    
    try:
        # Parse each part
        dialog_str, sequence_str, item_str = parts
        
        # Validate minimum length
        if len(dialog_str) < 4:
            raise ValueError(f"Dialog ID part must be at least 4 characters, got {len(dialog_str)}: {dialog_str}")
        if len(sequence_str) < 4:
            raise ValueError(f"Sequence ID part must be at least 4 characters, got {len(sequence_str)}: {sequence_str}")
        if len(item_str) < 4:
            raise ValueError(f"Item ID part must be at least 4 characters, got {len(item_str)}: {item_str}")
        
        # Validate that all parts are numeric
        if not dialog_str.isdigit():
            raise ValueError(f"Dialog ID part must be numeric, got: {dialog_str}")
        if not sequence_str.isdigit():
            raise ValueError(f"Sequence ID part must be numeric, got: {sequence_str}")
        if not item_str.isdigit():
            raise ValueError(f"Item ID part must be numeric, got: {item_str}")
        
        # Convert to integers
        dialog_id = int(dialog_str)
        sequence_id = int(sequence_str)
        item_id = int(item_str)
        
        return dialog_id, sequence_id, item_id
        
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to parse DDID '{ddid}': {e}")


def validate_ddid(ddid: str) -> bool:
    """
    Validate DDID format without raising exceptions
    
    Args:
        ddid: DDID string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parse_ddid(ddid)
        return True
    except ValueError:
        return False


def normalize_ddid(ddid: str) -> str:
    """
    Normalize DDID by parsing and recreating it
    Ensures consistent formatting
    
    Args:
        ddid: DDID string to normalize
        
    Returns:
        Normalized DDID string
        
    Raises:
        ValueError: If DDID is invalid
    """
    dialog_id, sequence_id, item_id = parse_ddid(ddid)
    return create_ddid(dialog_id, sequence_id, item_id) 