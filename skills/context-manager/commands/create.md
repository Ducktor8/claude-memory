---
name: context-manager:create
description: Create a new memory context with interactive wizard
---

# /context-manager:create

Create a new memory context.

## When triggered

When the user invokes `/context-manager:create` or asks to "create a new context".

## Procedure

1. **Ask for the name** (required):
   ```
   Context name (lowercase, no spaces):
   ```
   - Validate: only letters, numbers, hyphens
   - Example: `crypto-bot`, `project-xyz`

2. **Ask for the description**:
   ```
   Short description of the context:
   ```

3. **Ask for associated directories**:
   ```
   Associated directories (glob patterns, one per line, empty to finish):
   Example: ~/projects/crypto-bot/*
   ```
   - Supports glob: `*`, `**`
   - Supports `~` for home

4. **Ask for parent context** (optional):
   ```
   Parent context for inheritance [none]:
   ```
   - If specified, inherits memories from parent
   - Example: `trading` for a trading bot

5. **Execute creation**:

```bash
python3 ~/.claude/memory/lib/context.py create \
  --name "$NAME" \
  --description "$DESCRIPTION" \
  --patterns $PATTERNS \
  --parent "$PARENT"
```

6. **Confirm to user**:
   ```
   ✓ Context 'name' created successfully!
   ✓ File: ~/.claude/memory/contexts/name.md
   ✓ Mapped directories: ~/path1/*, ~/path2/*
   ✓ Parent: trading (inherits memories)

   Use /context-manager:switch name to activate it manually.
   ```

## Complete Example

```
User: /context-manager:create

Claude: Context name (lowercase, no spaces):

User: crypto-bot

Claude: Short description of the context:

User: Automated bot for crypto trading

Claude: Associated directories (one per line, empty to finish):

User: ~/projects/crypto-bot/*
~/trading/bots/crypto/*

Claude: Parent context for inheritance [none]:

User: trading

Claude:
✓ Context 'crypto-bot' created successfully!
✓ File: ~/.claude/memory/contexts/crypto-bot.md
✓ Mapped directories: ~/projects/crypto-bot/*, ~/trading/bots/crypto/*
✓ Parent: trading (inherits memories from trading and global)

When working in these directories, the context will be detected automatically.
Use /context-manager:switch crypto-bot to activate it manually.
```
