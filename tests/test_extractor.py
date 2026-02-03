"""
Tests for the extractor module.
"""

import pytest


class TestKeywordExtraction:
    """Tests for code keyword extraction."""

    def test_extract_camelcase(self, initialized_db):
        """Test extracting CamelCase identifiers."""
        from lib.extractor import _extract_code_keywords

        text = "The UserService class handles authentication with AuthProvider"
        keywords = _extract_code_keywords(text)

        assert "userservice" in keywords or "user" in keywords
        assert "authprovider" in keywords or "auth" in keywords

    def test_extract_snakecase(self, initialized_db):
        """Test extracting snake_case identifiers."""
        from lib.extractor import _extract_code_keywords

        text = "Use user_service and auth_provider for the implementation"
        keywords = _extract_code_keywords(text)

        assert "user_service" in keywords
        assert "auth_provider" in keywords

    def test_extract_file_paths(self, initialized_db):
        """Test extracting file paths."""
        from lib.extractor import _extract_code_keywords

        text = "Edit the file src/components/Button.tsx"
        keywords = _extract_code_keywords(text)

        assert "button.tsx" in keywords or "Button.tsx" in [k for k in keywords]


class TestCodePatterns:
    """Tests for code pattern extraction."""

    def test_extract_python_functions(self, initialized_db):
        """Test extracting Python function names."""
        from lib.extractor import _extract_code_patterns

        code = """
def fetch_user(user_id):
    pass

def process_data(data):
    pass

class UserService:
    def get_all(self):
        pass
"""
        patterns = _extract_code_patterns(code)

        assert "fetch_user" in patterns
        assert "process_data" in patterns
        assert "UserService" in patterns

    def test_extract_javascript_functions(self, initialized_db):
        """Test extracting JavaScript function names."""
        from lib.extractor import _extract_code_patterns

        code = """
function fetchUser(userId) {}
const processData = function(data) {}
const handleClick = (e) => {}
class ApiService {}
"""
        patterns = _extract_code_patterns(code)

        assert "fetchUser" in patterns
        assert "ApiService" in patterns


class TestDeduplication:
    """Tests for memory deduplication."""

    def test_compute_content_hash(self, initialized_db):
        """Test content hash computation."""
        from lib.extractor import compute_content_hash

        hash1 = compute_content_hash("Hello World")
        hash2 = compute_content_hash("Hello World")
        hash3 = compute_content_hash("hello world")  # Different case

        assert hash1 == hash2  # Same content = same hash
        assert hash1 == hash3  # Normalized, so same hash

    def test_is_duplicate_exact(self, initialized_db):
        """Test detecting exact duplicates."""
        from lib.extractor import is_duplicate, compute_content_hash
        from lib.memory import create_memory
        from lib.db import get_db

        content = "This is a test memory for deduplication"

        # Create a memory with hash
        mem_id = create_memory(content=content, context="work")
        content_hash = compute_content_hash(content)

        with get_db() as conn:
            conn.execute(
                "UPDATE memories SET content_hash = ? WHERE id = ?",
                (content_hash, mem_id)
            )

        # Same content should be detected as duplicate
        assert is_duplicate(content, "work")

        # Different content should not be duplicate
        assert not is_duplicate("Completely different content", "work")


class TestToolExtraction:
    """Tests for extracting memories from tool use."""

    def test_extract_from_edit(self, initialized_db):
        """Test extracting memory from Edit tool."""
        from lib.extractor import _extract_from_edit

        tool_input = {
            'file_path': '/home/user/project/config.json',
            'old_string': '{"port": 3000}',
            'new_string': '{"port": 3001, "host": "localhost"}'
        }

        mem = _extract_from_edit(tool_input, "")

        assert mem is not None
        assert mem.type == 'decision'
        assert 'config.json' in mem.summary

    def test_extract_from_bash_install(self, initialized_db):
        """Test extracting memory from package install."""
        from lib.extractor import _extract_from_bash

        tool_input = {'command': 'npm install express cors dotenv'}
        mems = _extract_from_bash(tool_input, "")

        assert len(mems) > 0
        assert any('express' in m.content for m in mems)

    def test_extract_from_bash_git(self, initialized_db):
        """Test extracting memory from git operations."""
        from lib.extractor import _extract_from_bash

        tool_input = {'command': 'git remote add origin https://github.com/user/repo.git'}
        mems = _extract_from_bash(tool_input, "")

        assert len(mems) > 0
        assert any('remote' in m.keywords for m in mems)


class TestBatchExtraction:
    """Tests for batch memory extraction."""

    def test_extract_and_save(self, initialized_db):
        """Test extracting and saving from session log."""
        from lib.extractor import extract_and_save_memories
        from lib.memory import get_memories_by_context

        session_log = [
            {
                'tool': 'Write',
                'input': {
                    'file_path': '/home/user/project/package.json',
                    'content': '{"name": "my-app", "version": "1.0.0"}'
                },
                'output_preview': ''
            },
            {
                'tool': 'Bash',
                'input': {'command': 'npm install axios'},
                'output_preview': 'added 1 package'
            }
        ]

        saved = extract_and_save_memories(session_log, "work")

        # Should have saved some memories
        assert saved >= 1

        # Verify memories exist
        memories = get_memories_by_context("work", include_global=False)
        assert len(memories) >= 1
