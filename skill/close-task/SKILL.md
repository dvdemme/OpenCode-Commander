---
name: close-task
description: Usare SOLO a fine task o prima di fermare la sessione. Scrive l'handoff sul worklog (fatto, pendente, prossimi passi, decisioni, assunzioni, verdetti) e lo snapshot di costo (pricing, telemetria, KPI). Non aprire .env, credenziali o database a mano.
---

# Chiusura task (handoff + snapshot costi)

## 1. Handoff
Aggiorna il worklog esistente (non riscriverlo); se manca, crea `WORKLOG.md` alla root del progetto.
Sezioni (solo queste):
- **Fatto** — completato e verificato.
- **Pendente** — ciò che resta.
- **Prossimi passi** — azioni concrete per la prossima sessione.
- **Decisioni** — una riga ciascuna.
- **Assunzioni aperte** — da verificare.
- **Verdetti** — esito antenna/quasar (se presenti).

## 2. Snapshot costi
1. Leggi `~/.config/opencode/pricing.md` (fonte unica prezzi).
2. `last_verified` assente o > 7 giorni → webfetch dei link già nel file e aggiorna tabella + data. Fetch fallito → `prezzi: STALE` (non bloccare, non inventare prezzi).
3. Token SOLO via `python ~/.config/opencode/scripts/telemetry.py --session <commander_id>` (o `--recent N`). MAI query a mano sul database.
4. KPI solo quelli del kernel: rejection rate (se c'è storico), costo antenna vs ~50% del quasar atteso, $/gate.

## Regole
- Niente diff, log interi o segreti nel worklog.
- Non aprire `.env`, credenziali o database a mano.
- Input mancante → `n/d`; costi mancanti → `costo: non misurato` (mai cifre inventate).

Output: blocco handoff + blocco costi (8–12 righe) da appendere al worklog.
