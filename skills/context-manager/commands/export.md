# context-manager:export

Export memories to a JSON backup file.

## Usage

```
/context-manager:export [path] [--context <name>]
```

## Options

- `path`: Output file path. Default: ~/claude-memory-backup-{timestamp}.json
- `--context <name>`: Export only memories from this context

## Instructions

<context-manager-export>

Execute this to export memories:

```python
import sys
import os
sys.path.insert(0, os.path.expanduser("~/.claude/memory/src"))

from lib.backup import export_memories, get_backup_stats

# Parse arguments (if any)
output_path = None
context_filter = None

# If user provided a path or context, parse them here
# args will be passed by Claude based on user input

# Show stats first
stats = get_backup_stats()
print(f"Database contains:")
print(f"  - {stats['total_contexts']} contexts")
print(f"  - {stats['total_memories']} memories")
print(f"  - {stats['total_mappings']} directory mappings")
print(f"  - Size: {stats.get('db_size_mb', 0)} MB")
print()

# Perform export
path = export_memories(output_path=output_path, context=context_filter)
print(f"Exported to: {path}")
```

When running:
1. First show the user what will be exported (stats)
2. Then perform the export
3. Report the output file path

If user specified a context, use `context=<name>` parameter.
If user specified a path, use `output_path=<path>` parameter.

</context-manager-export>
