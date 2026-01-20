#!/usr/bin/env python3
"""
Claude Memory System - Search CLI

Utility for searching memories from the command line.
Used by the context-manager:search skill.
"""

import sys
import os
import argparse
import json

# Add path for import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import ensure_initialized
from lib.context import detect_context
from lib.memory import search_memories, get_recent_memories, get_important_memories


def format_results(results: list, format_type: str = "detailed") -> str:
    """Formats search results."""
    if not results:
        return "No memories found."

    lines = []

    if format_type == "detailed":
        for mem, relevance in results:
            type_emoji = {
                'decision': '🎯',
                'error_fix': '🔧',
                'pattern': '📐',
                'preference': '⭐',
                'note': '📝'
            }.get(mem.type, '📝')

            lines.append(f"[#{mem.id}] {type_emoji} {mem.type} (importance: {mem.importance})")
            lines.append(f"  Context: {mem.context}")
            lines.append(f"  {mem.summary or mem.content[:150]}")
            if mem.keywords:
                lines.append(f"  Keywords: {mem.keywords}")
            lines.append(f"  Created: {mem.created_at}")
            lines.append("")

    elif format_type == "compact":
        for mem, relevance in results:
            lines.append(f"[#{mem.id}] {mem.type}: {mem.summary or mem.content[:80]}")

    elif format_type == "json":
        data = [{
            'id': mem.id,
            'type': mem.type,
            'context': mem.context,
            'summary': mem.summary,
            'content': mem.content,
            'keywords': mem.keywords,
            'importance': mem.importance,
            'relevance': relevance,
            'created_at': mem.created_at
        } for mem, relevance in results]
        return json.dumps(data, indent=2, ensure_ascii=False)

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description="Search Claude memories")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--context", "-c", help="Context to search in")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Max results")
    parser.add_argument("--format", "-f", choices=["detailed", "compact", "json"],
                        default="detailed", help="Output format")
    parser.add_argument("--min-importance", "-i", type=float, default=0.0,
                        help="Minimum importance")
    parser.add_argument("--recent", "-r", action="store_true",
                        help="Show recent memories instead of searching")
    parser.add_argument("--important", action="store_true",
                        help="Show important memories instead of searching")
    parser.add_argument("--no-global", action="store_true",
                        help="Exclude global context from results")

    args = parser.parse_args()

    ensure_initialized()

    # Detect context if not specified
    context = args.context or detect_context()

    print(f"Context: {context}" + (" (+ global)" if not args.no_global else ""))
    print()

    if args.recent:
        memories = get_recent_memories(limit=args.limit, context=context)
        results = [(m, 1.0) for m in memories]
        print(f"Recent memories:")
    elif args.important:
        memories = get_important_memories(
            context=context,
            min_importance=args.min_importance or 0.7,
            limit=args.limit
        )
        results = [(m, 1.0) for m in memories]
        print(f"Important memories (>={args.min_importance or 0.7}):")
    elif args.query:
        results = search_memories(
            query=args.query,
            context=context,
            include_global=not args.no_global,
            limit=args.limit,
            min_importance=args.min_importance
        )
        print(f"Query: \"{args.query}\"")
    else:
        # Show recent if no query
        memories = get_recent_memories(limit=args.limit, context=context)
        results = [(m, 1.0) for m in memories]
        print(f"Recent memories:")

    print()
    print(format_results(results, args.format))
    print(f"\nFound {len(results)} memories.")


if __name__ == "__main__":
    main()
