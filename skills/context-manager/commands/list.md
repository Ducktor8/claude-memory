---
name: context-manager:list
description: List all contexts with statistics
---

# /context-manager:list

Show all available contexts with their statistics.

## When triggered

- `/context-manager:list`
- "Show contexts"
- "What contexts do I have?"

## Procedure

1. **Retrieve contexts**:

```bash
python3 -c "
import sys
sys.path.insert(0, '$HOME/.claude/memory')
from src.lib import list_contexts, get_context_stats

for ctx in list_contexts():
    stats = get_context_stats(ctx.name)
    print(f'{ctx.name}|{ctx.description}|{ctx.parent or \"-\"}|{stats[\"total\"]}')
"
```

2. **Format output**:

```
Available Contexts

| Context | Description | Parent | Memories |
|----------|-------------|--------|---------|
| global | Always active memory | - | 15 |
| work | Work projects | - | 42 |
| trading | Trading and finance | - | 23 |
| personal | Personal projects | - | 8 |
| local | System and config | - | 5 |
| crypto-bot | Crypto trading bot | trading | 12 |

Total: 6 contexts, 105 memories

Use /context-manager:switch <name> to change context.
Use /context-manager:create to create a new one.
```

## With Details

If the user asks for details on a specific context:

```
User: /context-manager:list work

Claude:
Context: work

Description: Work projects
Parent: -
Directory: ~/work/*, ~/WebstormProjects/*

Statistics:
- Total memories: 42
- Decisions: 12
- Patterns: 15
- Resolved errors: 10
- Preferences: 3
- Notes: 2
- Average importance: 0.65

Recent memories:
[#123] decision - Use TypeScript for new project
[#120] error_fix - CORS resolved with Vite proxy
[#118] pattern - Custom hook for form validation
```
