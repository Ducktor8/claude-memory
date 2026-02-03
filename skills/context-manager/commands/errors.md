# context-manager:errors

Show recent errors from the Claude Memory System hooks.

## Usage

```
/context-manager:errors [--all] [--clear]
```

## Options

- `--all`: Show all errors including resolved ones
- `--clear`: Mark all errors as resolved

## Instructions

<context-manager-errors>

Execute this Python code to show errors:

```python
import sys
sys.path.insert(0, os.path.expanduser("~/.claude/memory/src"))

from lib.db import ensure_initialized, get_db

ensure_initialized()

# Check for --all or --clear flags
show_all = "--all" in sys.argv or "all" in input_args if 'input_args' in dir() else False
clear_errors = "--clear" in sys.argv or "clear" in input_args if 'input_args' in dir() else False

with get_db() as conn:
    if clear_errors:
        cursor = conn.execute("UPDATE error_log SET resolved = 1 WHERE resolved = 0")
        print(f"Marked {cursor.rowcount} errors as resolved.")
    else:
        if show_all:
            cursor = conn.execute("""
                SELECT id, timestamp, hook, error_type, error_message, resolved
                FROM error_log
                ORDER BY timestamp DESC
                LIMIT 20
            """)
        else:
            cursor = conn.execute("""
                SELECT id, timestamp, hook, error_type, error_message, resolved
                FROM error_log
                WHERE resolved = 0
                ORDER BY timestamp DESC
                LIMIT 10
            """)

        errors = cursor.fetchall()

        if not errors:
            print("No errors found.")
        else:
            print(f"Found {len(errors)} error(s):\n")
            for err in errors:
                status = "RESOLVED" if err['resolved'] else "ACTIVE"
                print(f"[{err['id']}] {err['timestamp'][:16]} [{status}]")
                print(f"    Hook: {err['hook']}")
                print(f"    {err['error_type']}: {err['error_message'][:100]}")
                print()
```

Display the results in a formatted way:

1. If no errors, say "No errors recorded in the memory system."
2. If errors exist, show them in a table format with:
   - ID
   - Timestamp
   - Hook name
   - Error type
   - Brief message
3. Offer to show full stack trace if user wants details

</context-manager-errors>
