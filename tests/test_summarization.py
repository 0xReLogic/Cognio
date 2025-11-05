"""Unit tests for the summarization module."""

from src.summarization import summarize


def test_summarize_short_text() -> None:
    """Test summarization of short text."""
    text = "This is a short text. It has only two sentences."
    summary = summarize(text)
    assert summary == text


def test_summarize_long_text() -> None:
    """Test summarization of long text."""
    text = (
        "This is a long text. It has many sentences. "
        "The summarization algorithm should pick the most important ones. "
        "The summary should be shorter than the original text. "
        "This is the fifth sentence. "
        "This is the sixth sentence. "
        "This is the seventh sentence. "
        "This is the eighth sentence. "
        "This is the ninth sentence. "
        "This is the tenth sentence."
    )
    summary = summarize(text)
    assert len(summary) < len(text)
    assert len(summary.split(". ")) <= 3
