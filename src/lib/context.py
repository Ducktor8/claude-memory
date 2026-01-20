"""
Claude Memory System - Context Detection and Management
"""

import os
import sys
import json
import fnmatch
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

from .db import get_db, ensure_initialized, get_memory_dir


@dataclass
class Context:
    """Represents a memory context."""
    name: str
    description: str = ""
    parent: Optional[str] = None
    directory_patterns: list[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.directory_patterns is None:
            self.directory_patterns = []

    def to_dict(self) -> dict:
        d = asdict(self)
        d['directory_patterns'] = self.directory_patterns
        return d

    @classmethod
    def from_row(cls, row) -> 'Context':
        patterns = json.loads(row['directory_patterns']) if row['directory_patterns'] else []
        # sqlite3.Row doesn't have .get(), use dict() or try/except
        row_dict = dict(row)
        return cls(
            name=row_dict['name'],
            description=row_dict.get('description') or "",
            parent=row_dict.get('parent'),
            directory_patterns=patterns,
            created_at=row_dict.get('created_at'),
            updated_at=row_dict.get('updated_at')
        )


def expand_path(path: str) -> str:
    """Expands ~ and environment variables in a path."""
    return os.path.expandvars(os.path.expanduser(path))


def path_matches_pattern(path: str, pattern: str) -> bool:
    """
    Checks if a path matches a glob pattern.

    Supports:
    - ~ for home directory
    - * for single wildcard
    - ** for recursive wildcard
    """
    expanded_pattern = expand_path(pattern)
    expanded_path = expand_path(path)

    # Normalize paths
    expanded_pattern = os.path.normpath(expanded_pattern)
    expanded_path = os.path.normpath(expanded_path)

    # Handle patterns with **
    if '**' in expanded_pattern:
        # Convert ** to pattern for fnmatch
        base_pattern = expanded_pattern.replace('**', '*')
        if fnmatch.fnmatch(expanded_path, base_pattern):
            return True
        # Also check if the path is under the pattern directory
        pattern_dir = expanded_pattern.split('**')[0].rstrip('/')
        if expanded_path.startswith(pattern_dir):
            return True

    # Standard pattern with *
    if fnmatch.fnmatch(expanded_path, expanded_pattern):
        return True

    # Check if the path is under the pattern directory
    pattern_dir = expanded_pattern.rstrip('/*')
    if expanded_path.startswith(pattern_dir + '/') or expanded_path == pattern_dir:
        return True

    return False


def detect_context(directory: Optional[str] = None) -> str:
    """
    Detects the context based on the current directory.

    Args:
        directory: Directory to analyze. Default: cwd

    Returns:
        Name of the detected context (default: 'local')
    """
    ensure_initialized()

    if directory is None:
        directory = os.getcwd()

    directory = os.path.abspath(expand_path(directory))

    with get_db() as conn:
        # Retrieve all mappings ordered by priority
        cursor = conn.execute("""
            SELECT pattern, context, priority
            FROM directory_mappings
            ORDER BY priority DESC
        """)

        mappings = cursor.fetchall()

    # Find the first match with highest priority
    for mapping in mappings:
        pattern = mapping['pattern']
        context = mapping['context']

        if path_matches_pattern(directory, pattern):
            return context

    # Fallback to 'local'
    return 'local'


def get_context(name: str) -> Optional[Context]:
    """Retrieves a context by name."""
    ensure_initialized()

    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM contexts WHERE name = ?",
            (name,)
        )
        row = cursor.fetchone()

        if row:
            return Context.from_row(row)
        return None


def list_contexts() -> list[Context]:
    """Lists all contexts."""
    ensure_initialized()

    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM contexts ORDER BY name")
        return [Context.from_row(row) for row in cursor]


