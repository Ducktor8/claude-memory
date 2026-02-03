"""
Tests for the context module.
"""

import pytest
import os


class TestContextDetection:
    """Tests for context detection."""

    def test_detect_context_work(self, initialized_db, tmp_path):
        """Test detecting work context."""
        from lib.context import detect_context

        # Create a work-like directory
        work_dir = tmp_path / "work" / "myproject"
        work_dir.mkdir(parents=True)

        # Note: This test depends on default mappings
        # Since ~/work/* is mapped to work, we test the pattern matching
        from lib.context import path_matches_pattern

        assert path_matches_pattern(str(work_dir), "~/work/*") or \
               path_matches_pattern(str(work_dir), str(tmp_path / "work/*"))

    def test_detect_context_fallback(self, initialized_db):
        """Test that unknown directories fall back to 'local'."""
        from lib.context import detect_context

        # A random directory should fall back to local
        context = detect_context("/tmp/random-test-dir-12345")

        # Should be 'local' as fallback
        assert context == "local"


class TestContextCRUD:
    """Tests for context CRUD operations."""

    def test_create_context(self, initialized_db):
        """Test creating a new context."""
        from lib.context import create_context, get_context

        ctx = create_context(
            name="my-project",
            description="My test project",
            directory_patterns=["~/projects/myproject/*"]
        )

        assert ctx is not None
        assert ctx.name == "my-project"
        assert ctx.description == "My test project"

        # Verify retrieval
        retrieved = get_context("my-project")
        assert retrieved.name == "my-project"

    def test_create_context_with_parent(self, initialized_db):
        """Test creating a context with parent."""
        from lib.context import create_context, get_context_hierarchy

        ctx = create_context(
            name="trading-bot",
            description="A trading bot project",
            parent="trading"
        )

        assert ctx.parent == "trading"

        # Check hierarchy
        hierarchy = get_context_hierarchy("trading-bot")
        assert hierarchy == ["global", "trading", "trading-bot"]

    def test_list_contexts(self, initialized_db):
        """Test listing all contexts."""
        from lib.context import list_contexts

        contexts = list_contexts()

        names = [c.name for c in contexts]
        assert "global" in names
        assert "work" in names
        assert "trading" in names

    def test_update_context(self, initialized_db):
        """Test updating a context."""
        from lib.context import create_context, update_context, get_context

        create_context(name="updateme", description="Original")

        update_context("updateme", description="Updated description")

        ctx = get_context("updateme")
        assert ctx.description == "Updated description"


class TestPathMatching:
    """Tests for path pattern matching."""

    def test_simple_wildcard(self, initialized_db):
        """Test simple wildcard matching."""
        from lib.context import path_matches_pattern

        assert path_matches_pattern("/home/user/work/project", "/home/user/work/*")
        assert not path_matches_pattern("/home/user/other/project", "/home/user/work/*")

    def test_double_wildcard(self, initialized_db):
        """Test recursive wildcard matching."""
        from lib.context import path_matches_pattern

        assert path_matches_pattern(
            "/home/user/work/project/src/file",
            "/home/user/work/**"
        )

    def test_tilde_expansion(self, initialized_db):
        """Test that ~ is expanded correctly."""
        from lib.context import expand_path
        import os

        expanded = expand_path("~/test")
        assert expanded == os.path.expanduser("~/test")


class TestDirectoryMappings:
    """Tests for directory mappings."""

    def test_add_directory_mapping(self, initialized_db):
        """Test adding a directory mapping."""
        from lib.context import (
            add_directory_mapping,
            list_directory_mappings,
            create_context
        )

        # First create context
        create_context(name="testmap")

        # Add mapping
        add_directory_mapping("~/testmap/*", "testmap", priority=50)

        mappings = list_directory_mappings("testmap")
        patterns = [m['pattern'] for m in mappings]
        assert "~/testmap/*" in patterns

    def test_remove_directory_mapping(self, initialized_db):
        """Test removing a directory mapping."""
        from lib.context import (
            add_directory_mapping,
            remove_directory_mapping,
            list_directory_mappings,
            create_context
        )

        create_context(name="removeme")
        add_directory_mapping("~/removeme/*", "removeme")

        result = remove_directory_mapping("~/removeme/*")
        assert result is True

        mappings = list_directory_mappings("removeme")
        patterns = [m['pattern'] for m in mappings]
        assert "~/removeme/*" not in patterns
