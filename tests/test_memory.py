"""
Tests for the memory module.
"""

import pytest


class TestMemoryCreate:
    """Tests for memory creation."""

    def test_create_memory(self, initialized_db):
        """Test creating a simple memory."""
        from lib.memory import create_memory, get_memory

        mem_id = create_memory(
            content="Test memory content",
            context="work",
            type="note",
            summary="Test summary",
            keywords=["test", "memory"],
            importance=0.5
        )

        assert mem_id > 0

        # Retrieve and verify
        mem = get_memory(mem_id)
        assert mem is not None
        assert mem.content == "Test memory content"
        assert mem.context == "work"
        assert mem.type == "note"
        assert mem.summary == "Test summary"
        assert "test" in mem.keywords_list()

    def test_create_memory_default_context(self, initialized_db):
        """Test that default context is 'global'."""
        from lib.memory import create_memory, get_memory

        mem_id = create_memory(content="Global memory")
        mem = get_memory(mem_id)

        assert mem.context == "global"

    def test_memory_types(self, initialized_db):
        """Test all memory types can be created."""
        from lib.memory import create_memory, get_memory

        types = ['decision', 'error_fix', 'pattern', 'preference', 'note']

        for mem_type in types:
            mem_id = create_memory(
                content=f"Test {mem_type}",
                type=mem_type
            )
            mem = get_memory(mem_id)
            assert mem.type == mem_type


class TestMemorySearch:
    """Tests for memory search functionality."""

    def test_search_by_content(self, sample_memories):
        """Test searching memories by content."""
        from lib.memory import search_memories

        results = search_memories("PostgreSQL database")

        assert len(results) > 0
        mem, score = results[0]
        assert "postgresql" in mem.content.lower() or "database" in mem.content.lower()

    def test_search_by_keyword(self, sample_memories):
        """Test searching by keywords."""
        from lib.memory import search_memories

        results = search_memories("cors proxy")

        assert len(results) > 0
        found_cors = any("cors" in m.keywords.lower() for m, _ in results if m.keywords)
        assert found_cors

    def test_search_with_context_filter(self, sample_memories):
        """Test searching within specific context."""
        from lib.memory import search_memories

        # Search only in work context
        results = search_memories(
            "typescript strict",
            context="work",
            include_global=False
        )

        # Should not find global memory
        for mem, _ in results:
            assert mem.context == "work"

    def test_search_includes_global(self, sample_memories):
        """Test that global memories are included by default."""
        from lib.memory import search_memories

        results = search_memories(
            "typescript strict",
            context="work",
            include_global=True
        )

        # Should find global memory
        found_global = any(m.context == "global" for m, _ in results)
        assert found_global


class TestMemoryUpdate:
    """Tests for memory updates."""

    def test_update_memory(self, initialized_db):
        """Test updating a memory."""
        from lib.memory import create_memory, get_memory, update_memory

        mem_id = create_memory(content="Original content")

        # Update
        update_memory(
            mem_id,
            content="Updated content",
            importance=0.9
        )

        mem = get_memory(mem_id)
        assert mem.content == "Updated content"
        assert mem.importance == 0.9

    def test_update_keywords(self, initialized_db):
        """Test updating keywords."""
        from lib.memory import create_memory, get_memory, update_memory

        mem_id = create_memory(
            content="Test",
            keywords=["old", "keywords"]
        )

        update_memory(mem_id, keywords=["new", "updated", "keywords"])

        mem = get_memory(mem_id)
        assert "new" in mem.keywords_list()
        assert "old" not in mem.keywords_list()


class TestMemoryDelete:
    """Tests for memory deletion."""

    def test_delete_memory(self, initialized_db):
        """Test deleting a memory."""
        from lib.memory import create_memory, get_memory, delete_memory

        mem_id = create_memory(content="To be deleted")
        assert get_memory(mem_id) is not None

        result = delete_memory(mem_id)
        assert result is True

        assert get_memory(mem_id) is None

    def test_delete_nonexistent(self, initialized_db):
        """Test deleting nonexistent memory returns False."""
        from lib.memory import delete_memory

        result = delete_memory(99999)
        assert result is False


class TestMemoryRetrieval:
    """Tests for memory retrieval functions."""

    def test_get_recent_memories(self, sample_memories):
        """Test getting recent memories."""
        from lib.memory import get_recent_memories

        recent = get_recent_memories(limit=3)
        assert len(recent) == 3

    def test_get_important_memories(self, sample_memories):
        """Test getting important memories."""
        from lib.memory import get_important_memories

        important = get_important_memories(min_importance=0.8)

        for mem in important:
            assert mem.importance >= 0.8

    def test_get_memories_by_context(self, sample_memories):
        """Test getting memories by context."""
        from lib.memory import get_memories_by_context

        work_mems = get_memories_by_context("work", include_global=False)

        for mem in work_mems:
            assert mem.context == "work"
