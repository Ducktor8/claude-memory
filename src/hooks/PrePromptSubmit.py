#!/usr/bin/env python3
"""
Claude Memory System - PrePromptSubmit Hook

This hook runs BEFORE the prompt is sent to Claude.
Injects relevant memories into the context based on the prompt and directory.

Input: prompt via stdin
Output: relevant memories to inject (stdout)
"""

import sys
import os
import json
import re
import traceback

# Add path for import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import ensure_initialized, get_db
from lib.context import detect_context, get_context_hierarchy, get_context
from lib.memory import search_memories, get_important_memories, get_recent_memories
from lib.migrations import ensure_migrated


def extract_keywords_advanced(text: str) -> list[str]:
    """
    Extracts keywords from text with code-aware parsing.

    Recognizes:
    - CamelCase identifiers
    - snake_case identifiers
    - CONSTANT_CASE identifiers
    - File paths and extensions
    - Technical terms
    - Error messages
    """
    keywords = set()

    # Normalize text
    text_lower = text.lower()

    # 1. CamelCase words (e.g., UserService, fetchData)
    camel_matches = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', text)
    for match in camel_matches:
        keywords.add(match.lower())
        # Also add individual parts
        parts = re.findall(r'[A-Z][a-z]+', match)
        keywords.update(p.lower() for p in parts if len(p) > 2)

    # 2. snake_case words (e.g., user_service, fetch_data)
    snake_matches = re.findall(r'\b[a-z]+(?:_[a-z]+)+\b', text_lower)
    keywords.update(snake_matches)
    # Also add individual parts
    for match in snake_matches:
        parts = match.split('_')
        keywords.update(p for p in parts if len(p) > 2)

    # 3. CONSTANT_CASE (e.g., MAX_RETRIES, API_KEY)
    const_matches = re.findall(r'\b[A-Z][A-Z0-9_]+[A-Z0-9]\b', text)
    keywords.update(c.lower() for c in const_matches)

    # 4. File paths and names
    path_matches = re.findall(r'[\w/.-]+\.[a-zA-Z]{1,4}\b', text)
    for path in path_matches:
        # Add full filename
        filename = os.path.basename(path)
        keywords.add(filename.lower())
        # Add extension
        ext = os.path.splitext(filename)[1]
        if ext:
            keywords.add(ext.lower())

    # 5. Technical terms and commands
    tech_patterns = [
        r'\b(?:npm|pip|yarn|docker|git|apt|brew)\s+\w+',  # Package managers
        r'\b(?:error|exception|bug|fix|issue|warning)\b',  # Error-related
        r'\b(?:config|setup|install|deploy|build|test)\b',  # Operations
        r'\b(?:api|rest|graphql|websocket|http|https)\b',  # Protocols
        r'\b(?:database|db|sql|postgres|mysql|mongo|redis)\b',  # Databases
        r'\b(?:react|vue|angular|svelte|next|nuxt)\b',  # Frameworks
        r'\b(?:python|javascript|typescript|rust|go|java)\b',  # Languages
    ]
    for pattern in tech_patterns:
        matches = re.findall(pattern, text_lower)
        keywords.update(matches)

    # 6. Error messages (extract key parts)
    error_patterns = [
        r"(?:error|errore)[:.\s]+([^\n]+)",
        r"(?:failed|fallito)[:.\s]+([^\n]+)",
        r"(?:cannot|impossibile)\s+(\w+)",
        r"(?:undefined|null)\s+(\w+)",
    ]
    for pattern in error_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            words = match.split()[:5]  # First 5 words of error
            keywords.update(w for w in words if len(w) > 2)

    # 7. Regular significant words (filtered)
    stopwords = {
        # Italian
        'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'di', 'da',
        'in', 'con', 'su', 'per', 'tra', 'fra', 'che', 'non', 'come', 'quando',
        'dove', 'perché', 'cosa', 'sono', 'sei', 'siamo', 'siete', 'hanno',
        'ho', 'hai', 'puoi', 'posso', 'voglio', 'vorrei', 'fammi', 'dimmi',
        'aiutami', 'per', 'favore', 'grazie', 'ciao', 'ok', 'si', 'no',
        # English
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
        'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been', 'from',
        'this', 'that', 'these', 'those', 'with', 'they', 'will', 'what',
        'when', 'where', 'which', 'who', 'whom', 'how', 'why', 'its', 'your',
        'me', 'we', 'him', 'them', 'just', 'now', 'also', 'very', 'any',
        'some', 'could', 'would', 'should', 'may', 'might', 'must', 'into',
        'than', 'then', 'there', 'their', 'only', 'other', 'more', 'most',
        'such', 'each', 'every', 'both', 'few', 'many', 'much', 'own', 'same',
        'being', 'does', 'did', 'doing', 'done', 'about', 'after', 'before',
        'between', 'through', 'during', 'without', 'again', 'further', 'once',
    }

    words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
    for word in words:
        w = word.lower()
        if w not in stopwords and len(w) > 3:
            keywords.add(w)

    # Remove very short and very common
    keywords = {k for k in keywords if len(k) > 2 and k not in stopwords}

    # Sort by length (longer = more specific) and return top 15
    sorted_keywords = sorted(keywords, key=lambda x: -len(x))
    return sorted_keywords[:15]


