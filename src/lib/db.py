"""
Claude Memory System - Database Connection and Utilities
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

# Default paths
DEFAULT_MEMORY_DIR = Path.home() / ".claude" / "memory"
DEFAULT_DB_PATH = DEFAULT_MEMORY_DIR / "memory.db"
SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"


def get_memory_dir() -> Path:
    """Returns the memory directory, creating it if necessary."""
    memory_dir = Path(os.environ.get("CLAUDE_MEMORY_DIR", DEFAULT_MEMORY_DIR))
    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


def get_db_path() -> Path:
    """Returns the database path."""
    return get_memory_dir() / "memory.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Creates a connection to the database.

    Args:
        db_path: Optional database path. Default: ~/.claude/memory/memory.db

    Returns:
        Configured SQLite connection
    """
    if db_path is None:
        db_path = get_db_path()

    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row  # Access by column name
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")

    return conn


@contextmanager
def get_db(db_path: Optional[Path] = None):
    """
    Context manager per connessione database con commit/rollback automatico.

    Usage:
        with get_db() as conn:
            conn.execute("INSERT INTO ...")
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database(db_path: Optional[Path] = None, schema_path: Optional[Path] = None) -> bool:
    """
    Initializes the database with the schema.

    Args:
        db_path: Database path
        schema_path: Path to schema.sql file

    Returns:
        True if initialized successfully
    """
    if db_path is None:
        db_path = get_db_path()

    if schema_path is None:
        schema_path = SCHEMA_PATH

    # Create directory if it doesn't exist
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Read schema
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    schema_sql = schema_path.read_text()

    # Execute schema
    with get_db(db_path) as conn:
        conn.executescript(schema_sql)

    return True


def is_initialized(db_path: Optional[Path] = None) -> bool:
    """Checks if the database is initialized."""
    if db_path is None:
        db_path = get_db_path()

    if not db_path.exists():
        return False

    try:
        with get_db(db_path) as conn:
            # Verify that tables exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
            )
            return cursor.fetchone() is not None
    except sqlite3.Error:
        return False


def ensure_initialized(db_path: Optional[Path] = None) -> bool:
    """Ensures that the database is initialized."""
    if not is_initialized(db_path):
        return init_database(db_path)
    return True


def execute_query(query: str, params: tuple = (), db_path: Optional[Path] = None) -> list[sqlite3.Row]:
    """
    Executes a SELECT query and returns the results.

    Args:
        query: SQL query
        params: Query parameters
        db_path: Optional database path

    Returns:
        List of result rows
    """
    with get_db(db_path) as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchall()


def execute_write(query: str, params: tuple = (), db_path: Optional[Path] = None) -> int:
    """
    Executes an INSERT/UPDATE/DELETE query and returns the number of modified rows.

    Args:
        query: SQL query
        params: Query parameters
        db_path: Optional database path

    Returns:
        Number of modified rows or lastrowid for INSERT
    """
    with get_db(db_path) as conn:
        cursor = conn.execute(query, params)
        if query.strip().upper().startswith("INSERT"):
            return cursor.lastrowid
        return cursor.rowcount


def get_stats() -> dict:
    """Returns database statistics."""
    with get_db() as conn:
        stats = {}

        # Memory count by context
        cursor = conn.execute("""
            SELECT context, COUNT(*) as count
            FROM memories
            GROUP BY context
        """)
        stats['memories_by_context'] = {row['context']: row['count'] for row in cursor}

        # Total memories
        cursor = conn.execute("SELECT COUNT(*) as total FROM memories")
        stats['total_memories'] = cursor.fetchone()['total']

        # Context count
        cursor = conn.execute("SELECT COUNT(*) as total FROM contexts")
        stats['total_contexts'] = cursor.fetchone()['total']

        # Database size
        db_path = get_db_path()
        stats['db_size_bytes'] = db_path.stat().st_size if db_path.exists() else 0
        stats['db_size_mb'] = round(stats['db_size_bytes'] / (1024 * 1024), 2)

        return stats


if __name__ == "__main__":
    # Test initialization
    print(f"Memory dir: {get_memory_dir()}")
    print(f"DB path: {get_db_path()}")
    print(f"Initialized: {is_initialized()}")

    if not is_initialized():
        print("Initializing database...")
        init_database()
        print("Done!")

    print(f"Stats: {get_stats()}")
