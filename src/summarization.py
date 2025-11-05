"""Extractive summarization using sentence-transformers."""

import re
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics import pairwise_distances_argmin_min


# Initialize the sentence transformer model
model = SentenceTransformer("all-MiniLM-L6-v2")

# In-memory cache for summaries
summary_cache = {}


def summarize(text: str, num_sentences: int = 3) -> str:
    """
    Generate an extractive summary of the given text.

    Args:
        text: The text to summarize.
        num_sentences: The desired number of sentences in the summary.

    Returns:
        The generated summary.
    """
    # Check if summary is already cached
    if text in summary_cache:
        return summary_cache[text]

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

    # Cache the summary
    summary_cache[text] = summary

    return summary
