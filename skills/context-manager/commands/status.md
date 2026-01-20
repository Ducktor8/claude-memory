---
name: context-manager:status
description: Show the current context and loaded memories
---

# /context-manager:status

Show information about the currently active context.

## When triggered

- `/context-manager:status`
- "What context is active?"
- "Memory status"

## Procedure

1. **Detect current context**:

```bash
python3 -c "
import os
import sys
sys.path.insert(0, '$HOME/.claude/memory')
from src.lib import detect_context, get_context_hierarchy, get_context_stats

# Check override
override_file = os.path.expanduser('~/.claude/memory/.context_override')
if os.path.exists(override_file):
    with open(override_file) as f:
        context = f.read().strip()
    mode = 'override'
else:
    context = detect_context()
    mode = 'auto'

hierarchy = get_context_hierarchy(context)
stats = get_context_stats(context)

print(f'context={context}')
print(f'mode={mode}')
print(f'hierarchy={\"→\".join(hierarchy)}')
print(f'total={stats[\"total\"]}')
"
```

2. **Format output**:

```
Current Context

Context: work
Mode: auto-detect (from directory)
Directory: /home/user/WebstormProjects/myapp
Hierarchy: global → work

Statistics:
- Total memories: 42
- Decisions: 12
- Resolved errors: 10
- Patterns: 15
- Preferences: 3
- Notes: 2

Last 3 memories:
[#123] Use TypeScript strict mode
[#120] Fix CORS with Vite proxy
[#118] Pattern: useForm custom hook

Use /context-manager:search <query> to search memories.
```

## If Override Active

```
Current Context

Context: trading
Mode: MANUAL OVERRIDE
Actual directory: /home/user/work/project (not matched)
Hierarchy: global → trading

Override is active. Use /context-manager:switch --auto to return to auto-detection.
```
