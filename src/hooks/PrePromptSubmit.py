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

# Add path for import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import ensure_initialized
from lib.context import detect_context, get_context_hierarchy, get_context
from lib.memory import search_memories, get_important_memories, get_recent_memories


def extract_keywords_simple(text: str) -> list[str]:
    """
    Extracts simple keywords from text.
    Does not use NLP, only basic pattern matching.
    """
    # Remove punctuation
    text = re.sub(r'[^\w\s]', ' ', text.lower())

    # Words to ignore (basic Italian + English stopwords)
    stopwords = {
        'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una',
        'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
        'che', 'non', 'come', 'quando', 'dove', 'perché', 'cosa',
        'sono', 'sei', 'è', 'siamo', 'siete', 'hanno', 'ho', 'hai',
        'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
        'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'must',
        'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
        'this', 'that', 'these', 'those', 'it', 'its', 'my', 'your',
        'what', 'which', 'who', 'whom', 'how', 'when', 'where', 'why',
        'me', 'you', 'we', 'they', 'him', 'her', 'them', 'us',
        'can', 'just', 'now', 'also', 'very', 'all', 'any', 'some',
        'puoi', 'posso', 'voglio', 'vorrei', 'fammi', 'dimmi', 'aiutami',
        'per', 'favore', 'grazie', 'ciao', 'ok', 'si', 'no'
    }

    # Extract significant words (>2 characters, not stopwords)
    words = text.split()
    keywords = [w for w in words if len(w) > 2 and w not in stopwords]

    # Remove duplicates while maintaining order
    seen = set()
    unique = []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            unique.append(w)

    return unique[:10]  # Maximum 10 keywords


def format_memories_for_injection(memories: list, context: str) -> str:
    """Formats memories for context injection."""
    if not memories:
        return ""

    lines = [
        f'<relevant-memories context="{context}">',
        ""
    ]

    for mem, relevance in memories:
        type_emoji = {
            'decision': '🎯',
            'error_fix': '🔧',
            'pattern': '📐',
            'preference': '⭐',
            'note': '📝'
        }.get(mem.type, '📝')

        lines.append(f"[#{mem.id}] {type_emoji} {mem.type} (importance: {mem.importance})")
        lines.append(f"  {mem.summary or mem.content[:100]}")
        if mem.keywords:
            lines.append(f"  Keywords: {mem.keywords}")
        lines.append("")

    lines.append("</relevant-memories>")
    lines.append("")
    lines.append("Use these memories as context. If they are not relevant, ignore them.")

    return '\n'.join(lines)


def main():
    """Hook entry point."""
    try:
        ensure_initialized()

        # Read prompt from stdin
        prompt = sys.stdin.read().strip()

        if not prompt:
            return

        # Detect context from current directory
        cwd = os.getcwd()
        context = detect_context(cwd)

        # Extract keywords from prompt
        keywords = extract_keywords_simple(prompt)

        if not keywords:
            # No significant keywords, load only recent important memories
            important = get_important_memories(context=context, limit=3)
            if important:
                memories_with_score = [(m, 1.0) for m in important]
                output = format_memories_for_injection(memories_with_score, context)
                print(output)
            return

        # Build query for FTS5 (space-separated keywords, search_memories adds OR)
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
        # Log error but don't block the prompt
        import traceback
        sys.stderr.write(f"[claude-memory] PrePromptSubmit error: {e}\n")
        sys.stderr.write(traceback.format_exc())


if __name__ == "__main__":
    main()
