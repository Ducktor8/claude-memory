---
name: context-manager:switch
description: Change the active context (override auto-detection)
---

# /context-manager:switch <name>

Manually change the active context, overriding directory-based auto-detection.

## When triggered

- `/context-manager:switch <name>`
- "Switch to context X"
- "Use context Y"

## Procedure

1. **Validate context**:
   - Verify that the context exists
   - If it doesn't exist, suggest `/context-manager:create`

2. **Set override**:

```bash
echo "$CONTEXT_NAME" > ~/.claude/memory/.context_override
```

3. **Confirm**:
   ```
   ✓ Context changed to: name
   ✓ Hierarchy loaded: global → parent → name
   ✓ Override active until /context-manager:switch --auto
   ```

## Special Arguments

- `/context-manager:switch --auto` - Remove override and return to auto-detection
- `/context-manager:switch --list` - Show available contexts (alias of /context-manager:list)

## Example

```
User: /context-manager:switch trading

Claude:
✓ Context changed to: trading

Context statistics:
- Total memories: 23
- Decisions: 5
- Patterns: 8
- Resolved errors: 10

Override active. Use /context-manager:switch --auto to return to auto-detection.
```

```
User: /context-manager:switch --auto

Claude:
✓ Override removed
✓ Auto-detection reactivated
✓ Current context (from directory): work
```
