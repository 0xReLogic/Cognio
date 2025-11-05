"""Unit tests for utility functions."""

from src.utils import format_timestamp, generate_text_hash, get_timestamp


def test_generate_text_hash() -> None:
    """Test text hash generation."""
    text = "This is a test memory"
    hash1 = generate_text_hash(text)
    hash2 = generate_text_hash(text)

    # Same text should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 produces 64 character hex

    # Different text should produce different hash
    hash3 = generate_text_hash("Different text")
    assert hash1 != hash3


def test_get_timestamp() -> None:
    """Test timestamp generation."""
    ts = get_timestamp()
    assert isinstance(ts, int)
    assert ts > 0


def test_format_timestamp() -> None:
    """Test timestamp formatting."""
    ts = 1609459200  # 2021-01-01 00:00:00 UTC
    formatted = format_timestamp(ts)
    assert "2021-01-01" in formatted
    assert formatted.endswith("Z")


def test_format_timestamp_is_utc() -> None:
    """Test timestamp formatting is explicitly UTC."""
    ts = 1609459200  # 2021-01-01 00:00:00 UTC
    formatted = format_timestamp(ts)
    assert formatted == "2021-01-01T00:00:00Z"
