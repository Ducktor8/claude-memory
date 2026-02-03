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
| `PostToolUse` | Dopo ogni uso di tool | Traccia le modifiche ai file per auto-save |
| `Stop` | Fine del turno di Claude | Estrae e salva automaticamente nuove memorie |

### Auto-Save

Il sistema salva automaticamente memorie quando:
- File di configurazione vengono modificati (package.json, config.ini, etc.)
- Pacchetti vengono installati (npm, pip, etc.)
- Operazioni git significative vengono eseguite
- Pattern di codice vengono creati
- Errori vengono risolti

### Deduplicazione

Le memorie duplicate vengono rilevate tramite:
- Hash del contenuto normalizzato
- Ricerca FTS per similarità semantica
- Soglia di similarità del 70%

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
/context-manager:map      - Gestisci mapping directory -> contesto
/context-manager:export   - Esporta memorie in JSON
/context-manager:import   - Importa memorie da JSON
/context-manager:errors   - Mostra log errori
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
    │   └── schema.sql
    ├── hooks/             # Hook scripts Python
    │   ├── PrePromptSubmit.py
    │   ├── PostToolUse.py
    │   └── Stop.py
    └── lib/               # Librerie Python
        ├── db.py          # Connessione database
        ├── context.py     # Gestione contesti
        ├── memory.py      # CRUD memorie
        ├── extractor.py   # Auto-estrazione memorie
        ├── migrations.py  # Migrazioni schema DB
        └── backup.py      # Export/Import
```

## Sviluppo

### Eseguire i test

```bash
pip install pytest
pytest tests/ -v
```

### Testare le modifiche

```bash
# Verifica database
python3 -c "
import sys; sys.path.insert(0, 'src')
from lib.db import ensure_initialized, get_stats
ensure_initialized()
print(get_stats())
"

# Test migrazioni
python3 src/lib/migrations.py
```

### Dopo modifiche

1. Aggiorna `schema.sql` e `migrations.py` se cambi lo schema
2. Aggiorna `install.sh` se cambi i path
3. Ri-esegui `./install.sh` per applicare
4. Riavvia Claude Code per attivare i nuovi hook
5. Esegui `pytest tests/` per verificare che tutto funzioni
