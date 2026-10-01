# OpenCode Commander

Un "team" di agenti AI per [opencode](https://opencode.ai): un orchestratore (`commander`) che pianifica, decompone e delega a un equipaggio di subagent specializzati, con revisione incrociata multi-vendor e controllo costo/beneficio.

Tre vendor indipendenti (DeepSeek, Google/Gemini, xAI/Grok), ognuno usato dove rende di più.

## Requisiti

- [opencode](https://opencode.ai) installato (consigliata l'ultima versione).
- Una o più chiavi API: DeepSeek, Google, xAI (vedi FAQ se ne hai una sola).

## Installazione (guidata)

```bash
git clone https://github.com/dvdemme/OpenCode-Commander.git
cd OpenCode-Commander
./install.sh          # oppure: ./install.sh --copy
```

`install.sh` ti guida passo-passo:

1. verifica che opencode sia installato;
2. configura i provider (le chiavi vengono chieste da `opencode auth login`, non da questo script);
3. collega agenti + skill nel tuo `~/.config/opencode/`;
4. (opzionale) imposta `commander` come modello di default;
5. verifica l'installazione.

Poi **riavvia opencode** e lancia:

```bash
opencode --agent commander
```

## Il team

| Agente | Modello | Ruolo |
|---|---|---|
| `commander` | DeepSeek V4 Pro | orchestra, delega, integra |
| `rocket` | DeepSeek V4 Pro | implementa codice e test |
| `rover` | DeepSeek Flash | task meccanici/ripetitivi |
| `hubble` | Gemini Flash | interpreta immagini/diagrammi |
| `antenna` | Gemini Flash | review soft "anticipata" |
| `quasar` | Grok 4.7 | review deep "finale" |

## Skill automatiche

- `task-card` — card di delega prima di ogni Task.
- `review-package` — pacchetto per la review di `quasar`.
- `close-task` — handoff + snapshot costi a fine task.

Le skill si caricano da sole quando servono (l'utente non le invoca): il `commander` le attiva con giudizio.

## Aggiornamento

```bash
cd OpenCode-Commander && git pull
```

Con l'installazione via symlink (default) l'aggiornamento è automatico: `git pull` aggiorna i file collegati.

## FAQ

**Ho una sola chiave (es. solo DeepSeek).** Puoi installare lo stesso: `quasar` (xAI) e `antenna`/`hubble` (Google) non risponderanno finché non configuri quei provider. Configurali dopo con `opencode auth login -p <id>`.

**Posso saltare un provider?** Sì, l'installer te lo chiede per ciascuno. Se salti, gli agenti collegati restano inattivi (ma il resto funziona).

**Windows?** Non ancora supportato (v2).

**Dove finiscono i file?** In `~/.config/opencode/` (agenti in `agent/`, skill in `skill/`, supporto in `scripts/`).

## Licenza

MIT
