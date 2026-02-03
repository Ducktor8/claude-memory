"""
Claude Memory System - Automatic Memory Extractor

Analyzes session logs and tool outputs to automatically extract
memories without requiring Claude to process an extraction prompt.
"""

import re
import json
import hashlib
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

from .db import get_db, ensure_initialized
from .memory import create_memory, search_memories, MemoryType


@dataclass
class ExtractedMemory:
    """A memory extracted from session analysis."""
    type: MemoryType
    content: str
    summary: str
    keywords: list[str]
    importance: float
    source_file: Optional[str] = None


# Patterns for automatic extraction
ERROR_PATTERNS = [
    # Common error messages followed by resolution
    r'(?:error|errore|exception|failed|failure)[:.\s]+(.+?)(?:fixed|risolto|solved|solution|fix)',
    r'(?:bug|issue|problem)[:.\s]+(.+?)(?:fixed|risolto|resolved)',
]

DECISION_PATTERNS = [
    r'(?:decided|deciso|scelto|chosen|using|usiamo|use)\s+(.+?)\s+(?:for|per|because|perché)',
    r'(?:will use|useremo|adopting)\s+(.+)',
    r'(?:switched to|passato a|migrated to)\s+(.+)',
]

CONFIG_PATTERNS = [
    r'(?:configured|configurato|set|impostato)\s+(.+?)\s+(?:to|a|=)',
    r'(?:added|aggiunto)\s+(.+?)\s+(?:to config|alla configurazione)',
]

# File types that often contain important decisions
IMPORTANT_FILE_TYPES = {
    '.json': ['package.json', 'tsconfig.json', 'config.json', '.eslintrc'],
    '.yaml': ['docker-compose', '.github/workflows'],
    '.yml': ['docker-compose', '.github/workflows'],
    '.toml': ['pyproject.toml', 'Cargo.toml'],
    '.ini': ['setup.cfg', 'config.ini'],
    '.env': ['.env', '.env.local'],
}


def compute_content_hash(content: str) -> str:
    """Computes a hash for deduplication."""
    normalized = ' '.join(content.lower().split())
    return hashlib.md5(normalized.encode()).hexdigest()[:16]


def is_duplicate(content: str, context: str) -> bool:
    """Checks if a similar memory already exists."""
    ensure_initialized()

    content_hash = compute_content_hash(content)

    with get_db() as conn:
        # Check exact hash match
        cursor = conn.execute("""
            SELECT id FROM memories
            WHERE context = ? AND content_hash = ?
            LIMIT 1
        """, (context, content_hash))

        if cursor.fetchone():
            return True

    # Also check FTS similarity for fuzzy dedup
    # Extract first 50 chars as search query
    query_text = content[:50].replace('"', ' ')
    try:
        results = search_memories(query_text, context=context, limit=3)
        for mem, score in results:
            # If very similar (high relevance), consider duplicate
            if score < -10:  # BM25 scores are negative, more negative = more relevant
                # Additional check: compare normalized content
                existing_normalized = ' '.join(mem.content.lower().split())
                new_normalized = ' '.join(content.lower().split())

                # Simple similarity: shared words ratio
                existing_words = set(existing_normalized.split())
                new_words = set(new_normalized.split())

                if len(existing_words) > 0 and len(new_words) > 0:
                    overlap = len(existing_words & new_words)
                    similarity = overlap / max(len(existing_words), len(new_words))

                    if similarity > 0.7:  # 70% similar = duplicate
                        return True
    except Exception:
        pass  # FTS might fail on some queries

    return False


def extract_from_tool_use(tool_name: str, tool_input: dict, tool_output: str, context: str) -> list[ExtractedMemory]:
    """
    Extracts memories from a single tool use.

    Args:
        tool_name: Name of the tool used
        tool_input: Tool input parameters
        tool_output: Tool output/result
        context: Current memory context

    Returns:
        List of extracted memories
    """
    memories = []

    if tool_name == 'Edit':
        mem = _extract_from_edit(tool_input, tool_output)
        if mem:
            memories.append(mem)

    elif tool_name == 'Write':
        mem = _extract_from_write(tool_input, tool_output)
        if mem:
            memories.append(mem)

    elif tool_name == 'Bash':
        mems = _extract_from_bash(tool_input, tool_output)
        memories.extend(mems)

    return memories


