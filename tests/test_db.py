"""
Tests for the database module.
"""

import pytest
from pathlib import Path


class TestDatabaseInit:
    """Tests for database initialization."""

    def test_ensure_initialized(self, temp_memory_dir):
        """Test that ensure_initialized creates the database."""
        from lib.db import ensure_initialized, is_initialized, get_db_path

        # Copy schema
        schema_src = Path(__file__).parent.parent / "src" / "db" / "schema.sql"
        schema_dst = temp_memory_dir / "schema.sql"
        import shutil
        shutil.copy(schema_src, schema_dst)

        # Should not be initialized yet
        assert not is_initialized()

        # Initialize
        from lib.db import init_database
        init_database(schema_path=schema_dst)

        # Now should be initialized
        assert is_initialized()

    def test_get_connection(self, initialized_db):
        """Test getting a database connection."""
        from lib.db import get_connection

        conn = get_connection()
        assert conn is not None

        # Test that tables exist
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        assert 'memories' in tables
        assert 'contexts' in tables
        assert 'directory_mappings' in tables

        conn.close()

    def test_execute_query(self, initialized_db):
        """Test execute_query helper."""
        from lib.db import execute_query

        # Query default contexts
        rows = execute_query("SELECT name FROM contexts")

        names = [row['name'] for row in rows]
        assert 'global' in names
        assert 'work' in names

    def test_execute_write(self, initialized_db):
        """Test execute_write helper."""
        from lib.db import execute_write, execute_query

        # Insert a test context
        row_id = execute_write(
            "INSERT INTO contexts (name, description) VALUES (?, ?)",
            ("test-context", "A test context")
        )

        assert row_id > 0

        # Verify it was inserted
        rows = execute_query(
            "SELECT * FROM contexts WHERE name = ?",
            ("test-context",)
        )
        assert len(rows) == 1
        assert rows[0]['description'] == "A test context"


class TestDatabaseStats:
    """Tests for database statistics."""

    def test_get_stats(self, sample_memories):
        """Test getting database statistics."""
        from lib.db import get_stats

        stats = get_stats()

        assert stats['total_memories'] >= 4
        assert stats['total_contexts'] >= 5  # Default contexts
        assert 'work' in stats['memories_by_context']
        assert stats['memories_by_context']['work'] >= 3
