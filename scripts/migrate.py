"""Database migration script for Cognio."""

import sqlite3
import sys
from pathlib import Path


def get_current_version(conn: sqlite3.Connection) -> int:
    """Get current database schema version."""
    try:
        cursor = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        result = cursor.fetchone()
        return result[0] if result else 0
    except sqlite3.OperationalError:
        return 0


def init_version_table(conn: sqlite3.Connection) -> None:
    """Initialize schema version tracking table."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at INTEGER NOT NULL,
            description TEXT
        )
    """
    )
    conn.commit()


def migration_001_initial_schema(conn: sqlite3.Connection) -> None:
    """Initial database schema."""
    print("  Applying migration 001: Initial schema")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            text_hash TEXT,
            embedding BLOB,
            project TEXT,
            tags TEXT,
            created_at INTEGER,
            updated_at INTEGER
        )
    """
    )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_project ON memories(project)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON memories(text_hash)")

    conn.execute(
        "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
        (1, int(__import__("time").time()), "Initial schema"),
    )
    conn.commit()


def migration_002_add_archived_flag(conn: sqlite3.Connection) -> None:
    """Add archived flag for soft delete."""
    print("  Applying migration 002: Add archived flag")

    # Check if column exists
    cursor = conn.execute("PRAGMA table_info(memories)")
    columns = [col[1] for col in cursor.fetchall()]

    if "archived" not in columns:
        conn.execute("ALTER TABLE memories ADD COLUMN archived INTEGER DEFAULT 0")

    conn.execute(
        "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
        (2, int(__import__("time").time()), "Add archived flag for soft delete"),
    )
    conn.commit()


# Migration registry
MIGRATIONS = {
    1: migration_001_initial_schema,
    2: migration_002_add_archived_flag,
}


def run_migrations(db_path: str) -> None:
    """Run pending migrations."""
    print(f"Running migrations on: {db_path}")

    # Ensure database directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(db_path)

    try:
        # Initialize version tracking
        init_version_table(conn)

        # Get current version
        current_version = get_current_version(conn)
        print(f"Current schema version: {current_version}")

        # Get max version available
        max_version = max(MIGRATIONS.keys()) if MIGRATIONS else 0

        if current_version >= max_version:
            print("Database is up to date!")
            return

        # Apply pending migrations
        print(f"Migrating from version {current_version} to {max_version}")

        for version in range(current_version + 1, max_version + 1):
            if version in MIGRATIONS:
                migration_func = MIGRATIONS[version]
                migration_func(conn)
                print(f"  Migration {version} completed")
            else:
                print(f"  Warning: Migration {version} not found")

        print("\nAll migrations completed successfully!")
        print(f"Current version: {get_current_version(conn)}")

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./data/memory.db"
    run_migrations(db_path)
