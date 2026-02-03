# Claude Memory System

A persistent, multi-context memory system for Claude Code. It automatically remembers decisions, patterns, and solutions across your coding sessions.

## Why?

Claude Code starts fresh every session. This means you end up explaining the same things over and over:
- "We use TypeScript strict mode in this project"
- "The API runs on port 3001, not 3000"
- "We fixed that CORS issue by adding a Vite proxy"

**Claude Memory fixes this.** It automatically saves important information and brings it back when relevant.

## How It Works

1. **Contexts** - Your memories are organized by what you're working on (work, personal, trading, etc.)
2. **Auto-detection** - The system detects which context to use based on your current directory
3. **Injection** - At the start of each conversation, relevant memories are loaded
4. **Auto-Save** - Memories are automatically extracted and saved after tool use

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Ducktor8/claude-memory.git
cd claude-memory

# Run the installer
./install.sh

# Restart Claude Code to activate hooks
```

That's it. The system will start learning from your sessions automatically.

## Commands

| Command | What it does |
|---------|--------------|
| `/context-manager:status` | See which context is active and recent memories |
| `/context-manager:list` | List all your contexts |
| `/context-manager:search <query>` | Find memories by keyword |
| `/context-manager:remember` | Manually save something important |
| `/context-manager:forget <id>` | Delete a memory |
| `/context-manager:switch <name>` | Manually change context |
| `/context-manager:create` | Create a new context |
| `/context-manager:map` | Manage directory mappings |
| `/context-manager:export` | Export memories to JSON backup |
| `/context-manager:import <file>` | Import memories from backup |
| `/context-manager:errors` | View system error log |

## Default Contexts

| Context | Auto-detected from | What goes here |
|---------|-------------------|----------------|
| `global` | Always loaded | Things that apply everywhere |
| `work` | `~/work/*`, `~/WebstormProjects/*` | Work projects |
| `trading` | `~/trading/*` | Trading and finance |
| `personal` | `~/personal/*`, `~/Projects/*` | Side projects |
| `local` | `~/` (fallback) | Machine-specific stuff |

## What Gets Remembered

The system automatically saves different types of memories:

- **Decisions** - "We chose PostgreSQL for JSON support"
- **Error fixes** - "CORS error fixed by adding Vite proxy"
- **Patterns** - "Use this custom hook for forms"
- **Preferences** - "Always use TypeScript strict mode"
- **Notes** - General information

### Auto-Save Triggers

Memories are automatically extracted when:
- Configuration files are created/edited (package.json, config.ini, etc.)
- Packages are installed (npm install, pip install, etc.)
- Git operations are performed (remote add, etc.)
- Code files with patterns are created
- Errors appear and are resolved

## File Structure

```
~/.claude/memory/
├── memory.db          # SQLite database with FTS5 search
├── contexts/          # Markdown files for each context
├── skills/            # Skill definitions for Claude Code
└── src/
    ├── db/            # Database schema
    ├── hooks/         # Auto-injection and extraction
    └── lib/           # Core Python libraries
```

## Requirements

- Python 3.10+
- SQLite with FTS5 support (standard on most systems)
- Claude Code CLI

## Creating Custom Contexts

Want a context for a specific project? Easy:

```
/context-manager:create
```

Follow the prompts to:
1. Name your context (e.g., `my-saas`)
2. Add a description
3. Map directories (e.g., `~/projects/my-saas/*`)
4. Optionally inherit from a parent context

## Directory Mappings

Map any directory to a context:

```
/context-manager:map --add "~/code/myproject/*" work
/context-manager:map --list
/context-manager:map --remove "~/old-project/*"
```

## Backup and Restore

Export your memories:
```
/context-manager:export                      # Export all
/context-manager:export --context work       # Export only work
```

Import from backup:
```
/context-manager:import ~/backup.json        # Merge with existing
/context-manager:import ~/backup.json --replace  # Replace all
```

## Troubleshooting

**Hooks not working?**
- Make sure you restarted Claude Code after installation
- Check `~/.claude/settings.json` has the hooks configured

**Memories not saving?**
- The auto-save runs after tool use (edits, bash commands)
- Use `/context-manager:remember` to save something immediately

**Wrong context detected?**
- Use `/context-manager:switch <name>` to override
- Use `/context-manager:map` to add custom directory mappings

**Check for errors?**
- Use `/context-manager:errors` to view the error log

## Development

Run tests:
```bash
pip install pytest
pytest tests/ -v
```

## License

MIT License - do whatever you want with it.
