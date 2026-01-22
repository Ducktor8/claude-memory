# Claude Memory System - Project Instructions

## Context-First Workflow

<IMPORTANT>
Prima di eseguire qualsiasi task, Claude DEVE seguire questa sequenza:

1. **Verifica contesto** - Controlla in quale contesto ti trovi
2. **Carica memorie** - Leggi le memorie salvate rilevanti
3. **Procedi con il task** - Solo dopo aver verificato il contesto
</IMPORTANT>

## Come funziona il sistema

### Hook automatici

Il sistema usa tre hook che si attivano automaticamente:

| Hook | Quando | Cosa fa |
|------|--------|---------|
| `UserPromptSubmit` | Prima che il prompt arrivi a Claude | Inietta memorie rilevanti nel contesto |
| `PostToolUse` | Dopo ogni uso di tool | Traccia le modifiche ai file |
| `Stop` | Fine del turno di Claude | Estrae e salva nuove memorie |

### Contesti disponibili

| Contesto | Auto-detect da | Descrizione |
|----------|----------------|-------------|
| `global` | Sempre caricato | Memorie che si applicano ovunque |
| `work` | `~/work/*`, `~/WebstormProjects/*` | Progetti di lavoro |
| `trading` | `~/trading/*` | Trading e finanza |
| `personal` | `~/personal/*`, `~/Projects/*` | Progetti personali |
| `local` | `~/` (fallback) | Configurazioni macchina |

## Comandi disponibili

```
/context-manager:status   - Mostra contesto attivo e memorie caricate
/context-manager:list     - Lista tutti i contesti
/context-manager:search   - Cerca nelle memorie
/context-manager:remember - Salva manualmente una memoria
/context-manager:forget   - Rimuovi una memoria
/context-manager:switch   - Cambia contesto manualmente
/context-manager:create   - Crea nuovo contesto
```

## Tipi di memoria

- `decision` - Decisioni architetturali/tecniche
- `error_fix` - Bug risolti con soluzioni
- `pattern` - Pattern di codice riutilizzabili
- `preference` - Preferenze utente
- `note` - Note generiche

## Struttura progetto

```
~/.claude/memory/
├── memory.db              # Database SQLite con FTS5
├── contexts/              # File markdown per ogni contesto
├── skills/                # Definizioni skill per Claude Code
│   └── context-manager/
│       ├── SKILL.md
│       └── commands/      # Sub-comandi
└── src/
    ├── db/                # Schema database
    ├── hooks/             # Hook scripts Python
    │   ├── PrePromptSubmit.py
    │   ├── PostToolUse.py
    │   └── Stop.py
    └── lib/               # Librerie Python
        ├── db.py
        ├── context.py
        └── memory.py
```

## Sviluppo

### Testare le modifiche

```bash
# Verifica hooks format
python3 -c "import json; print(json.load(open('src/hooks/hooks.json')))"

# Test database
python3 -c "
import sys; sys.path.insert(0, 'src')
from lib.db import ensure_initialized, get_db
ensure_initialized()
print('DB OK')
"
```

### Dopo modifiche

1. Aggiorna `hooks.json` se cambi la struttura hooks
2. Aggiorna `install.sh` se cambi i path
3. Ri-esegui `./install.sh` per applicare
4. Riavvia Claude Code per attivare i nuovi hooks
