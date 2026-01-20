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
4. **Extraction** - At the end, new learnings are automatically saved

## Quick Start

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/claude-memory.git
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

## Default Contexts

| Context | Auto-detected from | What goes here |
|---------|-------------------|----------------|
| `global` | Always loaded | Things that apply everywhere |
| `work` | `~/work/*`, `~/WebstormProjects/*` | Work projects |
| `trading` | `~/trading/*` | Trading and finance |
| `personal` | `~/personal/*`, `~/Projects/*` | Side projects |
| `local` | `~/` (fallback) | Machine-specific stuff |

## What Gets Remembered

The system saves different types of memories:

- **Decisions** - "We chose PostgreSQL for JSON support"
- **Error fixes** - "CORS error fixed by adding Vite proxy"
- **Patterns** - "Use this custom hook for forms"
- **Preferences** - "Always use TypeScript strict mode"
- **Notes** - General information

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

## Troubleshooting

**Hooks not working?**
- Make sure you restarted Claude Code after installation
- Check `~/.claude/settings.json` has the hooks configured

**Memories not saving?**
- The extraction happens every few turns, not immediately
- Use `/context-manager:remember` to save something right now

**Wrong context detected?**
- Use `/context-manager:switch <name>` to override
- Or use `/context-manager:switch --auto` to go back to auto-detection

## License

MIT License - do whatever you want with it.
