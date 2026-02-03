"""
Claude Memory System - Test Configuration

Provides fixtures for testing with isolated database.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_memory_dir(tmp_path):
    """Creates a temporary memory directory for isolated testing."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()

    # Set environment variable to use temp dir
    old_env = os.environ.get("CLAUDE_MEMORY_DIR")
    os.environ["CLAUDE_MEMORY_DIR"] = str(memory_dir)

    yield memory_dir

    # Restore
    if old_env:
        os.environ["CLAUDE_MEMORY_DIR"] = old_env
    else:
        os.environ.pop("CLAUDE_MEMORY_DIR", None)


@pytest.fixture
def initialized_db(temp_memory_dir):
    """Provides an initialized database in a temp directory."""
    from lib.db import init_database, get_db_path

    # Copy schema to temp location
    schema_src = Path(__file__).parent.parent / "src" / "db" / "schema.sql"
    schema_dst = temp_memory_dir / "schema.sql"

    import shutil
    shutil.copy(schema_src, schema_dst)

    # Initialize
    init_database(schema_path=schema_dst)

    yield temp_memory_dir

    # Cleanup happens automatically with tmp_path


@pytest.fixture
def sample_memories(initialized_db):
    """Creates sample memories for testing."""
    from lib.memory import create_memory

    memories = []

    # Decision memory
    mem_id = create_memory(
        content="Decided to use PostgreSQL for the main database due to JSON support",
        context="work",
        type="decision",
        summary="Use PostgreSQL for JSON support",
        keywords=["postgresql", "database", "json"],
        importance=0.8
    )
    memories.append(mem_id)

    # Error fix memory
    mem_id = create_memory(
        content="Fixed CORS error by adding proxy configuration in vite.config.ts",
        context="work",
        type="error_fix",
        summary="CORS fix: add Vite proxy",
        keywords=["cors", "vite", "proxy", "error"],
        importance=0.7
    )
    memories.append(mem_id)

    # Pattern memory
    mem_id = create_memory(
        content="Use custom useForm hook for all form handling in React components",
        context="work",
        type="pattern",
        summary="useForm hook for forms",
        keywords=["react", "hook", "form", "useform"],
        importance=0.6
    )
    memories.append(mem_id)

    # Global preference
    mem_id = create_memory(
        content="Always use TypeScript strict mode in all projects",
        context="global",
        type="preference",
        summary="TypeScript strict mode",
        keywords=["typescript", "strict", "config"],
        importance=0.9
    )
    memories.append(mem_id)

    yield memories
