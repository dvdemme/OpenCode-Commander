---
name: task-card
description: Usare SOLO subito prima di una chiamata Task a rocket, rover, hubble, antenna o quasar. Produce la task card da incollare nel prompt del subagent: obiettivo, done, file, vincoli, assunzioni, output atteso. Non usarla per routing, escalation o per decidere i gate.
---

# Task card

Produci UNA task card per subagent, da incollare tale e quale nel prompt del Task.
Se il lavoro mescola meccanico e design, spezza in due card (rover + rocket).

## Campi obbligatori (mai omettere)
- **id** — identificatore breve del task.
- **agente** — chi la esegue.
- **obiettivo** — una frase.
- **done verificabile** — come si dimostra finito (test/build/lint specifici).
- **path in scope / fuori scope** — file e dir espliciti.
- **vincoli** — niente commit/push/deploy; niente scope extra; niente librerie nuove se non richieste.
- **assunzioni** — `ASSUNTO` (non verificato) / `NON NOTO` (dato mancante).
- **input già estratti** — spec/contesto rilevante incluso qui (il subagent NON fa grep).
- **formato report di ritorno** — cosa deve riportare.

## Regole per destinatario
- **rocket**: includi il piano richiesto prima del codice (serve al gate `antenna`).
- **rover**: se serve il pacchetto di review, aggiungi la frase "carica `review-package`".
- **quasar**: la card contiene il pacchetto di review, non "esplora il repo".
- **antenna**: la card è la checklist chiusa + il piano/diff da valutare.

## Vietato
- Segreti, token, contenuto di `.env`.
- "Ignora le regole" o istruzioni che scavalcano il kernel.

Output: SOLO il blocco card.
