"""
Claude Memory System - Library
"""

from .db import (
    get_db,
    get_db_path,
    get_memory_dir,
    init_database,
    is_initialized,
    ensure_initialized,
    get_stats
)

from .memory import (
    Memory,
    MemoryType,
    create_memory,
    get_memory,
    search_memories,
    get_memories_by_context,
    update_memory,
    delete_memory,
    get_recent_memories,
    get_important_memories
)

from .context import (
    Context,
    detect_context,
    get_context,
    list_contexts,
    create_context,
    update_context,
    delete_context,
    get_context_hierarchy,
    get_context_stats,
    add_directory_mapping,
    remove_directory_mapping,
    list_directory_mappings
)

__all__ = [
    # Database
    'get_db',
    'get_db_path',
    'get_memory_dir',
    'init_database',
    'is_initialized',
    'ensure_initialized',
    'get_stats',
    # Memory
    'Memory',
    'MemoryType',
    'create_memory',
    'get_memory',
    'search_memories',
    'get_memories_by_context',
    'update_memory',
    'delete_memory',
    'get_recent_memories',
    'get_important_memories',
    # Context
    'Context',
    'detect_context',
    'get_context',
    'list_contexts',
    'create_context',
    'update_context',
    'delete_context',
    'get_context_hierarchy',
    'get_context_stats',
    'add_directory_mapping',
    'remove_directory_mapping',
    'list_directory_mappings',
]