def create_context(
    name: str,
    description: str = "",
    directory_patterns: Optional[list[str]] = None,
    parent: Optional[str] = None
) -> Context:
    """
    Creates a new context.

    Args:
        name: Unique context name (lowercase, no spaces)
        description: Context description
        directory_patterns: List of glob patterns for auto-detect
        parent: Parent context name for inheritance

    Returns:
        Created context
    """
    ensure_initialized()

    # Validate name
    name = name.lower().replace(' ', '-')

    if directory_patterns is None:
        directory_patterns = []

    patterns_json = json.dumps(directory_patterns)

    with get_db() as conn:
        # Verify that parent exists if specified
        if parent:
            cursor = conn.execute(
                "SELECT name FROM contexts WHERE name = ?",
                (parent,)
            )
            if not cursor.fetchone():
                raise ValueError(f"Parent context '{parent}' does not exist")

        # Insert context
        conn.execute("""
            INSERT INTO contexts (name, description, parent, directory_patterns)
            VALUES (?, ?, ?, ?)
        """, (name, description, parent, patterns_json))

        # Add mapping for each pattern
        for i, pattern in enumerate(directory_patterns):
            priority = 100 - i  # More specific patterns first
            conn.execute("""
                INSERT OR REPLACE INTO directory_mappings (pattern, context, priority)
                VALUES (?, ?, ?)
            """, (pattern, name, priority))

    # Create context.md file
    _create_context_file(name, description)

    return get_context(name)


def update_context(
    name: str,
    description: Optional[str] = None,
    directory_patterns: Optional[list[str]] = None,
    parent: Optional[str] = None
) -> bool:
    """Updates an existing context."""
    ensure_initialized()

    updates = []
    params = []

    if description is not None:
        updates.append("description = ?")
        params.append(description)

    if directory_patterns is not None:
        updates.append("directory_patterns = ?")
        params.append(json.dumps(directory_patterns))

    if parent is not None:
        updates.append("parent = ?")
        params.append(parent if parent else None)

    if not updates:
        return False

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(name)

    with get_db() as conn:
        cursor = conn.execute(f"""
            UPDATE contexts SET {', '.join(updates)}
            WHERE name = ?
        """, params)

        # Update mappings if patterns changed
        if directory_patterns is not None:
            # Remove old mappings
            conn.execute(
                "DELETE FROM directory_mappings WHERE context = ?",
                (name,)
            )
            # Add new mappings
            for i, pattern in enumerate(directory_patterns):
                priority = 100 - i
                conn.execute("""
                    INSERT INTO directory_mappings (pattern, context, priority)
                    VALUES (?, ?, ?)
                """, (pattern, name, priority))

        return cursor.rowcount > 0


def delete_context(name: str, force: bool = False) -> bool:
    """
    Deletes a context.

    Args:
        name: Context name
        force: If True, also deletes associated memories

    Returns:
        True if deleted
    """
    ensure_initialized()

    # Do not allow deletion of predefined contexts
    predefined = {'global', 'work', 'trading', 'local', 'personal'}
    if name in predefined and not force:
        raise ValueError(f"Cannot delete predefined context '{name}'")

    with get_db() as conn:
        # Verify that there are no child contexts
        cursor = conn.execute(
            "SELECT name FROM contexts WHERE parent = ?",
            (name,)
        )
        children = cursor.fetchall()
        if children and not force:
            child_names = [c['name'] for c in children]
            raise ValueError(
                f"Context has children: {child_names}. Use force=True to delete."
            )

        # Delete (CASCADE will delete mappings and memories if force)
        cursor = conn.execute(
            "DELETE FROM contexts WHERE name = ?",
            (name,)
        )

        # Delete context.md file
        context_file = get_memory_dir() / "contexts" / f"{name}.md"
        if context_file.exists():
            context_file.unlink()

        return cursor.rowcount > 0


def get_context_hierarchy(name: str) -> list[str]:
    """
    Returns the context hierarchy to load.

    E.g.: for 'crypto-bot' with parent 'trading':
    Returns: ['global', 'trading', 'crypto-bot']
    """
    ensure_initialized()

    hierarchy = ['global']  # Always included

    if name == 'global':
        return hierarchy

    # Build parent chain
    chain = []
    current = name

    with get_db() as conn:
        while current and current != 'global':
            chain.append(current)
            cursor = conn.execute(
                "SELECT parent FROM contexts WHERE name = ?",
                (current,)
            )
            row = cursor.fetchone()
            current = row['parent'] if row else None

    # Reverse to get correct order (parent -> child)
    chain.reverse()
    hierarchy.extend(chain)

    return hierarchy


