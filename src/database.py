"""Database management for Cognio."""

import hashlib
import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

from .config import settings
from .engram import engram_index
from .models import Memory
from .utils import get_timestamp

logger = logging.getLogger(__name__)

# Constants
_DB_NOT_CONNECTED_ERROR = "Database not connected"
_PROJECT_FILTER_SQL = " AND project = ?"
_TAGS_LIKE_SQL = "tags LIKE ?"
_LEANN_GLOBAL_KEY = "__global__"
_LEANN_PROJECT_MAX_LEN = 64


class Database:
    """SQLite database manager for memories."""

    def __init__(self, db_path: str | None = None) -> None:
        """Initialize database connection."""
        self.db_path = db_path or settings.db_path
        self.conn: sqlite3.Connection | None = None
        self.fts_ready: bool = False
        self.leann_engines: dict[str, Any] = {}
        self.leann_dirty_projects: set[str] = set()

    def connect(self) -> None:
        """Create database connection and initialize schema."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        logger.info(f"Connected to database: {self.db_path}")

        # Initialize schema
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        if self.conn is None:
            raise RuntimeError(_DB_NOT_CONNECTED_ERROR)

        cursor = self.conn.cursor()

        # Main memories table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                text_hash TEXT,
                embedding BLOB,
                project TEXT,
                tags TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                archived INTEGER DEFAULT 0
            )
        """
        )

        # Indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project ON memories(project)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON memories(text_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_archived ON memories(archived)")

        # Initialize FTS5 (best-effort)
        try:
            # Virtual table for keyword search
            cursor.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    id UNINDEXED,
                    text,
                    project,
                    tags
                )
                """
            )

            # Triggers to synchronize FTS index
            cursor.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_memories_ai_fts
                AFTER INSERT ON memories BEGIN
                  INSERT INTO memories_fts (id, text, project, tags)
                  SELECT NEW.id, NEW.text, NEW.project, NEW.tags
                  WHERE NEW.archived = 0;
                END;
                """
            )
            cursor.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_memories_au_fts
                AFTER UPDATE ON memories BEGIN
                  DELETE FROM memories_fts WHERE id = OLD.id;
                  INSERT INTO memories_fts (id, text, project, tags)
                  SELECT NEW.id, NEW.text, NEW.project, NEW.tags
                  WHERE NEW.archived = 0;
                END;
                """
            )
            cursor.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_memories_ad_fts
                AFTER DELETE ON memories BEGIN
                  DELETE FROM memories_fts WHERE id = OLD.id;
                END;
                """
            )

            # Backfill missing FTS rows
            cursor.execute(
                """
                INSERT INTO memories_fts (id, text, project, tags)
                SELECT m.id, m.text, m.project, m.tags
                FROM memories m
                LEFT JOIN memories_fts f ON f.id = m.id
                WHERE f.id IS NULL AND m.archived = 0
                """
            )

            self.fts_ready = True
        except sqlite3.OperationalError as e:
            # FTS5 not available in this SQLite build
            logger.warning(f"FTS5 not available or initialization failed: {e}")
            self.fts_ready = False

        # Engram hashed n-gram index (best-effort)
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS engram_index (
                    bucket INTEGER NOT NULL,
                    memory_id TEXT NOT NULL,
                    hits INTEGER NOT NULL,
                    PRIMARY KEY (bucket, memory_id)
                )
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_engram_bucket ON engram_index(bucket)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_engram_memory ON engram_index(memory_id)"
            )
        except sqlite3.OperationalError as e:
            logger.warning(f"Engram index init failed: {e}")

        self.conn.commit()
        logger.info("Database schema initialized")

    def has_fts(self) -> bool:
        """Return whether FTS is ready for use."""
        return self.fts_ready

    def backfill_engram_index(self) -> None:
        """Backfill Engram index for existing memories if empty."""
        if not settings.engram_enabled:
            return
        if self.conn is None:
            raise RuntimeError(_DB_NOT_CONNECTED_ERROR)

        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) AS count FROM engram_index")
            count = cursor.fetchone()["count"]
        except sqlite3.OperationalError as e:
            logger.warning(f"Engram backfill skipped: {e}")
            return

        if count and count > 0:
            return

        logger.info("Engram backfill: rebuilding index for existing memories...")
        cursor.execute("SELECT id, text FROM memories WHERE archived = 0")
        rows = cursor.fetchall()
        for row in rows:
            memory_id = row["id"]
            text = row["text"] or ""
            bucket_counts = engram_index.bucket_counts(text)
            for bucket, hits in bucket_counts.items():
                cursor.execute(
                    """
                    INSERT INTO engram_index (bucket, memory_id, hits)
                    VALUES (?, ?, ?)
                    ON CONFLICT(bucket, memory_id) DO UPDATE SET hits = excluded.hits
                    """,
                    (int(bucket), memory_id, int(hits)),
                )
        self.conn.commit()
        logger.info("Engram backfill: complete (entries=%s)", len(rows))

    def upsert_engram_index(self, memory_id: str, text: str) -> None:
        """Upsert Engram hashed n-gram buckets for a memory."""
        if not settings.engram_enabled or not text:
            return
        if self.conn is None:
            raise RuntimeError(_DB_NOT_CONNECTED_ERROR)

        bucket_counts = engram_index.bucket_counts(text)
        if not bucket_counts:
            return

        cursor = self.conn.cursor()
        for bucket, hits in bucket_counts.items():
            cursor.execute(
                """
                INSERT INTO engram_index (bucket, memory_id, hits)
                VALUES (?, ?, ?)
                ON CONFLICT(bucket, memory_id) DO UPDATE SET hits = excluded.hits
                """,
                (int(bucket), memory_id, int(hits)),
            )
        self.conn.commit()

    def delete_engram_for_ids(self, memory_ids: list[str]) -> None:
        """Remove Engram buckets for memory IDs."""
        if not settings.engram_enabled or not memory_ids:
            return
        if self.conn is None:
            raise RuntimeError(_DB_NOT_CONNECTED_ERROR)

        placeholders = ",".join(["?"] * len(memory_ids))
        self.execute(
            f"DELETE FROM engram_index WHERE memory_id IN ({placeholders})",
            tuple(memory_ids),
        )
        self.commit()

    def engram_search_candidates(
        self, query: str, project: str | None = None, limit: int | None = None
    ) -> list[tuple[str, int]]:
        """Return candidate memory IDs using Engram hashed n-gram lookup."""
        if not settings.engram_enabled:
            return []
        if self.conn is None:
            raise RuntimeError(_DB_NOT_CONNECTED_ERROR)

        buckets = engram_index.buckets_for_query(query)
        if not buckets:
            return []

        limit = int(limit or getattr(settings, "engram_candidate_limit", 200))
        min_hits = int(getattr(settings, "engram_min_hits", 2))

        placeholders = ",".join(["?"] * len(buckets))
        sql = (
            "SELECT e.memory_id AS id, SUM(e.hits) AS hits "
            "FROM engram_index e "
            "JOIN memories m ON m.id = e.memory_id "
            "WHERE m.archived = 0 AND e.bucket IN (" + placeholders + ")"
        )
        params: list[Any] = [*buckets]
        if project:
            sql += " AND m.project = ?"
            params.append(project)
        sql += " GROUP BY e.memory_id HAVING SUM(e.hits) >= ? ORDER BY hits DESC LIMIT ?"
        params.extend([min_hits, limit])

        try:
            cursor = self.execute(sql, tuple(params))
            rows = cursor.fetchall()
            return [(row["id"], int(row["hits"])) for row in rows]
        except sqlite3.OperationalError as e:
            logger.warning(f"Engram search failed: {e}")
            return []

    def _leann_project_key(self, project: str | None) -> str:
        if not project:
            return _LEANN_GLOBAL_KEY
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", project.strip().lower()).strip("-")
        if not slug:
            digest = hashlib.sha1(project.encode("utf-8")).hexdigest()[:12]
            slug = f"project-{digest}"
        return slug[:_LEANN_PROJECT_MAX_LEN]

    def _leann_index_path(self, project: str | None = None) -> Path:
        base = Path(settings.leann_index_path).expanduser().resolve()
        if not project:
            return base
        key = self._leann_project_key(project)
        if key == _LEANN_GLOBAL_KEY:
            return base
        suffix = base.suffix if base.suffix else ".leann"
        stem = base.stem or "memories"
        return base.with_name(f"{stem}_{key}{suffix}")

    def _leann_meta_path(self, index_path: Path) -> Path:
        return Path(f"{index_path}.meta.json")

    def leann_global_key(self) -> str:
        return _LEANN_GLOBAL_KEY

    def _get_project_for_memory(self, memory_id: str) -> str | None:
        if self.conn is None:
            raise RuntimeError(_DB_NOT_CONNECTED_ERROR)
        cursor = self.execute("SELECT project FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()
        return row["project"] if row else None

    def list_projects(self, include_none: bool = False) -> list[str | None]:
        if self.conn is None:
            raise RuntimeError(_DB_NOT_CONNECTED_ERROR)
        if include_none:
            cursor = self.execute("SELECT DISTINCT project FROM memories WHERE archived = 0")
        else:
            cursor = self.execute(
                "SELECT DISTINCT project FROM memories WHERE archived = 0 AND project IS NOT NULL"
            )
        return [row["project"] for row in cursor.fetchall()]

    def _mark_leann_dirty(self, project: str | None) -> None:
        key = self._leann_project_key(project)
        self.leann_dirty_projects.add(key)
        if project is not None:
            self.leann_dirty_projects.add(_LEANN_GLOBAL_KEY)

    def _clear_leann_dirty(self, project: str | None) -> None:
        key = self._leann_project_key(project)
        self.leann_dirty_projects.discard(key)

    def leann_is_dirty(self, project: str | None) -> bool:
        key = self._leann_project_key(project)
        return key in self.leann_dirty_projects

    def mark_all_leann_dirty(self) -> None:
        projects = self.list_projects(include_none=True)
        if not projects:
            self.leann_dirty_projects.add(_LEANN_GLOBAL_KEY)
            return
        for project in projects:
            self._mark_leann_dirty(project)

    def next_leann_build_project(self) -> str | None:
        projects = self.list_projects(include_none=True)
        if not projects:
            return None
        ordered = sorted([p for p in projects if p])
        ordered.append(_LEANN_GLOBAL_KEY)
        for project in ordered:
            project_value = None if project == _LEANN_GLOBAL_KEY else project
            index_path = self._leann_index_path(project_value)
            meta_path = self._leann_meta_path(index_path)
            if self.leann_is_dirty(project_value) or not meta_path.exists():
                return project
        return None

    def _cleanup_leann_engine_key(self, key: str) -> None:
        engine = self.leann_engines.pop(key, None)
        if engine is None:
            return
        cleanup = getattr(engine, "cleanup", None)
        if callable(cleanup):
            try:
                cleanup()
            except Exception as e:
                logger.warning(f"LEANN cleanup failed: {e}")

    def _cleanup_leann_engine(self, project: str | None = None) -> None:
        if project is None:
            for key in list(self.leann_engines.keys()):
                self._cleanup_leann_engine_key(key)
            return
        key = self._leann_project_key(project)
        self._cleanup_leann_engine_key(key)

    def _load_leann_engine(self, project: str | None) -> bool:
        if not settings.leann_enabled:
            return False
        try:
            from leann import LeannSearcher
        except Exception as e:
            logger.warning(f"LEANN not available: {e}")
            return False

        index_path = self._leann_index_path(project)
        meta_path = self._leann_meta_path(index_path)
        if not meta_path.exists():
            logger.info("LEANN index not found: %s", meta_path)
            return False

        try:
            key = self._leann_project_key(project)
            self.leann_engines[key] = LeannSearcher(
                str(index_path),
                enable_warmup=bool(settings.leann_warmup_on_start),
                recompute_embeddings=bool(settings.leann_recompute_on_search),
            )
            self._clear_leann_dirty(project)
            logger.info("LEANN searcher loaded: %s", index_path)
            return True
        except Exception as e:
            logger.warning(f"LEANN searcher load failed: {e}")
            self.leann_engines.pop(self._leann_project_key(project), None)
            return False

    def build_leann_index(self, project: str | None = None) -> bool:
        if not settings.leann_enabled:
            return False
        if self.conn is None:
            raise RuntimeError(_DB_NOT_CONNECTED_ERROR)

        try:
            from leann import LeannBuilder
        except Exception as e:
            logger.warning(f"LEANN not available: {e}")
            return False

        from .embeddings import embedding_service

        embedding_service.load_model()
        emb_dim = embedding_service.embedding_dim

        backend_kwargs: dict[str, Any] = {}
        if settings.leann_backend == "hnsw":
            backend_kwargs["is_recompute"] = bool(settings.leann_recompute_on_search)
            if not settings.leann_recompute_on_search:
                backend_kwargs["is_compact"] = False

        builder = LeannBuilder(
            backend_name=settings.leann_backend,
            embedding_model=embedding_service.model_name,
            embedding_mode="sentence-transformers",
            dimensions=emb_dim,
            **backend_kwargs,
        )

        sql = (
            "SELECT id, text, embedding, project FROM memories "
            "WHERE archived = 0 AND embedding IS NOT NULL"
        )
        params: list[Any] = []
        if project:
            sql += _PROJECT_FILTER_SQL
            params.append(project)
        cursor = self.execute(sql, tuple(params))
        rows = cursor.fetchall()
        ids: list[str] = []
        embeddings: list[list[float]] = []
        for row in rows:
            try:
                emb = json.loads(row["embedding"].decode("utf-8"))
            except Exception:
                continue
            if emb and len(emb) == emb_dim:
                memory_id = row["id"]
                ids.append(memory_id)
                embeddings.append(emb)
                metadata: dict[str, Any] = {"id": memory_id}
                if row["project"]:
                    metadata["project"] = row["project"]
                builder.add_text(row["text"] or "", metadata=metadata)

        if not ids:
            logger.info(
                "LEANN build skipped: no embeddings available (project=%s)",
                project or "global",
            )
            return False

        import os
        import pickle
        import tempfile

        import numpy as np

        index_path = self._leann_index_path(project)
        index_path.parent.mkdir(parents=True, exist_ok=True)

        embeddings_arr = np.asarray(embeddings, dtype=np.float32)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False) as tmp_file:
                pickle.dump((ids, embeddings_arr), tmp_file)
                temp_path = tmp_file.name
            builder.build_index_from_embeddings(str(index_path), temp_path)
        finally:
            if temp_path:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

        self._clear_leann_dirty(project)
        self._cleanup_leann_engine(project)
        logger.info(
            "LEANN index built: entries=%d path=%s project=%s",
            len(ids),
            index_path,
            project or "global",
        )
        return True

    def ensure_leann_engine(self, project: str | None, build_if_missing: bool = False) -> bool:
        if not settings.leann_enabled:
            return False

        key = self._leann_project_key(project)
        if key in self.leann_engines and not self.leann_is_dirty(project):
            return True

        if key in self.leann_engines and self.leann_is_dirty(project):
            self._cleanup_leann_engine(project)

        index_path = self._leann_index_path(project)
        meta_path = self._leann_meta_path(index_path)
        if meta_path.exists() and not self.leann_is_dirty(project):
            return self._load_leann_engine(project)

        if not build_if_missing:
            return False

        if not self.build_leann_index(project):
            return False
        return self._load_leann_engine(project)

    def maybe_init_leann(self) -> None:
        if not settings.leann_enabled:
            return
        if settings.leann_lazy_build and not settings.leann_warmup_on_start:
            return
        build_if_missing = not settings.leann_lazy_build
        self.ensure_leann_engine(project=None, build_if_missing=build_if_missing)

    def leann_search(self, query: str, limit: int = 5, project: str | None = None) -> list[str]:
        if not self.ensure_leann_engine(project=project, build_if_missing=True):
            return []
        engine = self.leann_engines.get(self._leann_project_key(project))
        if engine is None:
            return []
        try:
            results = engine.search(
                query,
                top_k=limit,
            )
        except Exception as e:
            logger.warning(f"LEANN search failed: {e}")
            return []

        ids = [result.id for result in results]
        if not project or not ids:
            return ids

        allowed = {m.id for m in self.get_memories_by_ids(ids=ids, project=project)}
        return [mid for mid in ids if mid in allowed]

    def close(self) -> None:
        """Close database connection."""
        self._cleanup_leann_engine()
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor."""
        if self.conn is None:
            raise RuntimeError(_DB_NOT_CONNECTED_ERROR)
        return self.conn.execute(query, params)

    def commit(self) -> None:
        """Commit current transaction."""
        if self.conn is None:
            raise RuntimeError(_DB_NOT_CONNECTED_ERROR)
        self.conn.commit()

    def save_memory(self, memory: Memory) -> None:
        """Save a memory to database."""
        embedding_bytes = None
        if memory.embedding:
            # Convert embedding list to bytes (simple JSON encoding for SQLite)
            embedding_bytes = json.dumps(memory.embedding).encode("utf-8")

        tags_str = json.dumps(memory.tags)

        self.execute(
            """
            INSERT INTO memories (id, text, text_hash, embedding, project, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory.id,
                memory.text,
                memory.text_hash,
                embedding_bytes,
                memory.project,
                tags_str,
                memory.created_at,
                memory.updated_at,
            ),
        )
        self.commit()

        try:
            self.upsert_engram_index(memory.id, memory.text)
        except Exception as e:
            logger.warning(f"Engram index update failed: {e}")
        self._mark_leann_dirty(memory.project)

    def get_memory_by_id(self, memory_id: str) -> Memory | None:
        """Retrieve a memory by ID."""
        cursor = self.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_memory(row)

    def get_memory_by_hash(self, text_hash: str) -> Memory | None:
        """Retrieve a memory by text hash (for deduplication)."""
        cursor = self.execute(
            "SELECT * FROM memories WHERE text_hash = ? AND archived = 0", (text_hash,)
        )
        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_memory(row)

    def list_memories(
        self,
        project: str | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Memory]:
        """List memories with optional filtering."""
        query = "SELECT * FROM memories WHERE archived = 0"
        params: list[Any] = []

        if project:
            query += _PROJECT_FILTER_SQL
            params.append(project)

        if tags:
            # Simple tag filtering (checks if ANY tag matches)
            tag_conditions = " OR ".join([_TAGS_LIKE_SQL for _ in tags])
            query += f" AND ({tag_conditions})"
            params.extend([f'%"{tag}"%' for tag in tags])

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.execute(query, tuple(params))
        rows = cursor.fetchall()

        return [self._row_to_memory(row) for row in rows]

    def count_memories(self, project: str | None = None, tags: list[str] | None = None) -> int:
        """Count total memories with optional filtering."""
        query = "SELECT COUNT(*) FROM memories WHERE archived = 0"
        params: list[Any] = []

        if project:
            query += _PROJECT_FILTER_SQL
            params.append(project)

        if tags:
            tag_conditions = " OR ".join([_TAGS_LIKE_SQL for _ in tags])
            query += f" AND ({tag_conditions})"
            params.extend([f'%"{tag}"%' for tag in tags])

        cursor = self.execute(query, tuple(params))
        result = cursor.fetchone()
        return result[0] if result else 0

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID (hard delete)."""
        project = self._get_project_for_memory(memory_id)
        cursor = self.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        deleted = cursor.rowcount > 0
        if deleted:
            try:
                self.delete_engram_for_ids([memory_id])
            except Exception as e:
                logger.warning(f"Engram index cleanup failed: {e}")
        self.commit()
        if deleted:
            self._mark_leann_dirty(project)
        return deleted

    def update_embedding(self, memory_id: str, embedding: list[float]) -> bool:
        """Update embedding vector for a memory and touch updated_at."""
        embedding_bytes = json.dumps(embedding).encode("utf-8")
        updated_at = get_timestamp()
        cursor = self.execute(
            "UPDATE memories SET embedding = ?, updated_at = ? WHERE id = ?",
            (embedding_bytes, updated_at, memory_id),
        )
        self.commit()
        if cursor.rowcount > 0:
            project = self._get_project_for_memory(memory_id)
            self._mark_leann_dirty(project)
        return cursor.rowcount > 0

    def archive_memory(self, memory_id: str) -> bool:
        """Archive a memory by ID (soft delete)."""
        project = self._get_project_for_memory(memory_id)
        cursor = self.execute(
            "UPDATE memories SET archived = 1 WHERE id = ? AND archived = 0", (memory_id,)
        )
        archived = cursor.rowcount > 0
        if archived:
            try:
                self.delete_engram_for_ids([memory_id])
            except Exception as e:
                logger.warning(f"Engram index cleanup failed: {e}")
        self.commit()
        if archived:
            self._mark_leann_dirty(project)
        return archived

    def bulk_delete(self, project: str | None = None, before_timestamp: int | None = None) -> int:
        """Bulk delete memories (hard delete)."""
        base = "FROM memories WHERE 1=1"
        params: list[Any] = []

        if project:
            base += _PROJECT_FILTER_SQL
            params.append(project)

        if before_timestamp is not None:
            base += " AND created_at < ?"
            params.append(before_timestamp)

        ids: list[str] = []
        if settings.engram_enabled:
            cursor = self.execute(f"SELECT id {base}", tuple(params))
            ids = [row["id"] for row in cursor.fetchall()]

        cursor = self.execute(f"DELETE {base}", tuple(params))
        self.commit()

        if ids:
            try:
                self.delete_engram_for_ids(ids)
            except Exception as e:
                logger.warning(f"Engram index cleanup failed: {e}")
        if cursor.rowcount > 0:
            if project is None:
                self.mark_all_leann_dirty()
            else:
                self._mark_leann_dirty(project)
        return cursor.rowcount

    def get_memories_by_ids(
        self,
        ids: list[str],
        project: str | None = None,
        tags: list[str] | None = None,
        after_timestamp: int | None = None,
        before_timestamp: int | None = None,
    ) -> list[Memory]:
        """Get memories by IDs with optional filtering (excluding archived)."""
        if not ids:
            return []

        placeholders = ",".join(["?"] * len(ids))
        query = f"SELECT * FROM memories WHERE archived = 0 AND id IN ({placeholders})"
        params: list[Any] = list(ids)

        if project:
            query += _PROJECT_FILTER_SQL
            params.append(project)

        if tags:
            tag_conditions = " OR ".join([_TAGS_LIKE_SQL for _ in tags])
            query += f" AND ({tag_conditions})"
            params.extend([f'%"{tag}"%' for tag in tags])

        if after_timestamp is not None:
            query += " AND created_at >= ?"
            params.append(after_timestamp)

        if before_timestamp is not None:
            query += " AND created_at <= ?"
            params.append(before_timestamp)

        query += " ORDER BY created_at DESC"
        cursor = self.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [self._row_to_memory(row) for row in rows]

    def get_all_memories(
        self,
        project: str | None = None,
        tags: list[str] | None = None,
        after_timestamp: int | None = None,
        before_timestamp: int | None = None,
    ) -> list[Memory]:
        """Get all memories (for semantic search, excluding archived)."""
        query = "SELECT * FROM memories WHERE archived = 0"
        params: list[Any] = []

        if project:
            query += _PROJECT_FILTER_SQL
            params.append(project)

        if tags:
            tag_conditions = " OR ".join([_TAGS_LIKE_SQL for _ in tags])
            query += f" AND ({tag_conditions})"
            params.extend([f'%"{tag}"%' for tag in tags])

        if after_timestamp is not None:
            query += " AND created_at >= ?"
            params.append(after_timestamp)

        if before_timestamp is not None:
            query += " AND created_at <= ?"
            params.append(before_timestamp)

        query += " ORDER BY created_at DESC"
        cursor = self.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [self._row_to_memory(row) for row in rows]

    def fts_search_candidates(
        self, query: str, project: str | None = None, limit: int = 50
    ) -> list[tuple[str, float]]:
        """Search FTS index and return candidate (id, bm25) pairs.

        Lower bm25 indicates better match.
        """
        if not self.fts_ready:
            return []

        # Build query
        sql = (
            "SELECT memories_fts.id AS id, bm25(memories_fts) AS rank "
            "FROM memories_fts JOIN memories m ON m.id = memories_fts.id "
            "WHERE m.archived = 0 AND memories_fts MATCH ?"
        )
        params: list[Any] = [query]
        if project:
            sql += " AND m.project = ?"
            params.append(project)

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        try:
            cursor = self.execute(sql, tuple(params))
            rows = cursor.fetchall()
            return [(row["id"], float(row["rank"])) for row in rows]
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS search failed: {e}")
            return []

    def like_search_candidates(
        self, query: str, project: str | None = None, limit: int = 100
    ) -> list[str]:
        """Return candidate ids using simple LIKE match on text when FTS yields no results."""
        pattern = f"%{query}%"
        sql = "SELECT id FROM memories WHERE archived = 0 AND text LIKE ?"
        params: list[Any] = [pattern]
        if project:
            sql += " AND project = ?"
            params.append(project)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        try:
            cursor = self.execute(sql, tuple(params))
            return [row["id"] for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            logger.warning(f"LIKE search failed: {e}")
            return []

    def fts_rank_for_ids(
        self, query: str, ids: list[str], project: str | None = None
    ) -> dict[str, float]:
        """Return BM25 ranks for a specific set of IDs using FTS5.

        Only IDs present in the FTS match will be returned.
        """
        if not self.fts_ready or not ids:
            return {}
        # Build placeholders for IN clause
        placeholders = ",".join(["?"] * len(ids))
        sql = (
            f"SELECT memories_fts.id AS id, bm25(memories_fts) AS rank "
            f"FROM memories_fts JOIN memories m ON m.id = memories_fts.id "
            f"WHERE m.archived = 0 AND memories_fts MATCH ? AND m.id IN ({placeholders})"
        )
        params: list[Any] = [query, *ids]
        if project:
            sql += " AND m.project = ?"
            params.append(project)
        try:
            cursor = self.execute(sql, tuple(params))
            rows = cursor.fetchall()
            return {row["id"]: float(row["rank"]) for row in rows}
        except sqlite3.OperationalError as e:
            logger.warning(f"FTS rank for ids failed: {e}")
            return {}

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        total = self.count_memories()

        # Count by project (excluding archived)
        cursor = self.execute(
            """
            SELECT project, COUNT(*) as count
            FROM memories
            WHERE project IS NOT NULL AND archived = 0
            GROUP BY project
            ORDER BY count DESC
            """
        )
        memories_by_project = {row["project"]: row["count"] for row in cursor.fetchall()}

        # Get all tags distribution (excluding archived)
        cursor = self.execute("SELECT tags FROM memories WHERE tags IS NOT NULL AND archived = 0")
        tags_distribution: dict[str, int] = {}
        for row in cursor.fetchall():
            tags = json.loads(row["tags"])
            for tag in tags:
                tags_distribution[tag] = tags_distribution.get(tag, 0) + 1

        # Calculate average text length
        cursor = self.execute(
            "SELECT AVG(LENGTH(text)) as avg_length FROM memories WHERE archived = 0"
        )
        avg_text_length = cursor.fetchone()["avg_length"] or 0

        # Calculate storage size
        db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
        storage_mb = db_size / (1024 * 1024)

        # Backward-compatible keys expected by some tests
        return {
            "total_memories": total,
            "total_projects": len(memories_by_project),
            "total_tags": len(tags_distribution),
            "storage_mb": round(storage_mb, 2),
            "avg_text_length": round(avg_text_length, 0) if avg_text_length else 0,
            "memories_by_project": memories_by_project,
            "tags_distribution": tags_distribution,
            "by_project": memories_by_project,
            "top_tags": tags_distribution,
        }

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        """Convert database row to Memory object."""
        embedding = None
        if row["embedding"]:
            embedding = json.loads(row["embedding"].decode("utf-8"))

        embedding_dim = len(embedding) if embedding else None

        tags = json.loads(row["tags"]) if row["tags"] else []

        return Memory(
            id=row["id"],
            text=row["text"],
            text_hash=row["text_hash"],
            embedding=embedding,
            embedding_dim=embedding_dim,
            project=row["project"],
            tags=tags,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


# Global database instance
db = Database()
