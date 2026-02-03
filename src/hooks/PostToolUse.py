#!/usr/bin/env python3
"""
Claude Memory System - PostToolUse Hook

This hook runs AFTER Claude uses a tool.
Tracks file modifications and tool usage for memory extraction.

Input: JSON with tool usage information (stdin)
Output: None (writes to session log)
"""

import sys
import os
import json
import re
import traceback
from datetime import datetime
from pathlib import Path

# Add path for import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Files for tracking
DIRTY_FILES_PATH = os.path.expanduser("~/.claude/memory/.dirty_files")
SESSION_LOG_PATH = os.path.expanduser("~/.claude/memory/.session_log")


def ensure_dirs():
    """Ensures tracking directories exist."""
    os.makedirs(os.path.dirname(DIRTY_FILES_PATH), exist_ok=True)


def log_tool_use(tool_name: str, tool_input: dict, tool_output: str = ""):
    """Logs tool usage to session log."""
    ensure_dirs()

    # Extract relevant output (truncate for storage)
    output_preview = ""
    if tool_output:
        # Remove ANSI codes
        clean_output = re.sub(r'\x1b\[[0-9;]*m', '', tool_output)
        output_preview = clean_output[:1000]

    entry = {
        'timestamp': datetime.now().isoformat(),
        'tool': tool_name,
        'input': tool_input,
        'output_preview': output_preview
    }

    with open(SESSION_LOG_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def track_file_modification(file_path: str, operation: str):
    """Tracks a file modification for extraction trigger."""
    ensure_dirs()

    entry = {
        'timestamp': datetime.now().isoformat(),
        'file': file_path,
        'operation': operation
    }

    with open(DIRTY_FILES_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def parse_bash_for_file_ops(command: str) -> list[tuple[str, str]]:
    """Parses bash commands for file operations."""
    operations = []

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
        (r'npm\s+install', 'npm_install'),
        (r'pip\s+install', 'pip_install'),
        (r'git\s+init', 'git_init'),
        (r'git\s+clone', 'git_clone'),
        (r'docker\s+build', 'docker_build'),
        (r'docker-compose\s+up', 'docker_up'),
    ]

    for pattern, op in patterns:
        matches = re.findall(pattern, command)
        for match in matches:
            if isinstance(match, tuple):
                operations.append((match[-1], op))
            elif isinstance(match, str) and match:
                operations.append((match, op))
            else:
                operations.append(('', op))

    return operations


def log_error(hook: str, error: Exception):
    """Logs error to database if possible."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from lib.db import ensure_initialized, get_db
        ensure_initialized()
        with get_db() as conn:
            conn.execute("""
                INSERT INTO error_log (hook, error_type, error_message, stack_trace)
                VALUES (?, ?, ?, ?)
            """, (hook, type(error).__name__, str(error), traceback.format_exc()))
    except Exception:
        pass


def main():
    """Hook entry point."""
    try:
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

        # Track modifications by tool type
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
                    if file_path:
                        track_file_modification(file_path, operation)
                    else:
                        # Track operation without specific file
                        track_file_modification(f"[{operation}]", operation)

        elif tool_name == 'NotebookEdit':
            notebook_path = tool_input.get('notebook_path', '')
            if notebook_path:
                track_file_modification(notebook_path, 'notebook_edit')

    except Exception as e:
        log_error("PostToolUse", e)
        sys.stderr.write(f"[claude-memory] PostToolUse error: {e}\n")


if __name__ == "__main__":
    main()
