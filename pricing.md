# Pricing — team "mission-control" (fonte unica prezzi)

> **Scopo:** fonte unica dei prezzi API per il calcolo dei costi nella telemetria per-task.
> Il commander NON usa prezzi "a memoria": legge questo file.
> **Currency:** USD · **last_verified:** 2026-10-02 · **refresh:** ogni 7 giorni (se `last_verified`
> è più vecchio, fare webfetch dei link sorgente e aggiornare la tabella).

## Modelli in uso

| Agente | Modello |
|---|---|
| commander, rocket | `deepseek/deepseek-v4-pro` |
| rover | `deepseek/deepseek-flash` |
| hubble, antenna | `google/gemini-3.8-flash` |
| quasar | `xai/grok-4.7` |

## Prezzi (USD / 1M token)

### DeepSeek (peak/off-peak + cache)

| Modello | Input cache-hit off/peak | Input cache-miss off/peak | Output off/peak |
|---|---|---|---|
| `deepseek-flash` | 0.003 / 0.006 | 0.15 / 0.30 | 0.60 / 1.20 |
| `deepseek-v4-pro` | 0.022 / 0.044 | 0.66 / 1.32 | 1.98 / 3.96 |

- **Off-peak = metà del peak** (peak = ×2 off-peak).
- **Finestra peak (UTC):** 01:00–04:00 e 06:00–10:00, lunedì–venerdì (escluse festività cinesi).
- **Italia:** inverno (CET, UTC+1) peak 02:00–05:00 e 07:00–11:00 · estate (CEST, UTC+2) peak 03:00–06:00 e 08:00–12:00.

### Google Gemini (flat, nessun peak/off-peak)

| Modello | Input | Cached input | Output (resp + reasoning) |
|---|---|---|---|
| `gemini-3.8-flash` | 0.75 | 0.075 | 3.75 |
| `gemini-3.1-flash-lite` | 0.25 | 0.025 | 1.50 |
| `gemini-3.1-pro-preview` | 2.00 | 0.20 | 12.00 |

- **`gemini-3.8-flash` è a prezzo promozionale fino al 2026-12-31**; dal 2027-01-01 passa a
  $1.50 / $7.50 (input/output). Verificare prima di ogni calcolo se la data è superata.
- **Long-context (>200k prompt):** `gemini-3.1-pro-preview` sale a $4.00 input / $18.00 output.
  Per i task brevi di hubble/antenna si usa il tier ≤200k.

### xAI `grok-4.7` (flat, nessun peak/off-peak)

| Prompt tokens | Input | Cached input | Output |
|---|---|---|---|
| < 200k | $2.00 | $0.50 | $6.00 |
| ≥ 200k | $4.00 | $1.00 | $12.00 |

- **Long-context:** la soglia ≥ 200k va calcolata sul **prompt totale = input + cached input**.
  Oltre soglia, TUTTI i token della richiesta sono fatturati al rate più alto.

## Regola di calcolo (per il commander)

1. Leggi i prezzi da questo file (non a memoria).
2. Registra **sempre l'orario UTC** del task.
3. **DeepSeek:** peak se l'orario UTC cade in 01:00–04:00 o 06:00–10:00 lun–ven; altrimenti off-peak.
4. **Gemini:** flat; usa il tier promozionale di `gemini-3.8-flash` solo se la data è ≤ 2026-12-31.
5. **xAI:** usa il tier `< 200k` (review brevi di quasar); se il prompt ≥ 200k, rate più alto.
6. **Cache:** usa lo split cache-hit/cache-miss dai dati di utilizzo se disponibile; altrimenti
   assumi cache-miss e dichiaralo.
7. **Reasoning tokens:** somma i `tokens_reasoning` all'**output** al rate output del modello.

## Fonte dei token (dati di utilizzo)

I conteggi token per-agente (`tokens_input/output/reasoning/cache_read/cache_write` + orari)
NON arrivano dal tool `Task`: vivono in **`opencode.db`** (tabella `session`, righe con
`parent_id` = sessione commander). Estraili e ricalcola con:

```
python ~/.config/opencode/scripts/telemetry.py --session <commander_id>   # report per-task
python ~/.config/opencode/scripts/telemetry.py --recent 10                # ultime sessioni
```

Il `cost` precalcolato da opencode **non si usa** (flat/tier-basso, senza peak/off-peak DeepSeek
né tier long-context xAI/Gemini: sottostima).

## Note

- La "Tools Pricing" di xAI (web_search, x_search, code_execution, ecc.) **NON si applica**:
  quasar usa i tool locali di opencode (read/grep/git diff/log/status), non i server-side xAI.

## Link sorgente

- **DeepSeek:** https://api-docs.deepseek.com/quick_start/pricing
- **xAI:** https://docs.x.ai/developers/pricing (primario) · https://docs.x.ai/docs/models (backup)
- **Gemini:** https://ai.google.dev/gemini-api/docs/pricing (primario) · https://cloud.google.com/vertex-ai/generative-ai/pricing (backup)
