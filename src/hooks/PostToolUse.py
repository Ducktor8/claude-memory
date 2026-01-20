#!/usr/bin/env python3
"""
Claude Memory System - PostToolUse Hook

This hook runs AFTER Claude uses a tool.
Tracks file modifications for subsequent extraction.

Input: JSON with tool usage information (stdin)
Output: None (writes to temporary file)
"""

import sys
import os
import json
from datetime import datetime

# Add path for import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Files for tracking modifications
DIRTY_FILES_PATH = os.path.expanduser("~/.claude/memory/.dirty_files")
SESSION_LOG_PATH = os.path.expanduser("~/.claude/memory/.session_log")


def ensure_dirs():
    """Ensures that directories exist."""
    os.makedirs(os.path.dirname(DIRTY_FILES_PATH), exist_ok=True)


def log_tool_use(tool_name: str, tool_input: dict, tool_output: str = ""):
    """Logs tool usage."""
    ensure_dirs()

    entry = {
        'timestamp': datetime.now().isoformat(),
        'tool': tool_name,
        'input': tool_input,
        'output_preview': tool_output[:500] if tool_output else ""
    }

    # Append to session log
    with open(SESSION_LOG_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def track_file_modification(file_path: str, operation: str):
    """Tracks a file modification."""
    ensure_dirs()

    entry = {
        'timestamp': datetime.now().isoformat(),
        'file': file_path,
        'operation': operation
    }

    with open(DIRTY_FILES_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def parse_bash_for_file_ops(command: str) -> list[tuple[str, str]]:
    """
    Parses a bash command for file operations.

    Returns:
        List of tuples (file_path, operation)
    """
    operations = []

    # Patterns for file modification commands
    patterns = [
        (r'rm\s+(?:-[rf]+\s+)?([^\s|&;]+)', 'delete'),
        (r'mv\s+([^\s]+)\s+([^\s|&;]+)', 'move'),
        (r'cp\s+(?:-[r]+\s+)?([^\s]+)\s+([^\s|&;]+)', 'copy'),
        (r'git\s+rm\s+([^\s|&;]+)', 'delete'),
        (r'git\s+mv\s+([^\s]+)\s+([^\s|&;]+)', 'move'),
        (r'mkdir\s+(?:-p\s+)?([^\s|&;]+)', 'create_dir'),
        (r'touch\s+([^\s|&;]+)', 'create'),
        (r'>\s*([^\s|&;]+)', 'write'),
        (r'>>\s*([^\s|&;]+)', 'append'),
    ]

    import re
    for pattern, op in patterns:
        matches = re.findall(pattern, command)
        for match in matches:
            if isinstance(match, tuple):
                # mv/cp have source and dest
                operations.append((match[-1], op))  # Track destination
            else:
                operations.append((match, op))

    return operations


def main():
    """Hook entry point."""
    try:
        # Read JSON input from stdin
        input_data = sys.stdin.read().strip()

        if not input_data:
            return

        try:
            data = json.loads(input_data)
        except json.JSONDecodeError:
            return

        tool_name = data.get('tool_name', '')
        tool_input = data.get('tool_input', {})
        tool_output = data.get('tool_output', '')

        # Log the tool use
        log_tool_use(tool_name, tool_input, tool_output)

        # Track tool-specific modifications
        if tool_name == 'Edit':
            file_path = tool_input.get('file_path', '')
            if file_path:
                track_file_modification(file_path, 'edit')

        elif tool_name == 'Write':
            file_path = tool_input.get('file_path', '')
            if file_path:
                track_file_modification(file_path, 'write')

        elif tool_name == 'Bash':
            command = tool_input.get('command', '')
            if command:
                file_ops = parse_bash_for_file_ops(command)
                for file_path, operation in file_ops:
                    track_file_modification(file_path, operation)

        elif tool_name == 'NotebookEdit':
            notebook_path = tool_input.get('notebook_path', '')
            if notebook_path:
                track_file_modification(notebook_path, 'notebook_edit')

    except Exception as e:
        # Never block for hook errors
        import traceback
        sys.stderr.write(f"[claude-memory] PostToolUse error: {e}\n")
        sys.stderr.write(traceback.format_exc())


if __name__ == "__main__":
    main()
