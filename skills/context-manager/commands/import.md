# context-manager:import

Import memories from a JSON backup file.

## Usage

```
/context-manager:import <path> [--replace] [--context <name>]
```

## Options

- `path`: Path to the backup file (required)
- `--replace`: Replace existing data instead of merging
- `--context <name>`: Import only memories from this context

## Instructions

<context-manager-import>

Execute this to import memories:

```python
import sys
import os
import json
sys.path.insert(0, os.path.expanduser("~/.claude/memory/src"))

from lib.backup import import_memories

# Parse arguments
# input_path: required, the backup file path
# merge: True by default, False if --replace specified
# context_filter: optional, import only this context

input_path = "<user-provided-path>"  # Replace with actual path
merge = True  # Set to False if user specified --replace
context_filter = None  # Set if user specified --context

# Verify file exists
if not os.path.exists(os.path.expanduser(input_path)):
    print(f"Error: File not found: {input_path}")
else:
    # Preview what will be imported
    with open(os.path.expanduser(input_path), 'r') as f:
        data = json.load(f)

    print(f"Backup file contains:")
    print(f"  - {len(data.get('contexts', []))} contexts")
    print(f"  - {len(data.get('memories', []))} memories")
    print(f"  - {len(data.get('directory_mappings', []))} mappings")
    print(f"  - Version: {data.get('version', 1)}")
    print(f"  - Exported at: {data.get('exported_at', 'unknown')}")
    print()

    # Perform import
    stats = import_memories(input_path, merge=merge, context_filter=context_filter)

    print("Import complete:")
    print(f"  - Contexts imported: {stats['contexts_imported']}")
    print(f"  - Contexts skipped (existing): {stats['contexts_skipped']}")
    print(f"  - Memories imported: {stats['memories_imported']}")
    print(f"  - Memories skipped (duplicates): {stats['memories_skipped']}")
    print(f"  - Mappings imported: {stats['mappings_imported']}")
```

When running:
1. First verify the file exists
2. Show preview of what the backup contains
3. Ask for confirmation if --replace is used
4. Perform the import
5. Report statistics

IMPORTANT: The path parameter is REQUIRED. If user doesn't provide it, ask for the backup file path.

</context-manager-import>
