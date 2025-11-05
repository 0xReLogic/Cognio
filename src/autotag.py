"""Automatic tagging service using OpenAI API."""

import json
import logging
from typing import Any

from openai import OpenAI

from .config import settings

logger = logging.getLogger(__name__)

# System prompt for tag extraction
SYSTEM_PROMPT = """
You are a helpful assistant that analyzes text and extracts relevant information.
Your task is to identify a single, overarching category and a list of specific tags from the user's text.
You will reply only with a valid JSON object, and no other descriptive or explanatory text.
The JSON object should have two keys: "category" (a string) and "tags" (a list of strings).
"""


client = None


def get_client() -> OpenAI:
    """Get the OpenAI client, initializing it if necessary."""
    global client
    if client is None:
        client = OpenAI(api_key=settings.openai_api_key)
    return client


def generate_tags(text: str) -> dict[str, Any]:
    """
    Generate tags for the given text using the OpenAI API.

    Args:
        text: The text to generate tags for.

    Returns:
        A dictionary with "category" and "tags".
    """
    if not settings.autotag_enabled or not settings.openai_api_key:
        return {"category": None, "tags": []}

    try:
        client = get_client()
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Please analyze the following text and extract a category and tags in JSON format:\n\n{text}",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0,
            seed=42,
        )
        if response.choices:
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
    except Exception as e:
        logger.error(f"Error generating tags: {e}")
        return {"category": None, "tags": []}

    return {"category": None, "tags": []}
