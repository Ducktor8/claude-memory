---
name: context-manager:search
description: Search memories in the current context
---

# /context-manager:search <query>

Search memories using full-text search.

## When triggered

- `/context-manager:search <query>`
- "Search memories: X"
- "What do you remember about X?"

## Procedure

1. **Execute search**:

```bash
python3 ~/.claude/memory/src/hooks/search.py "$QUERY" \
  --context "$CONTEXT" \
  --limit 10 \
  --format detailed
```

2. **Show results**:

```
Context: work (+ global)
Query: "docker deploy"

[#42] decision (importance: 0.8) - 2026-01-15
  Use docker-compose for local development environment
  Keywords: docker, compose, container, dev, development
  Context: work

[#38] error_fix (importance: 0.7) - 2026-01-14
  Docker build failed due to invalid cache - resolved with --no-cache
  Keywords: docker, build, cache, error

[#25] pattern (importance: 0.6) - 2026-01-10
  Pattern: multi-stage build for lighter images
  Keywords: docker, build, multi-stage, optimization

Found 3 memories.
```

## Advanced Options

- `/context-manager:search <query> --all` - Search in all contexts
- `/context-manager:search <query> --type decision` - Filter by type
- `/context-manager:search --recent` - Show recent memories (no query)
- `/context-manager:search --important` - Show important memories (>0.7)

## Interactive Example

```
User: /context-manager:search cors

Claude:
Context: work (+ global)
Query: "cors"

[#120] error_fix (importance: 0.8) - 2026-01-18
  CORS error in development - resolved by adding proxy in vite.config.ts
  Keywords: cors, vite, proxy, frontend, api, error

  Full content:
  The frontend on localhost:5173 could not call the API on localhost:3000.
  Solution: add proxy in vite.config.ts:
  server: { proxy: { '/api': 'http://localhost:3000' } }

[#85] pattern (importance: 0.5) - 2026-01-05
  Pattern: handle CORS in Express with middleware
  Keywords: cors, express, middleware, backend

Found 2 memories. Use /context-manager:forget <id> to remove one.
```