def format_memories_for_injection(memories: list, context: str) -> str:
    """Formats memories for context injection."""
    if not memories:
        return ""

    lines = [
        f'<relevant-memories context="{context}">',
        ""
    ]

    for mem, relevance in memories:
        type_label = {
            'decision': 'DECISION',
            'error_fix': 'FIX',
            'pattern': 'PATTERN',
            'preference': 'PREF',
            'note': 'NOTE'
        }.get(mem.type, 'NOTE')

        lines.append(f"[#{mem.id}] [{type_label}] (importance: {mem.importance})")
        lines.append(f"  {mem.summary or mem.content[:150]}")
        if mem.keywords:
            lines.append(f"  Keywords: {mem.keywords}")
        lines.append("")

    lines.append("</relevant-memories>")
    lines.append("")
    lines.append("Use these memories as context if relevant. Ignore if not applicable.")

    return '\n'.join(lines)


def log_error(hook: str, error: Exception, context: str = ""):
    """Logs error to database."""
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO error_log (hook, error_type, error_message, stack_trace, context)
                VALUES (?, ?, ?, ?, ?)
            """, (hook, type(error).__name__, str(error), traceback.format_exc(), context))
    except Exception:
        pass


def main():
    """Hook entry point."""
    try:
        ensure_initialized()
        ensure_migrated()

        # Read prompt from stdin
        prompt = sys.stdin.read().strip()

        if not prompt:
            return

        # Detect context from current directory
        cwd = os.getcwd()
        context = detect_context(cwd)

        # Extract keywords with advanced parsing
        keywords = extract_keywords_advanced(prompt)

        if not keywords:
            # No significant keywords - load important memories only
            important = get_important_memories(context=context, limit=3)
            if important:
                memories_with_score = [(m, 1.0) for m in important]
                output = format_memories_for_injection(memories_with_score, context)
                print(output)
            return

        # Build search query
        query = ' '.join(keywords)

        # Search for relevant memories
        results = search_memories(
            query=query,
            context=context,
            include_global=True,
            limit=5,
            min_importance=0.3
        )

        if results:
            output = format_memories_for_injection(results, context)
            print(output)

    except Exception as e:
        ctx = ""
        try:
            ctx = detect_context()
        except Exception:
            pass
        log_error("PrePromptSubmit", e, ctx)
        sys.stderr.write(f"[claude-memory] PrePromptSubmit error: {e}\n")


if __name__ == "__main__":
    main()
