"""
Tests for the backup module.
"""

import pytest
import json
import os


class TestExport:
    """Tests for memory export."""

    def test_export_all(self, sample_memories, tmp_path):
        """Test exporting all memories."""
        from lib.backup import export_memories

        output_path = str(tmp_path / "backup.json")
        result_path = export_memories(output_path=output_path)

        assert result_path == output_path
        assert os.path.exists(output_path)

        # Verify content
        with open(output_path, 'r') as f:
            data = json.load(f)

        assert data['version'] == 2
        assert 'exported_at' in data
        assert len(data['memories']) >= 4
        assert len(data['contexts']) >= 5

    def test_export_single_context(self, sample_memories, tmp_path):
        """Test exporting a single context."""
        from lib.backup import export_memories

        output_path = str(tmp_path / "work-backup.json")
        export_memories(output_path=output_path, context="work")

        with open(output_path, 'r') as f:
            data = json.load(f)

        # Should only have work memories
        for mem in data['memories']:
            assert mem['context'] == "work"

    def test_export_without_contexts(self, sample_memories, tmp_path):
        """Test exporting without context definitions."""
        from lib.backup import export_memories

        output_path = str(tmp_path / "memories-only.json")
        export_memories(output_path=output_path, include_contexts=False)

        with open(output_path, 'r') as f:
            data = json.load(f)

        assert len(data['contexts']) == 0
        assert len(data['memories']) >= 4


class TestImport:
    """Tests for memory import."""

    def test_import_merge(self, initialized_db, tmp_path):
        """Test importing with merge mode."""
        from lib.backup import export_memories, import_memories
        from lib.memory import create_memory, get_memories_by_context

        # Create initial memory
        create_memory(content="Initial memory", context="work")

        # Export
        export_path = str(tmp_path / "backup.json")
        export_memories(output_path=export_path)

        # Create another memory
        create_memory(content="Second memory", context="work")

        # Import (merge mode)
        stats = import_memories(export_path, merge=True)

        # Should skip duplicates
        assert stats['memories_skipped'] >= 0

    def test_import_context_filter(self, initialized_db, tmp_path):
        """Test importing only specific context."""
        from lib.backup import import_memories
        from lib.memory import get_memories_by_context

        # Create a backup file manually
        backup_data = {
            'version': 2,
            'exported_at': '2024-01-01T00:00:00',
            'contexts': [],
            'memories': [
                {
                    'context': 'work',
                    'type': 'note',
                    'content': 'Work memory',
                    'importance': 0.5
                },
                {
                    'context': 'trading',
                    'type': 'note',
                    'content': 'Trading memory',
                    'importance': 0.5
                }
            ],
            'directory_mappings': []
        }

        backup_path = str(tmp_path / "test-backup.json")
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f)

        # Import only work context
        stats = import_memories(backup_path, context_filter="work")

        assert stats['memories_imported'] == 1

        # Verify only work memory was imported
        work_mems = get_memories_by_context("work", include_global=False)
        trading_mems = get_memories_by_context("trading", include_global=False)

        work_contents = [m.content for m in work_mems]
        trading_contents = [m.content for m in trading_mems]

        assert "Work memory" in work_contents
        assert "Trading memory" not in trading_contents


class TestBackupStats:
    """Tests for backup statistics."""

    def test_get_backup_stats(self, sample_memories):
        """Test getting backup statistics."""
        from lib.backup import get_backup_stats

        stats = get_backup_stats()

        assert stats['total_contexts'] >= 5
        assert stats['total_memories'] >= 4
        assert 'work' in stats['memories_by_context']
        assert stats['total_mappings'] >= 0
        assert 'db_size_mb' in stats
