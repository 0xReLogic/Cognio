"""Unit tests for EmbeddingQueue behavior (fast and deterministic)."""

import asyncio

import pytest

from src.embedding_queue import EmbeddingQueue


class DummyEmbeddingService:
    def __init__(self) -> None:
        self.cache: dict[str, list[float]] = {}
        self.calls: list[list[str]] = []

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [[float(len(t)), 0.0, 0.0] for t in texts]


@pytest.mark.asyncio
async def test_add_task_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = DummyEmbeddingService()
    dummy.cache["hash-1"] = [1.0, 2.0, 3.0]
    monkeypatch.setattr("src.embedding_queue.embedding_service", dummy)

    queue = EmbeddingQueue(batch_size=2, batch_timeout=1.0)

    result = await queue.add_task("text", "hash-1")

    assert result == [1.0, 2.0, 3.0]
    assert dummy.calls == []


@pytest.mark.asyncio
async def test_process_queue_batches_and_updates_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = DummyEmbeddingService()
    monkeypatch.setattr("src.embedding_queue.embedding_service", dummy)

    queue = EmbeddingQueue(batch_size=2, batch_timeout=1.0)

    loop = asyncio.get_running_loop()
    fut1 = loop.create_future()
    fut2 = loop.create_future()

    await queue.queue.put(("one", "h1", fut1))
    await queue.queue.put(("two", "h2", fut2))

    await queue._process_queue()

    assert fut1.done() and fut2.done()
    assert fut1.result() == [3.0, 0.0, 0.0]
    assert fut2.result() == [3.0, 0.0, 0.0]
    assert "h1" in dummy.cache and "h2" in dummy.cache


@pytest.mark.asyncio
async def test_process_queue_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    class ErrorEmbeddingService:
        def __init__(self) -> None:
            self.cache: dict[str, list[float]] = {}

        def encode_batch(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
            raise RuntimeError("embedding failure")

    error_service = ErrorEmbeddingService()
    monkeypatch.setattr("src.embedding_queue.embedding_service", error_service)

    queue = EmbeddingQueue(batch_size=1, batch_timeout=1.0)

    loop = asyncio.get_running_loop()
    fut = loop.create_future()
    await queue.queue.put(("text", "hash", fut))

    await queue._process_queue()

    assert fut.done()
    with pytest.raises(RuntimeError):
        fut.result()
