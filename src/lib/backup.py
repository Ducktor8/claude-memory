"""
Claude Memory System - Backup and Restore

Export and import memories for backup purposes.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from .db import get_db, ensure_initialized, get_memory_dir
from .memory import Memory, create_memory
from .context import Context, list_contexts, create_context


def export_memories(
    output_path: Optional[str] = None,
    context: Optional[str] = None,
    include_contexts: bool = True
) -> str:
    """
    Exports memories to a JSON file.

    Args:
        output_path: Path for export file. Default: ~/claude-memory-backup-{date}.json
        context: Export only this context. Default: all contexts
        include_contexts: Also export context definitions

    Returns:
        Path to the created export file
    """
    ensure_initialized()

    if output_path is None:
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.expanduser(f"~/claude-memory-backup-{date_str}.json")

    export_data = {
        'version': 2,
        'exported_at': datetime.now().isoformat(),
        'contexts': [],
        'memories': [],
        'directory_mappings': []
    }

    with get_db() as conn:
        # Export contexts
        if include_contexts:
            cursor = conn.execute("SELECT * FROM contexts")
            for row in cursor:
                export_data['contexts'].append({
                    'name': row['name'],
                    'description': row['description'],
                    'parent': row['parent'],
                    'directory_patterns': row['directory_patterns']
                })

            # Export directory mappings
            cursor = conn.execute("SELECT * FROM directory_mappings")
            for row in cursor:
                export_data['directory_mappings'].append({
                    'pattern': row['pattern'],
                    'context': row['context'],
                    'priority': row['priority']
                })

        # Export memories
        if context:
            cursor = conn.execute("""
                SELECT * FROM memories WHERE context = ?
                ORDER BY created_at
            """, (context,))
        else:
            cursor = conn.execute("SELECT * FROM memories ORDER BY created_at")

        for row in cursor:
            export_data['memories'].append({
                'context': row['context'],
                'type': row['type'],
                'content': row['content'],
                'content_hash': row['content_hash'],
                'summary': row['summary'],
                'keywords': row['keywords'],
                'importance': row['importance'],
                'source_file': row['source_file'],
                'created_at': row['created_at'],
                'access_count': row['access_count']
            })

    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    return output_path


def import_memories(
    input_path: str,
    merge: bool = True,
    context_filter: Optional[str] = None
) -> dict:
    """
    Imports memories from a JSON backup file.

    Args:
        input_path: Path to the backup file
        merge: If True, merge with existing. If False, replace.
        context_filter: Import only this context

    Returns:
        Statistics about the import
    """
    ensure_initialized()

    input_path = os.path.expanduser(input_path)

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Backup file not found: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stats = {
        'contexts_imported': 0,
        'contexts_skipped': 0,
        'memories_imported': 0,
        'memories_skipped': 0,
        'mappings_imported': 0
    }

    with get_db() as conn:
        # Import contexts first
        for ctx_data in data.get('contexts', []):
            if context_filter and ctx_data['name'] != context_filter:
                continue

            # Check if context exists
            cursor = conn.execute(
                "SELECT name FROM contexts WHERE name = ?",
                (ctx_data['name'],)
            )

            if cursor.fetchone():
                if merge:
                    stats['contexts_skipped'] += 1
                    continue
                else:
                    # Delete existing to replace
                    conn.execute("DELETE FROM contexts WHERE name = ?", (ctx_data['name'],))

            conn.execute("""
                INSERT INTO contexts (name, description, parent, directory_patterns)
                VALUES (?, ?, ?, ?)
            """, (
                ctx_data['name'],
                ctx_data.get('description', ''),
                ctx_data.get('parent'),
                ctx_data.get('directory_patterns', '[]')
            ))
            stats['contexts_imported'] += 1

        # Import directory mappings
        for mapping in data.get('directory_mappings', []):
            if context_filter and mapping['context'] != context_filter:
                continue

            try:
                conn.execute("""
                    INSERT OR REPLACE INTO directory_mappings (pattern, context, priority)
                    VALUES (?, ?, ?)
                """, (mapping['pattern'], mapping['context'], mapping['priority']))
                stats['mappings_imported'] += 1
            except Exception:
                pass

        # Import memories
        for mem_data in data.get('memories', []):
            if context_filter and mem_data['context'] != context_filter:
                continue

            # Check for duplicate by hash
            content_hash = mem_data.get('content_hash')
            if content_hash and merge:
                cursor = conn.execute(
                    "SELECT id FROM memories WHERE content_hash = ?",
                    (content_hash,)
                )
                if cursor.fetchone():
                    stats['memories_skipped'] += 1
                    continue

            # Insert memory
            conn.execute("""
                INSERT INTO memories
                (context, type, content, content_hash, summary, keywords,
                 importance, source_file, created_at, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mem_data['context'],
                mem_data.get('type', 'note'),
                mem_data['content'],
                mem_data.get('content_hash'),
                mem_data.get('summary'),
                mem_data.get('keywords'),
                mem_data.get('importance', 0.5),
                mem_data.get('source_file'),
                mem_data.get('created_at'),
                mem_data.get('access_count', 0)
            ))
            stats['memories_imported'] += 1

    return stats


def get_backup_stats() -> dict:
    """Returns statistics about what would be exported."""
    ensure_initialized()

    with get_db() as conn:
        stats = {}

        cursor = conn.execute("SELECT COUNT(*) as c FROM contexts")
        stats['total_contexts'] = cursor.fetchone()['c']

        cursor = conn.execute("SELECT COUNT(*) as c FROM memories")
        stats['total_memories'] = cursor.fetchone()['c']

        cursor = conn.execute("""
            SELECT context, COUNT(*) as c FROM memories GROUP BY context
        """)
        stats['memories_by_context'] = {row['context']: row['c'] for row in cursor}

        cursor = conn.execute("SELECT COUNT(*) as c FROM directory_mappings")
        stats['total_mappings'] = cursor.fetchone()['c']

        # Database file size
        db_path = get_memory_dir() / "memory.db"
        if db_path.exists():
            stats['db_size_mb'] = round(db_path.stat().st_size / (1024 * 1024), 2)

    return stats


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python backup.py [export|import|stats] [options]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "export":
        path = export_memories()
        print(f"Exported to: {path}")

    elif cmd == "import":
        if len(sys.argv) < 3:
            print("Usage: python backup.py import <file>")
            sys.exit(1)
        stats = import_memories(sys.argv[2])
        print(f"Import stats: {json.dumps(stats, indent=2)}")

    elif cmd == "stats":
        stats = get_backup_stats()
        print(json.dumps(stats, indent=2))
