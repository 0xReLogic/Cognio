"""Unit tests for embedding service."""

import pytest

from src.embeddings import EmbeddingService
from src.utils import generate_text_hash


@pytest.fixture
def embedding_service() -> EmbeddingService:
    """Create embedding service instance."""
    return EmbeddingService()


def test_encode_single_text(embedding_service: EmbeddingService) -> None:
    """Test encoding a single text."""
    text = "This is a test sentence for embedding"
    text_hash = generate_text_hash(text)
    embedding = embedding_service.encode(text, text_hash)

    assert isinstance(embedding, list)
    assert len(embedding) == 768  # paraphrase-multilingual-mpnet-base-v2
    assert all(isinstance(x, float) for x in embedding)


def test_encode_batch(embedding_service: EmbeddingService) -> None:
    """Test encoding multiple texts."""
    texts = ["First text", "Second text", "Third text"]
    embeddings = embedding_service.encode_batch(texts)

    assert len(embeddings) == 3
    assert all(len(emb) == 768 for emb in embeddings)  # paraphrase-multilingual-mpnet-base-v2


def test_cosine_similarity(embedding_service: EmbeddingService) -> None:
    """Test cosine similarity calculation."""
    text1 = "The cat sat on the mat"
    text2 = "A cat was sitting on a mat"
    text3 = "Python programming language"

    hash1 = generate_text_hash(text1)
    hash2 = generate_text_hash(text2)
    hash3 = generate_text_hash(text3)

    emb1 = embedding_service.encode(text1, hash1)
    emb2 = embedding_service.encode(text2, hash2)
    emb3 = embedding_service.encode(text3, hash3)

    # Similar sentences should have high similarity
    sim_similar = embedding_service.cosine_similarity(emb1, emb2)
    assert sim_similar > 0.7

    # Dissimilar sentences should have lower similarity
    sim_different = embedding_service.cosine_similarity(emb1, emb3)
    assert sim_different < 0.5

    # Same sentence should have similarity close to 1.0
    sim_identical = embedding_service.cosine_similarity(emb1, emb1)
    assert sim_identical > 0.99


def test_embedding_cache(embedding_service: EmbeddingService) -> None:
    """Test the embedding cache."""
    text = "This is a test sentence for the embedding cache."
    text_hash = generate_text_hash(text)

    # First call should generate and cache the embedding
    embedding1 = embedding_service.encode(text, text_hash)

    # Second call should return the cached embedding
    embedding2 = embedding_service.encode(text, text_hash)

    assert embedding1 == embedding2

    # Save and load the cache
    embedding_service.save_cache()
    embedding_service.load_cache()

    # Third call should still return the cached embedding
    embedding3 = embedding_service.encode(text, text_hash)

    assert embedding1 == embedding3