def _extract_from_edit(tool_input: dict, tool_output: str) -> Optional[ExtractedMemory]:
    """Extracts memory from an Edit operation."""
    file_path = tool_input.get('file_path', '')
    old_string = tool_input.get('old_string', '')
    new_string = tool_input.get('new_string', '')

    if not file_path or not old_string or not new_string:
        return None

    # Check if this is a significant edit
    if len(new_string) < 20 and len(old_string) < 20:
        return None  # Too small to be significant

    # Determine file importance
    file_name = Path(file_path).name
    file_ext = Path(file_path).suffix

    is_config = any(
        pattern in file_name.lower()
        for patterns in IMPORTANT_FILE_TYPES.values()
        for pattern in patterns
    ) or file_ext in IMPORTANT_FILE_TYPES

    # Look for patterns in the edit
    combined_text = f"{old_string} -> {new_string}"

    # Error fix pattern
    if any(err in old_string.lower() for err in ['error', 'bug', 'fix', 'issue']):
        return ExtractedMemory(
            type='error_fix',
            content=f"Fixed in {file_name}:\nBefore: {old_string[:200]}\nAfter: {new_string[:200]}",
            summary=f"Fix in {file_name}: {new_string[:80]}",
            keywords=_extract_code_keywords(new_string) + [file_name],
            importance=0.7,
            source_file=file_path
        )

    # Config change
    if is_config:
        return ExtractedMemory(
            type='decision',
            content=f"Configuration change in {file_name}:\n{new_string[:500]}",
            summary=f"Config: {file_name} updated",
            keywords=_extract_code_keywords(new_string) + [file_name, 'config'],
            importance=0.6,
            source_file=file_path
        )

    return None


def _extract_from_write(tool_input: dict, tool_output: str) -> Optional[ExtractedMemory]:
    """Extracts memory from a Write operation."""
    file_path = tool_input.get('file_path', '')
    content = tool_input.get('content', '')

    if not file_path or not content:
        return None

    file_name = Path(file_path).name
    file_ext = Path(file_path).suffix

    # New config file
    is_config = any(
        pattern in file_name.lower()
        for patterns in IMPORTANT_FILE_TYPES.values()
        for pattern in patterns
    )

    if is_config:
        return ExtractedMemory(
            type='decision',
            content=f"Created configuration file {file_name}:\n{content[:500]}",
            summary=f"Created config: {file_name}",
            keywords=_extract_code_keywords(content) + [file_name, 'config', 'new'],
            importance=0.7,
            source_file=file_path
        )

    # New significant file (script, module, etc.)
    if file_ext in ['.py', '.js', '.ts', '.sh', '.go', '.rs']:
        # Extract main function/class names
        patterns_found = _extract_code_patterns(content)
        if patterns_found:
            return ExtractedMemory(
                type='pattern',
                content=f"Created {file_name} with: {', '.join(patterns_found[:5])}",
                summary=f"New file: {file_name}",
                keywords=patterns_found + [file_name],
                importance=0.5,
                source_file=file_path
            )

    return None


def _extract_from_bash(tool_input: dict, tool_output: str) -> list[ExtractedMemory]:
    """Extracts memories from Bash commands."""
    command = tool_input.get('command', '')
    memories = []

    if not command:
        return memories

    # Package installation
    if any(pkg in command for pkg in ['npm install', 'pip install', 'apt install', 'brew install']):
        # Extract package names
        packages = re.findall(r'install\s+([^\s&|;]+)', command)
        if packages:
            memories.append(ExtractedMemory(
                type='decision',
                content=f"Installed packages: {', '.join(packages)}\nCommand: {command}",
                summary=f"Installed: {', '.join(packages[:3])}",
                keywords=packages + ['install', 'dependency'],
                importance=0.6
            ))

    # Git operations that indicate decisions
    if 'git' in command:
        if 'git init' in command:
            memories.append(ExtractedMemory(
                type='decision',
                content=f"Initialized git repository",
                summary="Git repo initialized",
                keywords=['git', 'init', 'repository'],
                importance=0.5
            ))
        elif 'git remote add' in command:
            remote = re.search(r'git remote add\s+\w+\s+(\S+)', command)
            if remote:
                memories.append(ExtractedMemory(
                    type='decision',
                    content=f"Added git remote: {remote.group(1)}",
                    summary=f"Git remote: {remote.group(1)}",
                    keywords=['git', 'remote', remote.group(1)],
                    importance=0.6
                ))

    # Docker operations
    if 'docker' in command:
        if 'docker build' in command or 'docker-compose up' in command:
            memories.append(ExtractedMemory(
                type='pattern',
                content=f"Docker command: {command}",
                summary=f"Docker: {command[:60]}",
                keywords=['docker', 'container', 'build'],
                importance=0.5
            ))

    # Error in output that was resolved
    if tool_output and any(err in tool_output.lower() for err in ['error', 'failed', 'exception']):
        # Check if command succeeded despite error (common in npm, etc.)
        if 'success' in tool_output.lower() or 'completed' in tool_output.lower():
            memories.append(ExtractedMemory(
                type='error_fix',
                content=f"Command with warnings: {command}\nOutput: {tool_output[:300]}",
                summary=f"Resolved: {command[:50]}",
                keywords=_extract_code_keywords(tool_output),
                importance=0.6
            ))

    return memories


