---
name: context-manager:forget
description: Remove a memory from the database
---

# /context-manager:forget <id>

Delete a specific memory from the database.

## When triggered

- `/context-manager:forget <id>`
- "Forget memory #X"
- "Remove memory X"

## Procedure

1. **Show memory to delete**:

```bash
python3 -c "
import sys
sys.path.insert(0, '$HOME/.claude/memory')
from src.lib import get_memory

mem = get_memory($ID)
if mem:
    print(f'ID: {mem.id}')
    print(f'Type: {mem.type}')
    print(f'Context: {mem.context}')
    print(f'Summary: {mem.summary}')
    print(f'Content: {mem.content[:200]}')
"
```

2. **Ask for confirmation**:
   ```
   You are about to delete this memory:

   [#42] decision - work
   Use docker-compose for local development environment

   Confirm? (yes/no)
   ```

3. **If confirmed, delete**:

```bash
python3 -c "
import sys
sys.path.insert(0, '$HOME/.claude/memory')
from src.lib import delete_memory

if delete_memory($ID):
    print('✓ Memory deleted')
else:
    print('✗ Memory not found')
"
```

4. **Confirm**:
   ```
   ✓ Memory #42 deleted from context 'work'
   ```

## Multiple Deletion

```
User: /context-manager:forget 42 43 45

Claude:
You are about to delete 3 memories:
- [#42] decision: Use docker-compose...
- [#43] pattern: Multi-stage build...
- [#45] note: Consider Kubernetes...

Confirm? (yes/no)

User: yes

Claude:
✓ 3 memories deleted
```

## Security Note

- Deletions are permanent
- Confirmation is always required
- The context.md file is updated automatically
