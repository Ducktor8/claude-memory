---
name: context-manager:remember
description: Force saving a specific memory
---

# /context-manager:remember

Manually save a memory in the current context.

## When triggered

- `/context-manager:remember`
- "Remember this: X"
- "Save to memory: X"

## Procedure

### Interactive Mode

1. **Ask for content**:
   ```
   What do you want me to remember?
   ```

2. **Ask for type**:
   ```
   Memory type:
   1. decision - Technical/architectural decision
   2. error_fix - Bug resolved with solution
   3. pattern - Reusable pattern
   4. preference - Your preference
   5. note - Generic note
   ```

3. **Ask for importance**:
   ```
   Importance (0.1-1.0, default 0.5):
   ```

4. **Generate summary and keywords automatically**

5. **Save**:

```bash
python3 -c "
import sys
sys.path.insert(0, '$HOME/.claude/memory')
from src.lib import create_memory, detect_context

memory_id = create_memory(
    content='$CONTENT',
    context=detect_context(),
    type='$TYPE',
    summary='$SUMMARY',
    keywords=$KEYWORDS,
    importance=$IMPORTANCE
)
print(f'Memory saved with ID: {memory_id}')
"
```

6. **Confirm**:
   ```
   ✓ Memory saved!

   [#125] decision (importance: 0.8)
   Context: work
   Summary: Use PostgreSQL instead of MySQL for native JSON support
   Keywords: database, postgresql, mysql, json, choice
   ```

### Direct Mode

```
User: /context-manager:remember I always prefer using TypeScript strict mode in new projects

Claude:
✓ Memory saved!

[#126] preference (importance: 0.7)
Context: work
Summary: Preference for TypeScript strict mode in new projects
Keywords: typescript, strict, preference, projects, configuration
```

### With Explicit Type

```
User: /context-manager:remember --type error_fix The login bug was caused by cookie SameSite=Strict, resolved with SameSite=Lax

Claude:
✓ Memory saved!

[#127] error_fix (importance: 0.7)
Context: work
Summary: Login bug resolved by changing cookie from SameSite=Strict to Lax
Keywords: login, cookie, samesite, bug, authentication, security
```
