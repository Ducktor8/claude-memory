"""
Claude Memory System - Memory CRUD Operations
"""

import json
from datetime import datetime
from typing import Optional, Literal
from dataclasses import dataclass, asdict
from pathlib import Path

from .db import get_db, ensure_initialized, get_memory_dir

MemoryType = Literal['decision', 'error_fix', 'pattern', 'preference', 'note']


@dataclass
class Memory:
    """Represents a memory."""
    id: Optional[int] = None
    context: str = "global"
    type: MemoryType = "note"
    content: str = ""
    summary: Optional[str] = None
    keywords: Optional[str] = None  # CSV
    source_session: Optional[str] = None
    source_file: Optional[str] = None
    importance: float = 0.5
    created_at: Optional[str] = None
    last_accessed: Optional[str] = None
    access_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_row(cls, row) -> 'Memory':
        return cls(**dict(row))

    def keywords_list(self) -> list[str]:
        """Returns keywords as a list."""
        if not self.keywords:
            return []
        return [k.strip() for k in self.keywords.split(',')]


def create_memory(
    content: str,
    context: str = "global",
    type: MemoryType = "note",
    summary: Optional[str] = None,
    keywords: Optional[list[str]] = None,
    importance: float = 0.5,
    source_session: Optional[str] = None,
    source_file: Optional[str] = None
) -> int:
    """
    Creates a new memory.

    Args:
        content: Full content of the memory
        context: Context (global, work, trading, etc.)
        type: Memory type
        summary: Summary for search (1-2 lines)
        keywords: List of keywords for search
        importance: Importance 0.0-1.0
        source_session: Claude session ID
        source_file: Related file

    Returns:
        ID of the created memory
    """
    ensure_initialized()

    keywords_csv = ','.join(keywords) if keywords else None

    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO memories
            (context, type, content, summary, keywords, importance, source_session, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (context, type, content, summary, keywords_csv, importance, source_session, source_file))

        memory_id = cursor.lastrowid

        # Update context .md file
        _update_context_file(context)

        return memory_id


def get_memory(memory_id: int) -> Optional[Memory]:
    """Retrieves a memory by ID."""
    ensure_initialized()

    with get_db() as conn:
        # Update access
        conn.execute("""
            UPDATE memories
            SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
            WHERE id = ?
        """, (memory_id,))

        cursor = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()

        if row:
            return Memory.from_row(row)
        return None


def search_memories(
    query: str,
    context: Optional[str] = None,
    include_global: bool = True,
    limit: int = 10,
    min_importance: float = 0.0
) -> list[tuple[Memory, float]]:
    """
    Cerca memorie usando FTS5.

    Args:
        query: Query di ricerca
        context: Contesto specifico (None = tutti)
        include_global: Include sempre memorie global
        limit: Numero massimo risultati
        min_importance: Importanza minima

    Returns:
        Lista di tuple (Memory, relevance_score)
    """
    ensure_initialized()
    import re

    # Sanitize query for FTS5: quote terms with special characters
    terms = query.split()
    sanitized_terms = []
    for term in terms:
        # If it contains special characters (dashes, etc.), quote it
        if re.search(r'[^\w]', term):
            sanitized_terms.append(f'"{term}"')
        else:
            sanitized_terms.append(term)
    sanitized_query = ' OR '.join(sanitized_terms) if sanitized_terms else query

    with get_db() as conn:
        # Build context clause
        context_clause = ""
        params = [sanitized_query]

        if context:
            if include_global:
                context_clause = "AND m.context IN (?, 'global')"
                params.append(context)
            else:
                context_clause = "AND m.context = ?"
                params.append(context)

        params.extend([min_importance, limit])

        cursor = conn.execute(f"""
            SELECT m.*, bm25(memories_fts, 1.0, 0.75, 0.5) as relevance
            FROM memories m
            JOIN memories_fts fts ON m.id = fts.rowid
            WHERE memories_fts MATCH ?
            {context_clause}
            AND m.importance >= ?
            ORDER BY relevance
            LIMIT ?
        """, params)

        results = []
        for row in cursor:
            row_dict = dict(row)
            relevance = row_dict.pop('relevance', 0.0)
            memory = Memory(**row_dict)
            results.append((memory, relevance))

        # Update access for results
        if results:
            ids = [m.id for m, _ in results]
            placeholders = ','.join('?' * len(ids))
            conn.execute(f"""
                UPDATE memories
                SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE id IN ({placeholders})
            """, ids)

        return results


def get_memories_by_context(
    context: str,
    include_global: bool = True,
    limit: int = 50,
    order_by: str = "created_at DESC"
) -> list[Memory]:
    """Retrieves all memories of a context."""
    ensure_initialized()

    with get_db() as conn:
        if include_global:
            cursor = conn.execute(f"""
                SELECT * FROM memories
                WHERE context IN (?, 'global')
                ORDER BY {order_by}
                LIMIT ?
            """, (context, limit))
        else:
            cursor = conn.execute(f"""
                SELECT * FROM memories
                WHERE context = ?
                ORDER BY {order_by}
                LIMIT ?
            """, (context, limit))

        return [Memory.from_row(row) for row in cursor]


