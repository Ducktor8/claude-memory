#!/usr/bin/env python3
"""
Claude Memory System - Stop Hook

This hook runs when Claude finishes a turn.
Analyzes the conversation and extracts memories to save.

The extraction prompt is printed to stdout to be
processed by Claude itself.
"""

import sys
import os
import json
import re
from datetime import datetime

# Add path for import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.db import ensure_initialized, get_db
from lib.context import detect_context
from lib.memory import create_memory

# Temporary file for tracking session modifications
DIRTY_FILES_PATH = os.path.expanduser("~/.claude/memory/.dirty_files")
EXTRACTION_MARKER = os.path.expanduser("~/.claude/memory/.last_extraction")


def should_extract() -> bool:
    """
    Determines if memory extraction is necessary.
    Avoids extracting on every turn.
    """
    # Extract every 5 turns or if there are modified files
    if os.path.exists(DIRTY_FILES_PATH):
        with open(DIRTY_FILES_PATH, 'r') as f:
            dirty = f.read().strip()
            if dirty:
                return True

    # Check last extraction
    if os.path.exists(EXTRACTION_MARKER):
        with open(EXTRACTION_MARKER, 'r') as f:
            try:
                data = json.load(f)
                turns_since = data.get('turns_since_extraction', 0)
                if turns_since < 5:
                    # Update counter
                    data['turns_since_extraction'] = turns_since + 1
                    with open(EXTRACTION_MARKER, 'w') as fw:
                        json.dump(data, fw)
                    return False
            except json.JSONDecodeError:
                pass

    return True


def mark_extracted():
    """Marks that extraction has been performed."""
    os.makedirs(os.path.dirname(EXTRACTION_MARKER), exist_ok=True)
    with open(EXTRACTION_MARKER, 'w') as f:
        json.dump({
            'last_extraction': datetime.now().isoformat(),
            'turns_since_extraction': 0
        }, f)

    # Clean dirty files
    if os.path.exists(DIRTY_FILES_PATH):
        os.remove(DIRTY_FILES_PATH)


def get_extraction_prompt(context: str) -> str:
    """Generates the prompt for memory extraction."""
    return f'''<memory-extraction context="{context}">
Analizza questa conversazione e identifica informazioni utili da memorizzare per sessioni future.

ESTRAI SOLO SE TROVI:
- Decisioni architetturali o tecniche significative
- Bug/errori risolti con la loro soluzione
- Pattern di codice riutilizzabili
- Preferenze espresse dall'utente
- Configurazioni o setup importanti

NON ESTRARRE:
- Codice boilerplate generico
- Comandi banali (ls, cd, git status)
- Conversazioni generiche
- Informazioni già note o ovvie

Per ogni memoria trovata, rispondi con questo JSON (e nient'altro):
```json
{{
  "memories": [
    {{
      "type": "decision|error_fix|pattern|preference|note",
      "content": "Descrizione completa della memoria",
      "summary": "Riassunto di 1-2 righe per ricerca rapida",
      "keywords": ["keyword1", "keyword2", "sinonimi"],
      "importance": 0.0-1.0
    }}
  ]
}}
```

Se non c'è nulla di significativo da memorizzare, rispondi:
```json
{{"memories": []}}
```

IMPORTANTE:
- importance 0.8-1.0: decisioni critiche, bug bloccanti risolti
- importance 0.5-0.7: pattern utili, preferenze
- importance 0.3-0.5: note generiche
- keywords: includi sinonimi per migliorare la ricerca
</memory-extraction>'''


def process_extraction_response(response: str, context: str) -> int:
    """
    Processes the extraction response and saves memories.

    Args:
        response: JSON response from Claude
        context: Current context

    Returns:
        Number of saved memories
    """
    ensure_initialized()

    # Extract JSON from response
    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
    if not json_match:
        # Try without code block
        json_match = re.search(r'\{.*"memories".*\}', response, re.DOTALL)
        if not json_match:
            return 0

    try:
        if json_match.groups():
            data = json.loads(json_match.group(1))
        else:
            data = json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return 0

    memories = data.get('memories', [])
    saved = 0

    for mem in memories:
        try:
            create_memory(
                content=mem['content'],
                context=context,
                type=mem.get('type', 'note'),
                summary=mem.get('summary'),
                keywords=mem.get('keywords'),
                importance=mem.get('importance', 0.5),
                source_session=os.environ.get('CLAUDE_SESSION_ID')
            )
            saved += 1
        except Exception as e:
            sys.stderr.write(f"[claude-memory] Error saving memory: {e}\n")

    return saved


def main():
    """Hook entry point."""
    try:
        ensure_initialized()

        if not should_extract():
            return

        # Detect context
        cwd = os.getcwd()
        context = detect_context(cwd)

        # Print extraction prompt
        print(get_extraction_prompt(context))

        mark_extracted()

    except Exception as e:
        import traceback
        sys.stderr.write(f"[claude-memory] Stop hook error: {e}\n")
        sys.stderr.write(traceback.format_exc())


if __name__ == "__main__":
    # If called with "process" argument, process the response
    if len(sys.argv) > 1 and sys.argv[1] == "process":
        response = sys.stdin.read()
        context = sys.argv[2] if len(sys.argv) > 2 else detect_context()
        saved = process_extraction_response(response, context)
        print(f"Saved {saved} memories")
    else:
        main()
