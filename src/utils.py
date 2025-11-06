"""Utility functions for Cognio."""

import hashlib
from datetime import UTC, datetime


def generate_text_hash(text: str) -> str:
    """Generate SHA256 hash of text for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_timestamp() -> int:
    """Get current Unix timestamp."""
    return int(datetime.now().timestamp())


def format_timestamp(timestamp: int) -> str:
    """Convert Unix timestamp to ISO 8601 string."""
    return datetime.fromtimestamp(timestamp, UTC).isoformat()
