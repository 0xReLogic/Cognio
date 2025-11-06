"""Automatic tagging service using LLM APIs (Groq, OpenAI)."""

import json
import logging
from typing import Any

from groq import Groq
from openai import OpenAI

try:
    from .config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)

# System prompt for tag extraction
SYSTEM_PROMPT = """
You are a helpful assistant that analyzes text and extracts relevant information.
Your task is to identify a single, overarching category and a list of specific tags from the user's text.
You will reply only with a valid JSON object, and no other descriptive or explanatory text.
The JSON object should have two keys: "category" (a string) and "tags" (a list of strings).

Examples:
- For technical documentation: {"category": "Programming", "tags": ["python", "fastapi", "api"]}
- For research notes: {"category": "Research", "tags": ["machine-learning", "nlp", "transformers"]}
- For personal thoughts: {"category": "Personal", "tags": ["reflection", "goals", "productivity"]}
"""


client = None


def get_client() -> Groq | OpenAI:
    """Get the LLM client based on configured provider."""
    global client
    if client is None:
        if settings.llm_provider == "groq":
            if not settings.groq_api_key:
                raise ValueError("Groq API key not configured")
            client = Groq(api_key=settings.groq_api_key)
        elif settings.llm_provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            client = OpenAI(api_key=settings.openai_api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
    return client


def generate_tags(text: str) -> dict[str, Any]:
    """
    Generate tags for the given text using configured LLM API.

    Args:
        text: The text to generate tags for.

    Returns:
        A dictionary with "category" and "tags".
    """
    if not settings.autotag_enabled:
        return {"category": None, "tags": []}

    # Check API key based on provider
    if settings.llm_provider == "groq" and not settings.groq_api_key:
        logger.warning("Auto-tagging enabled but Groq API key not configured")
        return {"category": None, "tags": []}
    elif settings.llm_provider == "openai" and not settings.openai_api_key:
        logger.warning("Auto-tagging enabled but OpenAI API key not configured")
        return {"category": None, "tags": []}

    try:
        client = get_client()
        model = settings.groq_model if settings.llm_provider == "groq" else settings.openai_model

        # Truncate text if too long (max 8000 chars for safety)
        text_to_analyze = text[:8000] if len(text) > 8000 else text

        # Build kwargs based on provider
        create_kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Please analyze the following text and extract a category and tags in JSON format:\n\n{text_to_analyze}",
                },
            ],
            "temperature": 0,
        }

        # Only add response_format for OpenAI
        if settings.llm_provider == "openai":
            create_kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**create_kwargs)

        if response.choices:
            content = response.choices[0].message.content
            if content:
                # Try to parse JSON response
                try:
                    result = json.loads(content)
                    # Validate structure
                    if "category" in result and "tags" in result:
                        return result
                    else:
                        logger.warning(f"Invalid tag structure: {result}")
                        return {"category": None, "tags": []}
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON response: {content}")
                    return {"category": None, "tags": []}
    except Exception as e:
        logger.error(f"Error generating tags with {settings.llm_provider}: {e}")
        return {"category": None, "tags": []}

    return {"category": None, "tags": []}
