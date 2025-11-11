"""Embedding generation for semantic search."""

import logging
import pickle
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from .config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self) -> None:
        """Initialize the embedding model."""
        self.model_name = settings.embed_model
        self.device = settings.embed_device
        self.model: SentenceTransformer | None = None
        self.embedding_dim = 768  # Multilingual mpnet uses 768 dimensions
        self.cache: dict[str, list[float]] = {}
        self.cache_dirty = False  # Track if cache has unsaved changes
        self.load_cache()

    def load_cache(self) -> None:
        """Load the embedding cache from disk."""
        cache_path = Path(settings.embedding_cache_path)
        if cache_path.exists():
            with open(cache_path, "rb") as f:
                self.cache = pickle.load(f)
            logger.info(f"Loaded {len(self.cache)} embeddings from cache.")

    def save_cache(self) -> None:
        """Save the embedding cache to disk."""
        if not self.cache_dirty:
            logger.info("Cache not modified, skipping save")
            return

        cache_path = Path(settings.embedding_cache_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "wb") as f:
            pickle.dump(self.cache, f)
        self.cache_dirty = False
        logger.info(f"Saved {len(self.cache)} embeddings to cache.")

    def load_model(self) -> None:
        """Load the sentence-transformer model."""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name, device=self.device)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")

    def encode(self, text: str, text_hash: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to encode
            text_hash: The SHA256 hash of the text.

        Returns:
            List of floats representing the embedding vector
        """
        # Check if the embedding is in the cache
        if text_hash in self.cache:
            return self.cache[text_hash]

        if self.model is None:
            self.load_model()

        assert self.model is not None
        embedding = self.model.encode(text, convert_to_numpy=True)
        embedding_list = embedding.tolist()

        # Add the new embedding to the cache
        self.cache[text_hash] = embedding_list
        self.cache_dirty = True

        return embedding_list

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts to encode

        Returns:
            List of embedding vectors
        """
        if self.model is None:
            self.load_model()

        assert self.model is not None
        embeddings = self.model.encode(
            texts, batch_size=settings.batch_size, convert_to_numpy=True, show_progress_bar=False
        )
        return embeddings.tolist()

    def cosine_similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between 0.0 and 1.0
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        if vec1.shape != vec2.shape:
            return 0.0

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)


# Global embedding service instance
embedding_service = EmbeddingService()
