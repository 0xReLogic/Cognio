"""Async queue for embedding generation."""

import asyncio
import logging

from .embeddings import embedding_service

logger = logging.getLogger(__name__)


class EmbeddingQueue:
    """Async queue for batching embedding generation."""

    def __init__(self, batch_size: int = 32, batch_timeout: float = 0.5):
        """
        Initialize the embedding queue.

        Args:
            batch_size: Maximum number of items in a batch
            batch_timeout: Max seconds to wait before processing incomplete batch
        """
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.queue: asyncio.Queue = asyncio.Queue()
        self.processing = False

    async def add_task(self, text: str, text_hash: str) -> list[float]:
        """
        Add embedding generation task to queue.

        Args:
            text: Text to embed
            text_hash: Hash of the text

        Returns:
            Generated embedding
        """
        # Check cache first
        if text_hash in embedding_service.cache:
            return embedding_service.cache[text_hash]

        # Create future for this task
        future: asyncio.Future = asyncio.Future()
        await self.queue.put((text, text_hash, future))

        # Start processing if not already running
        if not self.processing:
            asyncio.create_task(self._process_queue())

        # Wait for result
        return await future

    async def _process_queue(self) -> None:
        """Process queue in batches."""
        if self.processing:
            return

        self.processing = True

        try:
            while not self.queue.empty():
                batch = []
                futures = []

                # Collect batch
                try:
                    while len(batch) < self.batch_size:
                        text, text_hash, future = await asyncio.wait_for(
                            self.queue.get(), timeout=self.batch_timeout
                        )
                        batch.append((text, text_hash))
                        futures.append(future)
                except TimeoutError:
                    # Process what we have
                    pass

                if not batch:
                    break

                # Generate embeddings in batch
                try:
                    texts = [item[0] for item in batch]
                    hashes = [item[1] for item in batch]

                    # Run embedding generation in thread pool
                    loop = asyncio.get_event_loop()
                    embeddings = await loop.run_in_executor(
                        None, embedding_service.encode_batch, texts
                    )

                    # Update cache
                    for text_hash, embedding in zip(hashes, embeddings):
                        embedding_service.cache[text_hash] = embedding

                    # Resolve futures
                    for future, embedding in zip(futures, embeddings):
                        future.set_result(embedding)

                    logger.info(f"Processed batch of {len(batch)} embeddings")

                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    # Reject all futures in batch
                    for future in futures:
                        if not future.done():
                            future.set_exception(e)

        finally:
            self.processing = False


# Global queue instance
embedding_queue = EmbeddingQueue()
