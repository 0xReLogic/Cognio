"""Database management for Cognio."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from .config import settings
from .models import Memory
from .utils import get_timestamp

logger = logging.getLogger(__name__)

# Constants
_DB_NOT_CONNECTED_ERROR = "Database not connected"
_PROJECT_FILTER_SQL = " AND project = ?"


class Database:
    """SQLite database manager for memories."""

    def __init__(self, db_path: str | None = None) -> None:
        """Initialize database connection."""
        self.db_path = db_path or settings.db_path
        self.conn: sqlite3.Connection | None = None
        self.fts_ready: bool = False

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

        self.conn.commit()
        logger.info("Database schema initialized")

    def has_fts(self) -> bool:
        """Return whether FTS is ready for use."""
        return self.fts_ready

    def close(self) -> None:
        """Close database connection."""
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
            tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
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
            tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
            query += f" AND ({tag_conditions})"
            params.extend([f'%"{tag}"%' for tag in tags])

        cursor = self.execute(query, tuple(params))
        result = cursor.fetchone()
        return result[0] if result else 0

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory by ID (hard delete)."""
        cursor = self.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.commit()
        return cursor.rowcount > 0

    def update_embedding(self, memory_id: str, embedding: list[float]) -> bool:
        """Update embedding vector for a memory and touch updated_at."""
        embedding_bytes = json.dumps(embedding).encode("utf-8")
        updated_at = get_timestamp()
        cursor = self.execute(
            "UPDATE memories SET embedding = ?, updated_at = ? WHERE id = ?",
            (embedding_bytes, updated_at, memory_id),
        )
        self.commit()
        return cursor.rowcount > 0

    def archive_memory(self, memory_id: str) -> bool:
        """Archive a memory by ID (soft delete)."""
        cursor = self.execute(
            "UPDATE memories SET archived = 1 WHERE id = ? AND archived = 0", (memory_id,)
        )
        self.commit()
        return cursor.rowcount > 0

    def bulk_delete(self, project: str | None = None, before_timestamp: int | None = None) -> int:
        """Bulk delete memories (hard delete)."""
        query = "DELETE FROM memories WHERE 1=1"
        params: list[Any] = []

        if project:
            query += _PROJECT_FILTER_SQL
            params.append(project)

        if before_timestamp:
            query += " AND created_at < ?"
            params.append(before_timestamp)

        cursor = self.execute(query, tuple(params))
        self.commit()
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
            tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
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

    def get_all_memories(self) -> list[Memory]:
        """Get all memories (for semantic search, excluding archived)."""
        cursor = self.execute("SELECT * FROM memories WHERE archived = 0 ORDER BY created_at DESC")
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

        tags = json.loads(row["tags"]) if row["tags"] else []

        return Memory(
            id=row["id"],
            text=row["text"],
            text_hash=row["text_hash"],
            embedding=embedding,
            project=row["project"],
            tags=tags,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


# Global database instance
db = Database()
