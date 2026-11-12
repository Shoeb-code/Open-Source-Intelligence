import re
import hashlib
from typing import Optional

def clean_text(text: Optional[str]) -> str:
    """Removes excessive whitespace, zero-width noise, and control characters, and normalizes text."""
    if not text:
        return ""
    # Remove zero-width / soft-hyphen / BOM artifacts
    text = re.sub(r'[\u200b-\u200d\ufeff\u00ad]+', '', text)
    # Normalize unicode spaces & line breaks
    text = re.sub(r'[\r\t\f\v]+', ' ', text)
    # Condense consecutive newlines and spaces
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def compute_content_hash(text: str) -> str:
    """Generates a SHA-256 hash for deduplication and content versioning."""
    normalized = clean_text(text).lower()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def truncate_text(text: str, max_chars: int = 1500) -> str:
    """Safely truncates text to a specified character limit."""
    if not text or len(text) <= max_chars:
        return text or ""
    return text[:max_chars] + "... [truncated]"

