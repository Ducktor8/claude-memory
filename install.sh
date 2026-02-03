#!/bin/bash
# Claude Memory System - Installation Script

set -e

MEMORY_DIR="$HOME/.claude/memory"
SKILLS_DIR="$HOME/.claude/skills"
SETTINGS_FILE="$HOME/.claude/settings.json"

echo "=== Claude Memory System Installer ==="
echo

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo -n "Checking Python version... "
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [[ $(echo "$PYTHON_VERSION >= 3.10" | bc -l) -eq 1 ]]; then
    echo -e "${GREEN}OK${NC} (Python $PYTHON_VERSION)"
else
    echo -e "${YELLOW}WARNING${NC}: Python 3.10+ recommended (found $PYTHON_VERSION)"
fi

# Check SQLite FTS5 support
echo -n "Checking SQLite FTS5 support... "
if python3 -c "import sqlite3; sqlite3.connect(':memory:').execute('CREATE VIRTUAL TABLE t USING fts5(c)')" 2>/dev/null; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${YELLOW}WARNING${NC}: FTS5 not available, search may not work"
fi

# Create directories
echo -n "Creating directories... "
mkdir -p "$MEMORY_DIR"/{contexts,skills,src/{db,hooks,lib}}
mkdir -p "$SKILLS_DIR"
echo -e "${GREEN}OK${NC}"

# Copy source files
echo -n "Copying source files... "
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy if running from repo, otherwise assume already in place
if [[ -d "$SCRIPT_DIR/src" && "$SCRIPT_DIR" != "$MEMORY_DIR" ]]; then
    cp -r "$SCRIPT_DIR/src/"* "$MEMORY_DIR/src/"
    cp -r "$SCRIPT_DIR/contexts/"* "$MEMORY_DIR/contexts/" 2>/dev/null || true
    cp -r "$SCRIPT_DIR/skills/"* "$MEMORY_DIR/skills/" 2>/dev/null || true
fi
echo -e "${GREEN}OK${NC}"

# Initialize database
echo -n "Initializing database... "
python3 -c "
import sys
sys.path.insert(0, '$MEMORY_DIR/src')
from lib.db import ensure_initialized
ensure_initialized()
print('', end='')
"
echo -e "${GREEN}OK${NC}"

# Create skill symlink
echo -n "Creating skill symlinks... "
ln -sf "$MEMORY_DIR/skills/context-manager" "$SKILLS_DIR/context-manager" 2>/dev/null || true

# Create sub-command skill directories
for cmd in create forget list remember search status switch map export import errors; do
    skill_dir="$SKILLS_DIR/context-manager:$cmd"
    mkdir -p "$skill_dir"
    if [[ -f "$MEMORY_DIR/skills/context-manager/commands/$cmd.md" ]]; then
        cp "$MEMORY_DIR/skills/context-manager/commands/$cmd.md" "$skill_dir/SKILL.md"
    fi
done
echo -e "${GREEN}OK${NC}"

# Configure hooks in settings.json
echo -n "Configuring hooks... "
if [[ -f "$SETTINGS_FILE" ]]; then
    # Backup existing settings
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.bak"
fi

# Create or merge settings (append to existing hooks, don't overwrite)
python3 << 'PYTHON_SCRIPT'
import json
import os

settings_file = os.path.expanduser("~/.claude/settings.json")
memory_dir = os.path.expanduser("~/.claude/memory")

# Load existing settings or create new
if os.path.exists(settings_file):
    with open(settings_file, 'r') as f:
        settings = json.load(f)
else:
    settings = {}

# Ensure hooks structure
if 'hooks' not in settings:
    settings['hooks'] = {}

# Our hook commands (to identify and avoid duplicates)
OUR_HOOK_MARKER = f"{memory_dir}/src/hooks/"

def is_our_hook(hook_entry):
    """Check if a hook entry is one of ours."""
    if isinstance(hook_entry, dict):
        hooks_list = hook_entry.get('hooks', [])
        for h in hooks_list:
            cmd = h.get('command', '')
            if OUR_HOOK_MARKER in cmd:
                return True
    return False

def append_hook(existing_list, new_hook):
    """Append a hook to existing list, avoiding duplicates."""
    # Remove any existing hooks from us (to update them)
    filtered = [h for h in existing_list if not is_our_hook(h)]
    # Add our new hook
    filtered.append(new_hook)
    return filtered

# Define our hooks
our_hook_entries = {
    "UserPromptSubmit": {
        "hooks": [{
            "type": "command",
            "command": f"python3 {memory_dir}/src/hooks/PrePromptSubmit.py"
        }]
    },
    "PostToolUse": {
        "matcher": "*",
        "hooks": [{
            "type": "command",
            "command": f"python3 {memory_dir}/src/hooks/PostToolUse.py"
        }]
    },
    "Stop": {
        "hooks": [{
            "type": "command",
            "command": f"python3 {memory_dir}/src/hooks/Stop.py"
        }]
    }
}

# Merge: append our hooks to existing ones
for event_type, our_hook in our_hook_entries.items():
    existing = settings['hooks'].get(event_type, [])

    # Ensure existing is a list
    if not isinstance(existing, list):
        existing = [existing] if existing else []

    # Append our hook (replacing any previous version)
    settings['hooks'][event_type] = append_hook(existing, our_hook)

# Write settings
with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print(f"Hooks configured (preserved {sum(len(v) - 1 for v in settings['hooks'].values() if isinstance(v, list))} existing hooks)")
PYTHON_SCRIPT
echo -e "${GREEN}OK${NC}"

echo
echo "=== Installation Complete ==="
echo
echo "Next steps:"
echo "  1. Restart Claude Code to activate hooks"
echo "  2. Try: /context-manager:list"
echo "  3. Try: /context-manager:status"
echo
echo "Documentation: $MEMORY_DIR/README.md"
