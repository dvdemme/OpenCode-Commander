#!/usr/bin/env python3
"""
Telemetria per-task del team "mission-control" (commander + subagent).

Estrae i conteggi token dei subagent (rocket/rover/hubble/antenna/quasar) da
opencode.db e ricalcola il costo con le regole di ~/.config/opencode/pricing.md
(il `cost` precalcolato da opencode NON si usa: è flat/tier-basso, senza
peak/off-peak DeepSeek né tier long-context xAI/Gemini).

Uso:
    python scripts/telemetry.py                 # auto-detect sessione commander del worktree
    python scripts/telemetry.py --session ses_xxxx
    python scripts/telemetry.py --recent 10

Fonte dati: ~/.local/share/opencode/opencode.db (tabella `session`,
righe con parent_id = sessione commander e agent in {rocket,rover,hubble,antenna,quasar}).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

# ── TARIFFE (FONTE UNICA: ~/.config/opencode/pricing.md — tenere sincronizzate) ──
# USD / 1M token.
DEEPSEEK_RATES = {
    "deepseek-v4-pro": {
        "cache_hit": {"off": 0.022, "peak": 0.044},
        "cache_miss": {"off": 0.66, "peak": 1.32},
        "output": {"off": 1.98, "peak": 3.96},
    },
    "deepseek-flash": {
        "cache_hit": {"off": 0.003, "peak": 0.006},
        "cache_miss": {"off": 0.15, "peak": 0.30},
        "output": {"off": 0.60, "peak": 1.20},
    },
}

# Google Gemini (flat). Tier promozionale gemini-3.8-flash valido fino a fine 2026.
GEMINI_RATES = {
    "gemini-3.8-flash": {"input": 0.75, "cached": 0.075, "output": 3.75},
    "gemini-3.1-flash-lite": {"input": 0.25, "cached": 0.025, "output": 1.50},
    "gemini-3.1-pro-preview": {"input": 2.00, "cached": 0.20, "output": 12.00},
}

# xAI grok-4.7 (flat). Tier per prompt TOTALE (input + cached) ≥ 200k.
XAI_RATES = {
    "grok-4.7": {
        "low": {"input": 2.00, "cached": 0.50, "output": 6.00},
        "high": {"input": 4.00, "cached": 1.00, "output": 12.00},
    },
}
XAI_LONG_CONTEXT = 200_000

# Finestra peak DeepSeek (UTC): 01:00–04:00 e 06:00–10:00, lun–ven (escl. festività cinesi).
PEAK_HOURS = ((1, 4), (6, 10))


def db_path() -> Path:
    candidates = [
        Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "opencode" / "opencode.db",
        Path.home() / ".local" / "share" / "opencode" / "opencode.db",
        Path(os.environ.get("LOCALAPPDATA", "")) / "opencode" / "opencode.db",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise SystemExit("opencode.db non trovato. Cerca in ~/.local/share/opencode/opencode.db")


def is_peak(epoch_ms: int) -> bool:
    """Peak se l'orario UTC cade nelle finestre DeepSeek (lun–ven)."""
    utc = dt.datetime.fromtimestamp(epoch_ms / 1000, tz=dt.timezone.utc)
    if utc.weekday() >= 5:
        return False
    for lo, hi in PEAK_HOURS:
        if lo <= utc.hour < hi:
            return True
    return False


def model_info(model_json: str) -> tuple[str, str]:
    """Ritorna (provider, model_id)."""
    try:
        m = json.loads(model_json)
        return m.get("providerID", "?"), m.get("id", "?")
    except (json.JSONDecodeError, AttributeError, TypeError):
        return "?", "?"


def compute_cost(
    provider: str,
    model_id: str,
    tokens_in: int,
    tokens_out: int,
    tokens_reason: int,
    cache_read: int,
    epoch_ms: int,
) -> tuple[float, str]:
    """Ricalcola il costo; ritorna (costo, note su peak/tier)."""
    out_total = tokens_out + tokens_reason  # reasoning → output (tutti i vendor)
    if provider == "xai":
        rate = XAI_RATES.get(model_id, XAI_RATES["grok-4.7"])
        prompt_total = tokens_in + cache_read
        tier = "high" if prompt_total >= XAI_LONG_CONTEXT else "low"
        r = rate[tier]
        cost = (tokens_in * r["input"] + cache_read * r["cached"] + out_total * r["output"]) / 1e6
        return cost, f"xAI tier {tier} (prompt totale {prompt_total})"
    if provider == "google":
        rate = GEMINI_RATES.get(model_id, GEMINI_RATES["gemini-3.8-flash"])
        cost = (
            tokens_in * rate["input"] + cache_read * rate["cached"] + out_total * rate["output"]
        ) / 1e6
        return cost, "Gemini flat"
    if provider == "deepseek":
        rate = DEEPSEEK_RATES.get(model_id, DEEPSEEK_RATES["deepseek-v4-pro"])
        window = "peak" if is_peak(epoch_ms) else "off"
        cost = (
            cache_read * rate["cache_hit"][window]
            + tokens_in * rate["cache_miss"][window]
            + out_total * rate["output"][window]
        ) / 1e6
        return cost, f"DeepSeek {window}"
    return 0.0, "provider sconosciuto"


