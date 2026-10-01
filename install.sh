#!/usr/bin/env bash
#
# install.sh — installa "OpenCode Commander" nel tuo opencode globale.
#
# Guida interattiva: configura i provider (deepseek/xai/google), collega i file
# (agenti + skill + supporto) e opzionalmente imposta commander come default.
#
# Uso:
#   ./install.sh           symlink (consigliato: `git pull` aggiorna tutto da solo)
#   ./install.sh --copy    copia i file (nessun aggiornamento automatico)
#
# Supportato: macOS + Linux (bash 3.2+). Windows: non ancora (v2).

set -u

# ── colori ────────────────────────────────────────────────────────────────
BOLD="$(tput bold 2>/dev/null || printf '')"
GREEN="$(tput setaf 2 2>/dev/null || printf '')"
YELLOW="$(tput setaf 3 2>/dev/null || printf '')"
RED="$(tput setaf 1 2>/dev/null || printf '')"
RESET="$(tput sgr0 2>/dev/null || printf '')"

CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="symlink"   # symlink | copy

PROVIDERS="deepseek xai google"

say()  { printf '%b\n' "$*"; }
ok()   { say "${GREEN}✓${RESET} $*"; }
warn() { say "${YELLOW}⚠${RESET} $*"; }
err()  { say "${RED}✗${RESET} $*"; }
step() { say ""; say "${BOLD}── $* ──${RESET}"; }

provider_label() { case "$1" in
  deepseek) echo "DeepSeek" ;;
  xai)      echo "xAI (Grok)" ;;
  google)   echo "Google (Gemini)" ;;
  *)        echo "$1" ;;
esac; }

provider_agents() { case "$1" in
  deepseek) echo "commander, rocket, rover" ;;
  xai)      echo "quasar" ;;
  google)   echo "antenna, hubble" ;;
  *)        echo "?" ;;
esac; }

is_authenticated() { # $1 = provider_id
  opencode auth list 2>/dev/null | grep -qi "$1"
}

usage() {
  say "Uso: ./install.sh [--copy] [--help]"
  say "  --copy   copia i file invece di creare symlink"
}

provider_setup() {
  step "Provider (chiavi API)"
  say "Il team usa tre vendor; ogni agente ha un suo modello:"
  say "  ${BOLD}DeepSeek${RESET}  → commander, rocket, rover"
  say "  ${BOLD}xAI${RESET}       → quasar"
  say "  ${BOLD}Google${RESET}    → antenna, hubble"
  say "Configura i provider per cui hai una chiave; gli altri puoi saltarli."
  say ""
  local id label agents skipped=""
  for id in $PROVIDERS; do
    label="$(provider_label "$id")"
    agents="$(provider_agents "$id")"
    if is_authenticated "$id"; then
      ok "$label già configurato."
      continue
    fi
    say "  ${BOLD}$label${RESET} non risulta configurato (agenti: $agents)."
    local ans
    while true; do
      read -r -p "  [s] configura ora · [N] salta · [q] esci — scelta: " ans
      case "${ans:-N}" in
        s|S)
          say "  Avvio opencode per $label: inserisci la chiave nella schermata che si apre."
          opencode auth login -p "$id" || true
          if is_authenticated "$id"; then
            ok "$label configurato."
            break
          fi
          say "  ${YELLOW}Non risulti ancora autenticato a $label.${RESET}"
          read -r -p "  [r] ritenta · [q] esci (riprendi dopo) — scelta: " ans
          case "${ans:-r}" in
            q|Q) say "  Installazione interrotta. Riprendi con: ./install.sh"; exit 1 ;;
            *)   continue ;;
          esac
          ;;
        n|N)
          warn "Saltato $label → gli agenti $agents non risponderanno finché non lo configuri."
          skipped="$skipped $id"
          break
          ;;
        q|Q)
          say "  Installazione interrotta. Riprendi con: ./install.sh"
          exit 1
          ;;
        *) say "  Scelta non valida." ;;
      esac
    done
  done
  [ -n "$skipped" ] && warn "Provider saltati:$skipped. Configurali poi con: opencode auth login -p <id>"
}