def update_memory(
    memory_id: int,
    content: Optional[str] = None,
    summary: Optional[str] = None,
    keywords: Optional[list[str]] = None,
    importance: Optional[float] = None
) -> bool:
    """Updates an existing memory."""
    ensure_initialized()

    updates = []
    params = []

    if content is not None:
        updates.append("content = ?")
        params.append(content)
    if summary is not None:
        updates.append("summary = ?")
        params.append(summary)
    if keywords is not None:
        updates.append("keywords = ?")
        params.append(','.join(keywords))
    if importance is not None:
        updates.append("importance = ?")
        params.append(importance)

    if not updates:
        return False

    params.append(memory_id)

    with get_db() as conn:
        cursor = conn.execute(f"""
            UPDATE memories SET {', '.join(updates)}
            WHERE id = ?
        """, params)

        return cursor.rowcount > 0


def delete_memory(memory_id: int) -> bool:
    """Deletes a memory."""
    ensure_initialized()

    with get_db() as conn:
        # Get context before deleting
        cursor = conn.execute("SELECT context FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()

        if not row:
            return False

        context = row['context']

        cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

        if cursor.rowcount > 0:
            _update_context_file(context)
            return True

        return False


def get_recent_memories(limit: int = 10, context: Optional[str] = None) -> list[Memory]:
    """Retrieves the most recent memories."""
    ensure_initialized()

    with get_db() as conn:
        if context:
            cursor = conn.execute("""
                SELECT * FROM memories
                WHERE context = ? OR context = 'global'
                ORDER BY created_at DESC
                LIMIT ?
            """, (context, limit))
        else:
            cursor = conn.execute("""
                SELECT * FROM memories
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        return [Memory.from_row(row) for row in cursor]


def get_important_memories(
    context: Optional[str] = None,
    min_importance: float = 0.7,
    limit: int = 10
) -> list[Memory]:
    """Retrieves the most important memories."""
    ensure_initialized()

    with get_db() as conn:
        if context:
            cursor = conn.execute("""
                SELECT * FROM memories
                WHERE (context = ? OR context = 'global')
                AND importance >= ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
            """, (context, min_importance, limit))
        else:
            cursor = conn.execute("""
                SELECT * FROM memories
                WHERE importance >= ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
            """, (min_importance, limit))

        return [Memory.from_row(row) for row in cursor]


def _update_context_file(context: str):
    """Updates the context .md file with a summary of memories."""
    memory_dir = get_memory_dir()
    contexts_dir = memory_dir / "contexts"
    contexts_dir.mkdir(parents=True, exist_ok=True)

    context_file = contexts_dir / f"{context}.md"

    with get_db() as conn:
        # Retrieve recent memories by type
        decisions = conn.execute("""
            SELECT summary, created_at FROM memories
            WHERE context = ? AND type = 'decision'
            ORDER BY created_at DESC LIMIT 5
        """, (context,)).fetchall()

        patterns = conn.execute("""
            SELECT summary, created_at FROM memories
            WHERE context = ? AND type = 'pattern'
            ORDER BY created_at DESC LIMIT 5
        """, (context,)).fetchall()

        error_fixes = conn.execute("""
            SELECT summary, created_at FROM memories
            WHERE context = ? AND type = 'error_fix'
            ORDER BY created_at DESC LIMIT 5
        """, (context,)).fetchall()

        preferences = conn.execute("""
            SELECT summary, created_at FROM memories
            WHERE context = ? AND type = 'preference'
            ORDER BY created_at DESC LIMIT 5
        """, (context,)).fetchall()

    # Generate content
    lines = [
        f"# Context: {context}",
        "",
        "<!-- AUTO-GENERATED - Do not edit above this line -->",
        ""
    ]

    if decisions:
        lines.append("## Recent Decisions")
        for row in decisions:
            date = row['created_at'][:10] if row['created_at'] else "N/A"
            lines.append(f"- [{date}] {row['summary']}")
        lines.append("")

    if patterns:
        lines.append("## Frequent Patterns")
        for row in patterns:
            lines.append(f"- {row['summary']}")
        lines.append("")

    if error_fixes:
        lines.append("## Resolved Errors")
        for row in error_fixes:
            lines.append(f"- {row['summary']}")
        lines.append("")

    if preferences:
        lines.append("## Preferences")
        for row in preferences:
            lines.append(f"- {row['summary']}")
        lines.append("")

    lines.extend([
        "<!-- MANUAL NOTES - Edit below this line -->",
        ""
    ])

    # Preserve manual notes if they exist
    if context_file.exists():
        content = context_file.read_text()
        manual_marker = "<!-- MANUAL NOTES - Edit below this line -->"
        if manual_marker in content:
            manual_notes = content.split(manual_marker)[1]
            lines.append(manual_notes.strip())

    context_file.write_text('\n'.join(lines))


if __name__ == "__main__":
    # Test
    ensure_initialized()

    # Create test memory
    memory_id = create_memory(
        content="Test: Usare FTS5 per ricerca full-text in SQLite",
        context="work",
        type="decision",
        summary="Usare FTS5 invece di vector search per semplicità",
        keywords=["fts5", "sqlite", "search", "ricerca"],
        importance=0.8
    )
    print(f"Created memory ID: {memory_id}")

    # Retrieve
    memory = get_memory(memory_id)
    print(f"Retrieved: {memory}")

    # Search
    results = search_memories("sqlite ricerca", context="work")
    print(f"Search results: {len(results)}")
    for mem, score in results:
        print(f"  [{score:.2f}] {mem.summary}")

    # Cleanup
    delete_memory(memory_id)
    print("Test memory deleted")
