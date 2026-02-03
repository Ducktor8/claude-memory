# context-manager:map

Map directories to contexts for auto-detection.

## Usage

```
/context-manager:map [--add <pattern> <context>] [--remove <pattern>] [--list]
```

## Options

- `--add <pattern> <context>`: Add a new mapping (e.g., `--add "~/projects/myapp/*" work`)
- `--remove <pattern>`: Remove a mapping
- `--list`: Show all current mappings (default if no option)

## Examples

```
/context-manager:map --list
/context-manager:map --add "~/code/trading-bot/*" trading
/context-manager:map --add "~/Documents/notes/*" personal
/context-manager:map --remove "~/old-project/*"
```

## Instructions

<context-manager-map>

Execute this to manage directory mappings:

```python
import sys
import os
sys.path.insert(0, os.path.expanduser("~/.claude/memory/src"))

from lib.context import (
    add_directory_mapping,
    remove_directory_mapping,
    list_directory_mappings,
    list_contexts
)
from lib.db import ensure_initialized

ensure_initialized()

# For --list (default):
mappings = list_directory_mappings()
contexts = {c.name: c for c in list_contexts()}

print("Current directory mappings:\n")
print(f"{'Pattern':<40} {'Context':<15} {'Priority':<8}")
print("-" * 65)

for m in mappings:
    ctx_name = m['context']
    print(f"{m['pattern']:<40} {ctx_name:<15} {m['priority']:<8}")

print(f"\nTotal: {len(mappings)} mappings")

# For --add:
# pattern = "<user-pattern>"  # e.g., "~/projects/myapp/*"
# context = "<user-context>"  # e.g., "work"
# priority = 100  # default
#
# # Verify context exists
# if context not in contexts:
#     print(f"Error: Context '{context}' does not exist.")
#     print(f"Available: {', '.join(contexts.keys())}")
# else:
#     add_directory_mapping(pattern, context, priority)
#     print(f"Added mapping: {pattern} -> {context}")

# For --remove:
# pattern = "<user-pattern>"
# if remove_directory_mapping(pattern):
#     print(f"Removed mapping: {pattern}")
# else:
#     print(f"Mapping not found: {pattern}")
```

When running:
1. If `--list` or no option: show all mappings in a table
2. If `--add`: verify context exists, then add mapping
3. If `--remove`: remove the mapping

For --add, the pattern should use:
- `~` for home directory
- `*` for wildcards
- `**` for recursive matching

Example patterns:
- `~/work/*` - All direct subdirectories of ~/work
- `~/projects/myapp/**` - myapp and all nested directories
- `~/Documents/*.md` - All markdown files in Documents

</context-manager-map>
