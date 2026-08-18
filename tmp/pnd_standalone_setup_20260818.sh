#!/bin/sh
set -eu
BASE="$HOME/.local/share/markvarec-pnd"
CFGDIR="$HOME/.config/markvarec-pnd"
CRED="$CFGDIR/credentials.json"
CFG="$CFGDIR/config.json"
mkdir -p "$BASE" "$CFGDIR"

EMAIL=$(zenity --entry --title="ČEZ – naměřená data" --text="Zadej e-mail, kterým se přihlašuješ do portálu ČEZ Distribuce:" 2>/dev/null) || exit 0
[ -n "$EMAIL" ] || { zenity --error --text="E-mail nesmí být prázdný." 2>/dev/null || true; exit 1; }
PASSWORD=$(zenity --password --title="ČEZ – naměřená data" --text="Zadej heslo k portálu ČEZ Distribuce. Heslo zůstane pouze na Prckovi:" 2>/dev/null) || exit 0
[ -n "$PASSWORD" ] || { zenity --error --text="Heslo nesmí být prázdné." 2>/dev/null || true; exit 1; }
ELM=$(zenity --entry --title="ČEZ – elektroměr" --text="Číslo elektroměru můžeš nechat prázdné. Pokud má účet právě jeden elektroměr, zkusím ho určit automaticky. Máš-li číslo ELM, zadej jen číslice:" 2>/dev/null) || ELM=""

CTMP=$(mktemp "$CFGDIR/.credentials.XXXXXX")
FTMP=$(mktemp "$CFGDIR/.config.XXXXXX")
cleanup() { rm -f "$CTMP" "$FTMP"; }
trap cleanup EXIT INT TERM
printf '%s\0%s\0%s\0' "$EMAIL" "$PASSWORD" "$ELM" | python3 -c '
import json, pathlib, sys
parts = sys.stdin.buffer.read().split(b"\0")
email = parts[0].decode("utf-8")
password = parts[1].decode("utf-8")
elm = parts[2].decode("utf-8").strip()
pathlib.Path(sys.argv[1]).write_text(json.dumps({"username": email, "password": password}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
pathlib.Path(sys.argv[2]).write_text(json.dumps({"elm": elm}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
' "$CTMP" "$FTMP"
chmod 600 "$CTMP" "$FTMP"
mv "$CTMP" "$CRED"
mv "$FTMP" "$CFG"
trap - EXIT INT TERM
unset EMAIL PASSWORD ELM

nohup "$HOME/.local/bin/markvarec-pnd-run" >"$BASE/pnd.log" 2>&1 &
zenity --info --title="ČEZ – naměřená data" --text="Údaje jsou uložené pouze na Prckovi. Spustila jsem první načtení dat z ČEZ; po jeho dokončení se stav objeví v Home Assistantu." 2>/dev/null || true