def _extract_code_keywords(text: str) -> list[str]:
    """Extracts code-relevant keywords from text."""
    keywords = set()

    # CamelCase words
    camel = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', text)
    keywords.update(w.lower() for w in camel)

    # snake_case words
    snake = re.findall(r'\b[a-z]+(?:_[a-z]+)+\b', text)
    keywords.update(snake)

    # CONSTANTS
    constants = re.findall(r'\b[A-Z][A-Z_]+[A-Z]\b', text)
    keywords.update(c.lower() for c in constants)

    # File paths
    paths = re.findall(r'[\w/.-]+\.\w{1,4}\b', text)
    keywords.update(Path(p).name for p in paths if '/' in p or '.' in p)

    # Technical terms (3+ chars, not common words)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
    common = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her',
              'was', 'one', 'our', 'out', 'has', 'have', 'been', 'from', 'this', 'that',
              'with', 'they', 'will', 'what', 'when', 'make', 'like', 'just', 'over',
              'such', 'into', 'than', 'them', 'some', 'could', 'would', 'there', 'their'}
    keywords.update(w.lower() for w in words if w.lower() not in common and len(w) > 3)

    return list(keywords)[:15]  # Limit to 15 keywords


def _extract_code_patterns(code: str) -> list[str]:
    """Extracts function/class names from code."""
    patterns = []

    # Python: def, class
    patterns.extend(re.findall(r'def\s+(\w+)', code))
    patterns.extend(re.findall(r'class\s+(\w+)', code))

    # JavaScript/TypeScript: function, const/let/var ... = function, class
    patterns.extend(re.findall(r'function\s+(\w+)', code))
    patterns.extend(re.findall(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\()', code))
    patterns.extend(re.findall(r'class\s+(\w+)', code))

    # Go: func
    patterns.extend(re.findall(r'func\s+(?:\([^)]+\)\s+)?(\w+)', code))

    # Rust: fn, struct, impl
    patterns.extend(re.findall(r'fn\s+(\w+)', code))
    patterns.extend(re.findall(r'struct\s+(\w+)', code))

    return list(set(patterns))


def extract_and_save_memories(session_log: list[dict], context: str) -> int:
    """
    Analyzes a session log and saves extracted memories.

    Args:
        session_log: List of tool use entries from the session
        context: Memory context to save to

    Returns:
        Number of memories saved
    """
    ensure_initialized()
    saved = 0

    for entry in session_log:
        tool_name = entry.get('tool', '')
        tool_input = entry.get('input', {})
        tool_output = entry.get('output_preview', '')

        memories = extract_from_tool_use(tool_name, tool_input, tool_output, context)

        for mem in memories:
            # Check for duplicates
            if is_duplicate(mem.content, context):
                continue

            try:
                # Compute hash for future dedup
                content_hash = compute_content_hash(mem.content)

                memory_id = create_memory(
                    content=mem.content,
                    context=context,
                    type=mem.type,
                    summary=mem.summary,
                    keywords=mem.keywords,
                    importance=mem.importance,
                    source_file=mem.source_file
                )

                # Store the hash
                with get_db() as conn:
                    conn.execute(
                        "UPDATE memories SET content_hash = ? WHERE id = ?",
                        (content_hash, memory_id)
                    )

                saved += 1

            except Exception as e:
                import sys
                sys.stderr.write(f"[claude-memory] Error saving extracted memory: {e}\n")

    return saved
