"""
Claude Memory System - Database Migrations

Handles schema upgrades for existing databases.
"""

import sqlite3
from pathlib import Path
from typing import Callable

from .db import get_db, get_db_path, ensure_initialized

# Current schema version
CURRENT_VERSION = 2

# Migration functions: version -> function that upgrades TO that version
MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {}


def migration(version: int):
    """Decorator to register a migration function."""
    def decorator(func: Callable[[sqlite3.Connection], None]):
        MIGRATIONS[version] = func
        return func
    return decorator


def get_schema_version() -> int:
    """Gets the current schema version from database."""
    try:
        with get_db() as conn:
            # Check if schema_version table exists
            cursor = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='schema_version'
            """)
            if not cursor.fetchone():
                return 1  # Original schema without versioning

            cursor = conn.execute("SELECT MAX(version) FROM schema_version")
            row = cursor.fetchone()
            return row[0] if row and row[0] else 1
    except Exception:
        return 0  # Database doesn't exist


def run_migrations() -> tuple[int, int]:
    """
    Runs all pending migrations.

    Returns:
        Tuple of (old_version, new_version)
    """
    ensure_initialized()

    old_version = get_schema_version()

    if old_version >= CURRENT_VERSION:
        return (old_version, old_version)

    with get_db() as conn:
        for version in range(old_version + 1, CURRENT_VERSION + 1):
            if version in MIGRATIONS:
                try:
                    MIGRATIONS[version](conn)
                    conn.execute(
                        "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                        (version, f"Migration to v{version}")
                    )
                except Exception as e:
                    raise RuntimeError(f"Migration to v{version} failed: {e}")

    return (old_version, CURRENT_VERSION)


# === MIGRATIONS ===

@migration(2)
def migrate_to_v2(conn: sqlite3.Connection):
    """
    Migration to version 2:
    - Add content_hash column to memories
    - Add schema_version table
    - Add error_log table
    """
    # Add schema_version table if not exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
    """)

    # Add content_hash to memories
    try:
        conn.execute("ALTER TABLE memories ADD COLUMN content_hash TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Create index for content_hash
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_hash ON memories(content_hash)")

    # Add error_log table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS error_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            hook TEXT,
            error_type TEXT,
            error_message TEXT,
            stack_trace TEXT,
            context TEXT,
            resolved INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_error_log_timestamp ON error_log(timestamp DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_error_log_resolved ON error_log(resolved)")


def ensure_migrated():
    """Ensures database is at current schema version."""
    old, new = run_migrations()
    if old != new:
        import sys
        sys.stderr.write(f"[claude-memory] Database migrated from v{old} to v{new}\n")


if __name__ == "__main__":
    old, new = run_migrations()
    if old == new:
        print(f"Database already at version {new}")
    else:
        print(f"Migrated from version {old} to {new}")