def get_context_stats(name: str) -> dict:
    """Returns statistics for a context."""
    ensure_initialized()

    with get_db() as conn:
        # Memory count
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN type = 'decision' THEN 1 ELSE 0 END) as decisions,
                SUM(CASE WHEN type = 'error_fix' THEN 1 ELSE 0 END) as error_fixes,
                SUM(CASE WHEN type = 'pattern' THEN 1 ELSE 0 END) as patterns,
                SUM(CASE WHEN type = 'preference' THEN 1 ELSE 0 END) as preferences,
                SUM(CASE WHEN type = 'note' THEN 1 ELSE 0 END) as notes,
                AVG(importance) as avg_importance
            FROM memories WHERE context = ?
        """, (name,))

        row = cursor.fetchone()

        return {
            'total': row['total'] or 0,
            'by_type': {
                'decisions': row['decisions'] or 0,
                'error_fixes': row['error_fixes'] or 0,
                'patterns': row['patterns'] or 0,
                'preferences': row['preferences'] or 0,
                'notes': row['notes'] or 0
            },
            'avg_importance': round(row['avg_importance'] or 0, 2)
        }


def _create_context_file(name: str, description: str = ""):
    """Creates the .md file for a new context."""
    memory_dir = get_memory_dir()
    contexts_dir = memory_dir / "contexts"
    contexts_dir.mkdir(parents=True, exist_ok=True)

    context_file = contexts_dir / f"{name}.md"

    content = f"""# Context: {name}

{description}

<!-- AUTO-GENERATED - Do not edit above this line -->

## Recent Decisions

## Frequent Patterns

## Resolved Errors

## Preferences

<!-- MANUAL NOTES - Edit below this line -->

"""

    context_file.write_text(content)


def add_directory_mapping(pattern: str, context: str, priority: int = 100) -> bool:
    """Adds a directory -> context mapping."""
    ensure_initialized()

    with get_db() as conn:
        # Verify that the context exists
        cursor = conn.execute(
            "SELECT name FROM contexts WHERE name = ?",
            (context,)
        )
        if not cursor.fetchone():
            raise ValueError(f"Context '{context}' does not exist")

        conn.execute("""
            INSERT OR REPLACE INTO directory_mappings (pattern, context, priority)
            VALUES (?, ?, ?)
        """, (pattern, context, priority))

        return True


def remove_directory_mapping(pattern: str) -> bool:
    """Removes a directory mapping."""
    ensure_initialized()

    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM directory_mappings WHERE pattern = ?",
            (pattern,)
        )
        return cursor.rowcount > 0


def list_directory_mappings(context: Optional[str] = None) -> list[dict]:
    """Lists all directory mappings."""
    ensure_initialized()

    with get_db() as conn:
        if context:
            cursor = conn.execute("""
                SELECT pattern, context, priority
                FROM directory_mappings
                WHERE context = ?
                ORDER BY priority DESC
            """, (context,))
        else:
            cursor = conn.execute("""
                SELECT pattern, context, priority
                FROM directory_mappings
                ORDER BY priority DESC, context
            """)

        return [dict(row) for row in cursor]


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Context management CLI")
    subparsers = parser.add_subparsers(dest="command")

    # detect
    detect_parser = subparsers.add_parser("detect", help="Detect context for directory")
    detect_parser.add_argument("directory", nargs="?", default=None)

    # list
    subparsers.add_parser("list", help="List all contexts")

    # create
    create_parser = subparsers.add_parser("create", help="Create new context")
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--description", default="")
    create_parser.add_argument("--patterns", nargs="*", default=[])
    create_parser.add_argument("--parent", default=None)

    # stats
    stats_parser = subparsers.add_parser("stats", help="Show context stats")
    stats_parser.add_argument("name")

    args = parser.parse_args()

    if args.command == "detect":
        context = detect_context(args.directory)
        print(context)

    elif args.command == "list":
        contexts = list_contexts()
        for ctx in contexts:
            print(f"{ctx.name}: {ctx.description}")

    elif args.command == "create":
        ctx = create_context(
            name=args.name,
            description=args.description,
            directory_patterns=args.patterns,
            parent=args.parent
        )
        print(f"Created context: {ctx.name}")

    elif args.command == "stats":
        stats = get_context_stats(args.name)
        print(json.dumps(stats, indent=2))

    else:
        parser.print_help()