def fmt(n: int | None) -> str:
    if n is None:
        return "-"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def fmt_dur(created: int, updated: int) -> str:
    secs = max(0, (updated - created) / 1000)
    if secs < 60:
        return f"{secs:.0f}s"
    m = int(secs // 60)
    return f"{m}m"


AGENTS = ("rocket", "rover", "hubble", "antenna", "quasar")
PRIMARIES = ("commander", "build", "plan")


def query(db: Path, session_id: str) -> list[dict]:
    placeholders = ",".join("?" * len(AGENTS))
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"SELECT id, agent, model, tokens_input, tokens_output, tokens_reasoning, "
        f"tokens_cache_read, tokens_cache_write, time_created, time_updated, title "
        f"FROM session WHERE parent_id = ? AND agent IN ({placeholders}) "
        f"ORDER BY time_created",
        (session_id, *AGENTS),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def task_id(title: str | None) -> str:
    """Estrae l'id task dal titolo; fallback sul titolo intero."""
    m = re.search(r"\b([A-Z]+\d+[a-z]?)\b", title or "")
    return m.group(1) if m else (title or "task")


def render(rows: list[dict]) -> str:
    header = "| Agente | Modello | Costo | in | out | reason | cache_read | durata |"
    sep = "|---|---|---|---|---|---|---|---|---|"

    groups: dict[str, list[tuple[dict, float]]] = {}
    order: list[str] = []
    grand = 0.0
    for r in rows:
        provider, model_id = model_info(r["model"])
        cost, _ = compute_cost(
            provider,
            model_id,
            r["tokens_input"] or 0,
            r["tokens_output"] or 0,
            r["tokens_reasoning"] or 0,
            r["tokens_cache_read"] or 0,
            r["time_created"] or 0,
        )
        grand += cost
        key = task_id(r["title"])
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append((r, cost))

    lines: list[str] = []
    for key in order:
        lines.append(f"**{key}**")
        lines.append(header)
        lines.append(sep)
        subtotal = 0.0
        for r, cost in groups[key]:
            provider, model_id = model_info(r["model"])
            subtotal += cost
            dur = fmt_dur(r["time_created"], r["time_updated"])
            lines.append(
                f"| {r['agent']} | {model_id} | ${cost:.3f} | {fmt(r['tokens_input'])} "
                f"| {fmt(r['tokens_output'])} | {fmt(r['tokens_reasoning'])} "
                f"| {fmt(r['tokens_cache_read'])} | {dur} |"
            )
        lines.append(f"→ subtotale {key}: ${subtotal:.3f}\n")
    lines.append(f"**Totale subagent: ${grand:.3f}**")
    return "\n".join(lines)


def autodetect_session(db: Path) -> str | None:
    """Ultima sessione primaria (commander/build/plan, parent_id NULL) del worktree corrente."""
    cwd = str(Path.cwd()).replace("\\", "/").rstrip("/")
    placeholders = ",".join("?" * len(PRIMARIES))
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        f"SELECT id, directory FROM session "
        f"WHERE agent IN ({placeholders}) AND parent_id IS NULL "
        f"AND directory = ? ORDER BY time_created DESC LIMIT 1",
        (*PRIMARIES, cwd),
    ).fetchone()
    if row is None:
        row = conn.execute(
            f"SELECT id, directory FROM session "
            f"WHERE agent IN ({placeholders}) AND parent_id IS NULL "
            f"AND directory = ? COLLATE NOCASE ORDER BY time_created DESC LIMIT 1",
            (*PRIMARIES, cwd),
        ).fetchone()
    conn.close()
    return row["id"] if row else None


def list_recent(db: Path, n: int) -> None:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, agent, model, title, time_created FROM session "
        "WHERE agent IN ('commander', 'rocket', 'rover', 'hubble', 'antenna', 'quasar', 'plan', 'build') "
        "ORDER BY time_created DESC LIMIT ?",
        (n,),
    ).fetchall()
    conn.close()
    for r in rows:
        provider, model_id = model_info(r["model"])
        t = dt.datetime.fromtimestamp(r["time_created"] / 1000).strftime("%Y-%m-%d %H:%M")
        print(f"{r['id']}  agent={r['agent']}  model={model_id}  {t}  {r['title']}")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    ap = argparse.ArgumentParser(description="Telemetria per-task (commander → subagent).")
    ap.add_argument("--session", help="ID della sessione commander (default: auto-detect ultima sessione primaria del worktree)")
    ap.add_argument("--recent", type=int, metavar="N", help="elenca le ultime N sessioni")
    args = ap.parse_args()

    db = db_path()
    if args.recent:
        list_recent(db, args.recent)
        return

    session_id = args.session or autodetect_session(db)
    if not session_id:
        print("Nessuna sessione commander trovata per il worktree corrente. Usa --session <id> o --recent N.", file=sys.stderr)
        sys.exit(1)

    rows = query(db, session_id)
    if not rows:
        print(f"Nessun subagent trovato per la sessione {session_id}.", file=sys.stderr)
        sys.exit(1)
    print(f"### Telemetria (sessione {session_id})\n")
    print(render(rows))


if __name__ == "__main__":
    main()
