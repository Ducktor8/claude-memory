---
name: context-manager
description: |
  Multi-context memory system for Claude Code.
  Manages separate contexts (work, trading, personal, local, global) with persistent memory.
  Automatically detects context from directory or allows manual switch.
  Invoke sub-commands with /context-manager:<command>, e.g.: /context-manager:create, /context-manager:search
commands:
  - create: Create a new context
  - switch: Change active context (override auto-detect)
  - list: Show all contexts with statistics
  - status: Show current context and loaded memories
  - search: Search in memories
  - forget: Remove a memory
  - remember: Force saving a memory
  - map: Manage directory to context mappings
  - export: Export memories to JSON backup
  - import: Import memories from JSON backup
  - errors: View system error log
---

# Context Manager

Multi-context persistent memory system for Claude Code.

## Default Contexts

| Context | Description | Directory Auto-Detect |
|---------|-------------|----------------------|
| `global` | Always active memory | Always loaded |
| `work` | Work projects | `~/work/*`, `~/WebstormProjects/*` |
| `trading` | Trading and finance | `~/trading/*` |
| `personal` | Personal projects | `~/personal/*`, `~/Projects/*` |
| `local` | System and config | `~/` (fallback) |

## Available Commands

| Command | Description |
|---------|-------------|
| `/context-manager:create` | Create a new context |
| `/context-manager:switch <name>` | Change active context (override auto-detect) |
| `/context-manager:list` | Show all contexts with statistics |
| `/context-manager:status` | Show current context and loaded memories |
| `/context-manager:search <query>` | Search in memories |
| `/context-manager:forget <id>` | Remove a memory |
| `/context-manager:remember` | Force saving a memory |
| `/context-manager:map` | Manage directory to context mappings |
| `/context-manager:export` | Export memories to JSON backup file |
| `/context-manager:import <file>` | Import memories from JSON backup |
| `/context-manager:errors` | View recent system errors |

## How It Works

1. **Auto-Detection**: Context is detected from the current directory
2. **Injection**: At the beginning of each prompt, relevant memories are injected
3. **Auto-Save**: Memories are automatically extracted and saved after tool use
4. **Deduplication**: Duplicate memories are detected and skipped
5. **Search**: FTS5 full-text search to find past memories

## Memory Types

- `decision` - Architectural and technical decisions
- `error_fix` - Resolved bugs with solutions
- `pattern` - Reusable code patterns
- `preference` - User preferences
- `note` - General notes

## Auto-Save Triggers

Memories are automatically saved when:
- Configuration files are edited (package.json, tsconfig.json, etc.)
- Packages are installed (npm, pip, etc.)
- Git operations are performed
- Errors are resolved
- Code patterns are created

## Inheritance

Contexts can have a "parent":
- `crypto-bot` with parent `trading` loads: `global` -> `trading` -> `crypto-bot`

## Backup and Restore

```
/context-manager:export              # Export all memories
/context-manager:export --context work  # Export only work context
/context-manager:import backup.json  # Import from backup
```

## Configuration Files

- Database: `~/.claude/memory/memory.db`
- Contexts: `~/.claude/memory/contexts/*.md`
- Session log: `~/.claude/memory/.session_log`
