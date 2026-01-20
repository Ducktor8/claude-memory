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

## How It Works

1. **Auto-Detection**: Context is detected from the current directory
2. **Injection**: At the beginning of each prompt, relevant memories are injected
3. **Extraction**: At the end of turns, new memories are automatically extracted
4. **Search**: FTS5 full-text search to find past memories

## Memory Types

- `decision` - Architectural and technical decisions
- `error_fix` - Resolved bugs with solutions
- `pattern` - Reusable code patterns
- `preference` - User preferences
- `note` - General notes

## Inheritance

Contexts can have a "parent":
- `crypto-bot` with parent `trading` loads: `global` -> `trading` -> `crypto-bot`

## Configuration Files

- Database: `~/.claude/memory/memory.db`
- Contexts: `~/.claude/memory/contexts/*.md`
- Config: `~/.claude/memory/config.json`
