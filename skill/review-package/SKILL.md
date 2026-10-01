---
name: review-package
description: Usare SOLO per assemblare il pacchetto di review di quasar (diff con untracked, status, output test/build, call-graph) o il solo delta dopo un verdetto non APPROVATO. Non implementa codice e non legge .env o segreti.
---

# Pacchetto di review (per quasar)

## Sequenza deterministica
1. `git add -N .` per includere gli untracked nel diff (MAI `git add` senza `-N`, MAI commit).
2. `git status --porcelain` → elenco file (modificati + untracked).
3. `git diff` → il diff.
4. Output test/build rilevante (o `n/a` con motivo se non c'è codice).
5. Call-graph a un hop sui simboli/funzioni nominati nella card (o `call-graph: n/a` + motivo).

## Completezza
Manca uno dei cinque → dichiarare "PACCHETTO INCOMPLETO" in testa, non nasconderlo.

## Redazione
- Se il diff mostra chiavi, token, `*.pem` o `.env`: sostituire con `[REDATTO]` e segnalare il path. NON aprire il file per verificare.
- Sopra ~400 righe: `stat`, elenco file, diff dei soli file in scope, nota di troncamento.

## Modalità delta (dopo un verdetto non APPROVATO)
Solo i file citati nelle riserve bloccanti + l'esito dei test dei fix. Non l'intero diff.

## Vincoli
Rover NON chiama quasar: il pacchetto risale al commander, che lo incolla nel Task di quasar.

Output: un blocco PACCHETTO.
