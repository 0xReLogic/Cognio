"""Text summarization using extractive and abstractive methods."""

import logging
import re

from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances_argmin_min

try:
    from .config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)

# Initialize the sentence transformer model for extractive summarization
model = SentenceTransformer("all-MiniLM-L6-v2")

# In-memory cache for summaries
summary_cache = {}


def extractive_summarize(text: str, num_sentences: int = 3) -> str:
    """
    Generate an extractive summary of the given text using clustering.

    Args:
        text: The text to summarize.
        num_sentences: The desired number of sentences in the summary.

    Returns:
        The generated summary.
    """
    # Split the text into sentences
    sentences = re.split(r'(?<=[.?!])\s+', text)
    if len(sentences) <= num_sentences:
        return text

    # Embed the sentences
    embeddings = model.encode(sentences)

    # Cluster the sentences
    kmeans = KMeans(n_clusters=num_sentences, random_state=0)
    kmeans.fit(embeddings)

    # Find the sentences closest to the cluster centroids
    avg = []
    for j in range(num_sentences):
        idx = kmeans.labels_ == j
        avg.append(embeddings[idx].mean(axis=0))
    closest, _ = pairwise_distances_argmin_min(kmeans.cluster_centers_, embeddings)
    ordering = sorted(range(num_sentences), key=lambda k: closest[k])
    summary = " ".join([sentences[closest[idx]] for idx in ordering])

    return summary


def abstractive_summarize(text: str, max_length: int = 150) -> str:
    """
    Generate an abstractive summary using LLM API.

    Args:
        text: The text to summarize.
        max_length: Maximum length of summary in words.

    Returns:
        The generated summary.
    """
    try:
        # Import here to avoid circular dependency
        try:
            from .autotag import get_client
        except ImportError:
            from autotag import get_client

        client = get_client()
        model_name = settings.groq_model if settings.llm_provider == "groq" else settings.openai_model

        # Truncate text if too long
        text_to_summarize = text[:15000] if len(text) > 15000 else text

        prompt = f"""Please provide a concise summary of the following text in approximately {max_length} words or less.
Focus on the main ideas and key points. Write in a clear, informative style.

Text to summarize:
{text_to_summarize}

Summary:"""

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates concise, accurate summaries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=300,
        )

        if response.choices:
            summary = response.choices[0].message.content
            if summary:
                return summary.strip()

        # Fallback to extractive if LLM fails
        logger.warning("Abstractive summarization failed, falling back to extractive")
        return extractive_summarize(text)

    except Exception as e:
        logger.error(f"Error in abstractive summarization: {e}")
        # Fallback to extractive summarization
        return extractive_summarize(text)


def summarize(text: str, num_sentences: int = 3) -> str:
    """
    Generate a summary of the given text using configured method.

    Args:
        text: The text to summarize.
        num_sentences: The desired number of sentences (for extractive method).

    Returns:
        The generated summary.
    """
    # Check if summarization is enabled
    if not settings.summarization_enabled:
        return text

    # Check if summary is already cached
    cache_key = f"{settings.summarization_method}:{text[:100]}"
    if cache_key in summary_cache:
        return summary_cache[cache_key]

    # Choose summarization method
    if settings.summarization_method == "abstractive":
        # Only use abstractive if autotag is enabled (shares same LLM client)
        if settings.autotag_enabled:
            summary = abstractive_summarize(text)
        else:
            logger.warning("Abstractive summarization requires autotag_enabled=True, using extractive instead")
            summary = extractive_summarize(text, num_sentences)
    else:
        summary = extractive_summarize(text, num_sentences)

    # Cache the summary
    summary_cache[cache_key] = summary

    return summary
