"""Unit tests for the auto-tagging module."""

import unittest
from unittest.mock import MagicMock, patch

from src.autotag import generate_tags
from src.config import settings


class TestAutoTag(unittest.TestCase):
    """Test suite for the auto-tagging service."""

    def setUp(self) -> None:
        """Set up test environment."""
        settings.autotag_enabled = True
        settings.llm_provider = "groq"
        settings.groq_api_key = "test-key"

    @patch("src.autotag.get_client")
    def test_generate_tags(self, mock_get_client: MagicMock) -> None:
        """Test tag generation."""
        # Mock the client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock the OpenAI API response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = '{"category": "Technology", "tags": ["AI", "LLM"]}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        # Call the function
        text = "This is a test text about AI and LLMs."
        result = generate_tags(text)

        # Assertions
        self.assertEqual(result["category"], "Technology")
        self.assertEqual(result["tags"], ["AI", "LLM"])
        mock_client.chat.completions.create.assert_called_once()
