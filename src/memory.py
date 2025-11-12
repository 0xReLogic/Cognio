"""Core memory operations for Cognio."""

import logging
import uuid
from datetime import datetime
from typing import Any

import numpy as np

from .autotag import generate_tags
from .config import settings
from .database import db
from .embeddings import embedding_service
from .models import Memory, MemoryResult, SaveMemoryRequest
from .summarization import summarize
from .utils import format_timestamp, generate_text_hash, get_timestamp

logger = logging.getLogger(__name__)

# Constants
_TIMEZONE_OFFSET = "+00:00"


class MemoryService:
    """Service for managing memories."""

    def __init__(self) -> None:
        """Initialize memory service."""
        pass

    def save_memory(self, request: SaveMemoryRequest) -> tuple[str, bool, str]:
        """
        Save a new memory.

        Args:
            request: Save memory request

        Returns:
            Tuple of (memory_id, is_duplicate, reason)
        """
        # Validate text length
        if len(request.text) > settings.max_text_length:
            raise ValueError(f"Text exceeds maximum length of {settings.max_text_length}")

        # Generate text hash for deduplication
        text_hash = generate_text_hash(request.text)

        # Check for duplicates
        existing = db.get_memory_by_hash(text_hash)
        if existing:
            logger.info(f"Duplicate memory found: {existing.id}")
            return existing.id, True, "duplicate"

        # Generate embedding
        embedding = embedding_service.encode(request.text, text_hash)

        # Generate summary if text is long enough
        summary = None
        if len(request.text.split()) > settings.summarize_threshold:
            summary = summarize(request.text)

        # Auto-generate tags if none are provided
        tags = request.tags
        if not tags and settings.autotag_enabled:
            autotag_result = generate_tags(request.text)
            if autotag_result["tags"]:
                tags.extend(autotag_result["tags"])
            if autotag_result["category"]:
                tags.append(autotag_result["category"])

        # Create memory object
        memory_id = str(uuid.uuid4())
        timestamp = get_timestamp()

        memory = Memory(
            id=memory_id,
            text=request.text,
            summary=summary,
            text_hash=text_hash,
            embedding=embedding,
            project=request.project,
            tags=tags,
            created_at=timestamp,
            updated_at=timestamp,
        )

        # Save to database
        db.save_memory(memory)
        logger.info(f"Memory saved: {memory_id}")

        return memory_id, False, "created"

    def search_memory(
        self,
        query: str,
        project: str | None = None,
        tags: list[str] | None = None,
        limit: int = 5,
        threshold: float | None = None,
        after_date: str | None = None,
        before_date: str | None = None,
    ) -> list[MemoryResult]:
        """
        Search memories using semantic similarity.

        Args:
            query: Search query text
            project: Optional project filter
            tags: Optional tags filter
            limit: Maximum number of results
            threshold: Minimum similarity score (defaults to settings.similarity_threshold)
            after_date: Filter memories after this date (ISO 8601)
            before_date: Filter memories before this date (ISO 8601)

        Returns:
            List of matching memories with scores
        """
        # Use default threshold from settings if not provided
        if threshold is None:
            threshold = settings.similarity_threshold
        query_hash = generate_text_hash(query)
        query_embedding = embedding_service.encode(query, query_hash)

        # If hybrid is enabled and FTS is ready, try hybrid path first
        if getattr(settings, "hybrid_enabled", False) and db.has_fts():
            alpha = float(getattr(settings, "hybrid_alpha", 0.6))
            # 1) Get FTS candidates (id, bm25 rank), lower rank is better
            candidates = db.fts_search_candidates(query=query, project=project, limit=100)

            # 2) Load memories and apply additional filters (tags, date range)
            all_memories = db.get_all_memories()
            mem_by_id = {m.id: m for m in all_memories}
            selected: list[tuple[Memory, float]] = []
            for mid, rank in candidates:
                m = mem_by_id.get(mid)
                if not m:
                    continue
                # Tags filter
                if tags and not any(t in m.tags for t in tags):
                    continue
                # Date filters
                ok = True
                if after_date:
                    try:
                        after_ts = int(
                            datetime.fromisoformat(
                                after_date.replace("Z", _TIMEZONE_OFFSET)
                            ).timestamp()
                        )
                        if m.created_at < after_ts:
                            ok = False
                    except ValueError:
                        pass
                if ok and before_date:
                    try:
                        before_ts = int(
                            datetime.fromisoformat(
                                before_date.replace("Z", _TIMEZONE_OFFSET)
                            ).timestamp()
                        )
                        if m.created_at > before_ts:
                            ok = False
                    except ValueError:
                        pass
                if ok:
                    selected.append((m, rank))

            # If no FTS candidates passed filters, try LIKE fallback; if still none, fallback semantic-only
            if not selected:
                like_ids: list[str] = []
                if not candidates:
                    like_ids = db.like_search_candidates(query=query, project=project, limit=100)
                if like_ids:
                    for mid in like_ids:
                        m = mem_by_id.get(mid)
                        if not m:
                            continue
                        if tags and not any(t in m.tags for t in tags):
                            continue
                        # Date filters
                        ok2 = True
                        if after_date:
                            try:
                                after_ts = int(
                                    datetime.fromisoformat(
                                        after_date.replace("Z", _TIMEZONE_OFFSET)
                                    ).timestamp()
                                )
                                if m.created_at < after_ts:
                                    ok2 = False
                            except ValueError:
                                pass
                        if ok2 and before_date:
                            try:
                                before_ts = int(
                                    datetime.fromisoformat(
                                        before_date.replace("Z", _TIMEZONE_OFFSET)
                                    ).timestamp()
                                )
                                if m.created_at > before_ts:
                                    ok2 = False
                            except ValueError:
                                pass
                        if ok2:
                            # Use rank=0.0 so bm25_norm becomes 1.0 after normalization
                            selected.append((m, 0.0))

            if not selected:
                # Fallback semantic-only path (original)
                emb_dim = embedding_service.embedding_dim
                base_memories = db.get_all_memories()
                if project:
                    base_memories = [m for m in base_memories if m.project == project]
                if tags:
                    base_memories = [m for m in base_memories if any(tag in m.tags for tag in tags)]
                if after_date:
                    try:
                        after_ts = int(
                            datetime.fromisoformat(
                                after_date.replace("Z", _TIMEZONE_OFFSET)
                            ).timestamp()
                        )
                        base_memories = [m for m in base_memories if m.created_at >= after_ts]
                    except ValueError:
                        pass
                if before_date:
                    try:
                        before_ts = int(
                            datetime.fromisoformat(
                                before_date.replace("Z", _TIMEZONE_OFFSET)
                            ).timestamp()
                        )
                        base_memories = [m for m in base_memories if m.created_at <= before_ts]
                    except ValueError:
                        pass

                mems_with_emb = [
                    m
                    for m in base_memories
                    if (m.embedding is not None and len(m.embedding) == emb_dim)
                ]
                if not mems_with_emb:
                    return []
                m_arr = np.asarray([m.embedding for m in mems_with_emb], dtype=np.float32)
                q = np.asarray(query_embedding, dtype=np.float32)
                q_norm = q / (np.linalg.norm(q) + 1e-12)
                m_norm = m_arr / (np.linalg.norm(m_arr, axis=1, keepdims=True) + 1e-12)
                scores = m_norm @ q_norm
                # Threshold filtering (semantic)
                thr = (
                    float(threshold)
                    if threshold is not None
                    else float(settings.similarity_threshold)
                )
                idxs = np.where(scores >= thr)[0]
                pairs = [(mems_with_emb[i], float(scores[i])) for i in idxs]
                pairs.sort(key=lambda x: x[1], reverse=True)
                topk = pairs[:limit]
                return [
                    MemoryResult(
                        id=memory.id,
                        text=memory.text,
                        summary=memory.summary,
                        score=round(score, 4),
                        project=memory.project,
                        tags=memory.tags,
                        created_at=format_timestamp(memory.created_at),
                    )
                    for memory, score in topk
                ]

            # 3) Semantic scores only on selected candidates
            emb_dim = embedding_service.embedding_dim
            cand_mems = [
                m
                for (m, _) in selected
                if (m.embedding is not None and len(m.embedding) == emb_dim)
            ]
            if not cand_mems:
                return []
            m_arr = np.asarray([m.embedding for m in cand_mems], dtype=np.float32)
            q = np.asarray(query_embedding, dtype=np.float32)
            q_norm = q / (np.linalg.norm(q) + 1e-12)
            m_norm = m_arr / (np.linalg.norm(m_arr, axis=1, keepdims=True) + 1e-12)
            sem_scores = m_norm @ q_norm  # higher is better

            # 4) Normalize semantic scores to [0,1]
            sem_min = float(np.min(sem_scores)) if sem_scores.size else 0.0
            sem_max = float(np.max(sem_scores)) if sem_scores.size else 1.0
            sem_range = sem_max - sem_min
            if sem_scores.size == 1 or abs(sem_range) < 1e-12:
                sem_norm = np.ones_like(sem_scores, dtype=np.float32)
            else:
                sem_norm = (sem_scores - sem_min) / (sem_range + 1e-12)

            # 5) Convert BM25 ranks to scores and normalize to [0,1]
            bm25_ranks = np.asarray([rank for (_, rank) in selected], dtype=np.float32)
            bm25_inv = 1.0 / (1.0 + bm25_ranks)  # higher is better
            bm_min = float(np.min(bm25_inv)) if bm25_inv.size else 0.0
            bm_max = float(np.max(bm25_inv)) if bm25_inv.size else 1.0
            bm_range = bm_max - bm_min
            if bm25_inv.size == 1 or abs(bm_range) < 1e-12:
                bm_norm = np.ones_like(bm25_inv, dtype=np.float32)
            else:
                bm_norm = (bm25_inv - bm_min) / (bm_range + 1e-12)

            # 6) Combine
            combined = alpha * sem_norm + (1.0 - alpha) * bm_norm

            # 7) Apply threshold if provided (on combined)
            thr = (
                float(threshold) if threshold is not None else float(settings.similarity_threshold)
            )
            mask = combined >= thr
            idxs = np.where(mask)[0]
            pairs = [(cand_mems[i], float(combined[i])) for i in idxs]
            pairs.sort(key=lambda x: x[1], reverse=True)
            topk = pairs[:limit]

            return [
                MemoryResult(
                    id=memory.id,
                    text=memory.text,
                    summary=memory.summary,
                    score=round(score, 4),
                    project=memory.project,
                    tags=memory.tags,
                    created_at=format_timestamp(memory.created_at),
                )
                for memory, score in topk
            ]

        # Semantic-only path (original)
        all_memories = db.get_all_memories()
        if project:
            all_memories = [m for m in all_memories if m.project == project]
        if tags:
            all_memories = [m for m in all_memories if any(tag in m.tags for tag in tags)]
        if after_date:
            try:
                after_ts = int(
                    datetime.fromisoformat(after_date.replace("Z", _TIMEZONE_OFFSET)).timestamp()
                )
                all_memories = [m for m in all_memories if m.created_at >= after_ts]
            except ValueError:
                pass
        if before_date:
            try:
                before_ts = int(
                    datetime.fromisoformat(before_date.replace("Z", _TIMEZONE_OFFSET)).timestamp()
                )
                all_memories = [m for m in all_memories if m.created_at <= before_ts]
            except ValueError:
                pass

        emb_dim = embedding_service.embedding_dim
        mems_with_emb = [
            m for m in all_memories if (m.embedding is not None and len(m.embedding) == emb_dim)
        ]
        if not mems_with_emb:
            return []
        m_arr = np.asarray([m.embedding for m in mems_with_emb], dtype=np.float32)
        q = np.asarray(query_embedding, dtype=np.float32)
        q_norm = q / (np.linalg.norm(q) + 1e-12)
        m_norm = m_arr / (np.linalg.norm(m_arr, axis=1, keepdims=True) + 1e-12)
        scores = m_norm @ q_norm

        thr = float(threshold) if threshold is not None else float(settings.similarity_threshold)
        idxs = np.where(scores >= thr)[0]
        pairs = [(mems_with_emb[i], float(scores[i])) for i in idxs]
        pairs.sort(key=lambda x: x[1], reverse=True)
        topk = pairs[:limit]
        return [
            MemoryResult(
                id=memory.id,
                text=memory.text,
                summary=memory.summary,
                score=round(score, 4),
                project=memory.project,
                tags=memory.tags,
                created_at=format_timestamp(memory.created_at),
            )
            for memory, score in topk
        ]

    def list_memories(
        self,
        project: str | None = None,
        tags: list[str] | None = None,
        page: int = 1,
        limit: int = 20,
        sort: str = "date",
        search_query: str | None = None,
    ) -> tuple[list[MemoryResult], int]:
        """
        List memories with pagination.

        Args:
            project: Optional project filter
            tags: Optional tags filter
            page: Page number (1-indexed)
            limit: Items per page
            sort: Sort order (date or relevance)
            search_query: Query for relevance sorting

        Returns:
            Tuple of (memories, total_count)
        """
        offset = (page - 1) * limit

        # Get all memories for relevance sorting, or use database pagination for date
        if sort == "relevance" and search_query:
            all_memories = db.list_memories(project=project, tags=tags, limit=10000, offset=0)
            total_count = len(all_memories)

            # Generate query embedding and calculate scores
            query_hash = generate_text_hash(search_query)
            query_embedding = embedding_service.encode(search_query, query_hash)
            scored_memories = []

            for memory in all_memories:
                if memory.embedding:
                    score = embedding_service.cosine_similarity(query_embedding, memory.embedding)
                    scored_memories.append((memory, score))

            # Sort by relevance score
            scored_memories.sort(key=lambda x: x[1], reverse=True)

            # Paginate
            paginated = scored_memories[offset : offset + limit]

            results = [
                MemoryResult(
                    id=memory.id,
                    text=memory.text,
                    summary=memory.summary,
                    score=round(score, 4),
                    project=memory.project,
                    tags=memory.tags,
                    created_at=format_timestamp(memory.created_at),
                )
                for memory, score in paginated
            ]
        else:
            # Default: sort by date
            memories = db.list_memories(project=project, tags=tags, limit=limit, offset=offset)
            total_count = db.count_memories(project=project, tags=tags)

            results = [
                MemoryResult(
                    id=memory.id,
                    text=memory.text,
                    summary=memory.summary,
                    score=None,
                    project=memory.project,
                    tags=memory.tags,
                    created_at=format_timestamp(memory.created_at),
                )
                for memory in memories
            ]

        return results, total_count

    def reembed_mismatched(self, page_size: int = 500) -> dict[str, int]:
        scanned = 0
        reembedded = 0
        offset = 0

        while True:
            memories = db.list_memories(limit=page_size, offset=offset)
            if not memories:
                break

            scanned += len(memories)
            needs = [
                m
                for m in memories
                if (m.embedding is None) or (len(m.embedding) != embedding_service.embedding_dim)
            ]

            if needs:
                texts = [m.text for m in needs]
                embeddings = embedding_service.encode_batch(texts)
                for m, emb in zip(needs, embeddings):
                    db.update_embedding(m.id, emb)
                    reembedded += 1

            offset += page_size

        logger.info(f"Re-embed completed: scanned={scanned}, reembedded={reembedded}")
        return {"scanned": scanned, "reembedded": reembedded}

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.

        Args:
            memory_id: Memory UUID

        Returns:
            True if deleted, False if not found
        """
        deleted = db.delete_memory(memory_id)
        if deleted:
            logger.info(f"Memory deleted: {memory_id}")
        else:
            logger.warning(f"Memory not found: {memory_id}")
        return deleted

    def bulk_delete(self, project: str | None = None, before_date: str | None = None) -> int:
        """
        Bulk delete memories.

        Args:
            project: Delete by project
            before_date: Delete before date (ISO 8601)

        Returns:
            Number of deleted memories
        """
        before_timestamp = None
        if before_date:
            try:
                dt = datetime.fromisoformat(before_date.replace("Z", _TIMEZONE_OFFSET))
                before_timestamp = int(dt.timestamp())
            except ValueError as e:
                raise ValueError(f"Invalid date format: {before_date}") from e

        count = db.bulk_delete(project=project, before_timestamp=before_timestamp)
        logger.info(f"Bulk deleted {count} memories")
        return count

    def get_stats(self) -> dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Dictionary with stats
        """
        return db.get_stats()

    def export_memories(
        self, format: str = "json", project: str | None = None
    ) -> str | dict[str, Any]:
        """
        Export memories to JSON or Markdown.

        Args:
            format: Export format (json or markdown)
            project: Optional project filter

        Returns:
            Exported data as string or dict
        """
        memories = db.list_memories(project=project, limit=10000)

        if format == "json":
            return {
                "memories": [
                    {
                        "id": m.id,
                        "text": m.text,
                        "project": m.project,
                        "tags": m.tags,
                        "created_at": format_timestamp(m.created_at),
                    }
                    for m in memories
                ]
            }
        elif format == "markdown":
            lines = ["# Memory Export\n"]
            for m in memories:
                lines.append(f"## {m.id}")
                lines.append(f"**Project**: {m.project or 'None'}")
                lines.append(f"**Tags**: {', '.join(m.tags) if m.tags else 'None'}")
                lines.append(f"**Created**: {format_timestamp(m.created_at)}")
                lines.append(f"\n{m.text}\n")
                lines.append("---\n")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")


# Global memory service instance
memory_service = MemoryService()
