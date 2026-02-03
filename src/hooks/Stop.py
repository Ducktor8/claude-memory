#!/usr/bin/env python3
"""
Claude Memory System - Stop Hook

This hook runs when Claude finishes a turn.
Automatically extracts and saves memories from the session log.

Input: None (reads from session log file)
Output: Status message about saved memories (stdout)
"""

import sys
import os
import json
import traceback
from datetime import datetime
from pathlib import Path

# Add path for import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import ensure_initialized, get_db
from lib.context import detect_context
from lib.extractor import extract_and_save_memories
from lib.migrations import ensure_migrated

# Files for tracking
SESSION_LOG_PATH = os.path.expanduser("~/.claude/memory/.session_log")
EXTRACTION_MARKER = os.path.expanduser("~/.claude/memory/.last_extraction")
DIRTY_FILES_PATH = os.path.expanduser("~/.claude/memory/.dirty_files")


def log_error(hook: str, error: Exception, context: str = ""):
    """Logs an error to the error_log table."""
    try:
        ensure_initialized()
        with get_db() as conn:
            conn.execute("""
                INSERT INTO error_log (hook, error_type, error_message, stack_trace, context)
                VALUES (?, ?, ?, ?, ?)
            """, (
                hook,
                type(error).__name__,
                str(error),
                traceback.format_exc(),
                context
            ))
    except Exception:
        pass  # Don't fail if we can't log


def should_extract() -> bool:
    """
    Determines if memory extraction should run.
    Extracts if there are dirty files or enough turns have passed.
    """
    # Always extract if there are tracked modifications
    if os.path.exists(DIRTY_FILES_PATH):
        with open(DIRTY_FILES_PATH, 'r') as f:
            if f.read().strip():
                return True

    # Check turn counter
    if os.path.exists(EXTRACTION_MARKER):
        try:
            with open(EXTRACTION_MARKER, 'r') as f:
                data = json.load(f)
                turns = data.get('turns_since_extraction', 0)

                if turns < 3:  # Extract every 3 turns minimum
                    data['turns_since_extraction'] = turns + 1
                    with open(EXTRACTION_MARKER, 'w') as fw:
                        json.dump(data, fw)
                    return False
        except (json.JSONDecodeError, KeyError):
            pass

    return True


def mark_extracted(memories_saved: int):
    """Records that extraction was performed."""
    os.makedirs(os.path.dirname(EXTRACTION_MARKER), exist_ok=True)

    with open(EXTRACTION_MARKER, 'w') as f:
        json.dump({
            'last_extraction': datetime.now().isoformat(),
            'turns_since_extraction': 0,
            'memories_saved': memories_saved
        }, f)

    # Clear dirty files
    if os.path.exists(DIRTY_FILES_PATH):
        os.remove(DIRTY_FILES_PATH)


def read_session_log() -> list[dict]:
    """Reads and parses the session log."""
    if not os.path.exists(SESSION_LOG_PATH):
        return []

    entries = []
    try:
        with open(SESSION_LOG_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass

    return entries


def clear_session_log():
    """Clears the session log after processing."""
    if os.path.exists(SESSION_LOG_PATH):
        # Keep only recent entries (last 10)
        entries = read_session_log()
        recent = entries[-10:] if len(entries) > 10 else []

        with open(SESSION_LOG_PATH, 'w') as f:
            for entry in recent:
                f.write(json.dumps(entry) + '\n')


def main():
    """Hook entry point."""
    try:
        ensure_initialized()
        ensure_migrated()

        if not should_extract():
            return

        # Detect context
        cwd = os.getcwd()
        context = detect_context(cwd)

        # Read session log
        session_log = read_session_log()

        if not session_log:
            mark_extracted(0)
            return

        # Extract and save memories
        saved = extract_and_save_memories(session_log, context)

        # Record extraction
        mark_extracted(saved)

        # Clear old log entries
        clear_session_log()

        # Output status (visible to user if verbose)
        if saved > 0:
            print(f"[claude-memory] Auto-saved {saved} memories to context '{context}'")

    except Exception as e:
        log_error("Stop", e, detect_context() if 'detect_context' in dir() else "unknown")
        sys.stderr.write(f"[claude-memory] Stop hook error: {e}\n")


if __name__ == "__main__":
    main()