install_files() {
  step "Installazione file ($MODE)"
  mkdir -p "$CONFIG_DIR/agent" "$CONFIG_DIR/skill" "$CONFIG_DIR/scripts"

  link_one() { # $1 = sorgente  $2 = destinazione (file o dir)
    local src="$1" dst="$2"
    if [ -e "$dst" ] || [ -L "$dst" ]; then
      local a
      read -r -p "  Esiste già $dst. Sovrascrivere? [s/N]: " a
      case "${a:-N}" in s|S) rm -rf "$dst" ;; *) warn "saltato: $dst"; return ;; esac
    fi
    if [ "$MODE" = "copy" ]; then
      cp -R "$src" "$dst" && ok "copiato  $dst"
    else
      ln -s "$src" "$dst" && ok "collegato $dst"
    fi
  }

  local f
  for f in "$SCRIPT_DIR"/agent/*.md; do
    [ -e "$f" ] || continue
    link_one "$f" "$CONFIG_DIR/agent/$(basename "$f")"
  done
  local d name
  for d in "$SCRIPT_DIR"/skill/*/; do
    [ -e "${d}SKILL.md" ] || continue
    name="$(basename "$d")"
    link_one "$d" "$CONFIG_DIR/skill/$name"
  done
  link_one "$SCRIPT_DIR/pricing.md" "$CONFIG_DIR/pricing.md"
  link_one "$SCRIPT_DIR/scripts/telemetry.py" "$CONFIG_DIR/scripts/telemetry.py"
}

config_setup() {
  step "Config (opzionale)"
  local a
  read -r -p "  Impostare commander come modello di default (model + small_model)? [s/N]: " a
  case "${a:-N}" in
    s|S) ;;
    *) say "  Saltato. Commander funziona comunque: i modelli sono nei singoli agenti."; return ;;
  esac
  if [ -e "$CONFIG_DIR/opencode.jsonc" ] || [ -e "$CONFIG_DIR/opencode.json" ]; then
    say "  Trovato un config esistente: non lo tocco. Aggiungi a mano queste righe a ${CONFIG_DIR}/opencode.jsonc:"
    say ""
    say '    "model": "deepseek/deepseek-v4-pro",'
    say '    "small_model": "deepseek/deepseek-flash"'
    say ""
  else
    cp "$SCRIPT_DIR/config/opencode.jsonc.example" "$CONFIG_DIR/opencode.jsonc"
    ok "Creato ${CONFIG_DIR}/opencode.jsonc"
  fi
}

verify() {
  step "Verifica"
  if opencode agent list 2>/dev/null | grep -q '^commander'; then
    ok "Agente 'commander' rilevato."
  else
    warn "'commander' non trovato. Riavvia opencode e riesegui ./install.sh."
  fi
  local id
  for id in $PROVIDERS; do
    is_authenticated "$id" && ok "Provider $id: configurato."
  done
  local missing="" m
  for m in deepseek/deepseek-v4-pro deepseek/deepseek-flash google/gemini-3.8-flash xai/grok-4.7; do
    opencode models 2>/dev/null | grep -qF "$m" || missing="$missing $m"
  done
  if [ -n "$missing" ]; then
    warn "Modelli non trovati nel tuo opencode:$missing (versione diversa?)."
  else
    ok "Modelli del team: tutti disponibili."
  fi
}

main() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --copy) MODE="copy"; shift ;;
      --help|-h) usage; exit 0 ;;
      *) warn "argomento ignoto: $1"; shift ;;
    esac
  done

  say "${BOLD}OpenCode Commander${RESET} — installazione"

  if ! command -v opencode >/dev/null 2>&1; then
    err "opencode non trovato nel PATH."
    say "  Installalo:  curl -fsSL https://opencode.ai/install | bash"
    exit 1
  fi
  ok "opencode trovato ($(opencode --version 2>/dev/null | head -1))."

  provider_setup
  install_files
  config_setup
  verify

  say ""
  say "${BOLD}Fatto.${RESET} Riavvia opencode e lancia:  ${GREEN}opencode --agent commander${RESET}"
}

main "$@"
