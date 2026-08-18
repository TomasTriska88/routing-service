from pathlib import Path
import py_compile

path = Path('/home/lina/.local/bin/markvarec-pnd-setup')
text = path.read_text(encoding='utf-8')
marker = 'WATCHDOG_PID_FILE=/tmp/ha-kiosk-watchdog.pid'
if marker in text:
    print('PND_SETUP_FOCUS_GUARD_ALREADY_PATCHED')
    raise SystemExit(0)

old = '''mkdir -p "$BASE" "$CFGDIR"\n\nEMAIL=$(zenity --entry --title="ČEZ – naměřená data"'''
new = '''mkdir -p "$BASE" "$CFGDIR"\n\n# The Prcek kiosk watchdog normally pulls focus back to Firefox. Pause only the\n# already-running watchdog process while credentials are entered, and always\n# resume it on exit/cancel/error. Firefox itself remains running.\nWATCHDOG_PID_FILE=/tmp/ha-kiosk-watchdog.pid\nWATCHDOG_PID=""\nWATCHDOG_PAUSED=0\nif [ -r "$WATCHDOG_PID_FILE" ]; then\n  WATCHDOG_PID=$(cat "$WATCHDOG_PID_FILE" 2>/dev/null || true)\n  case "$WATCHDOG_PID" in\n    ''|*[!0-9]*) WATCHDOG_PID="" ;;&\n  esac\n  if [ -n "$WATCHDOG_PID" ] && kill -0 "$WATCHDOG_PID" 2>/dev/null; then\n    if kill -STOP "$WATCHDOG_PID" 2>/dev/null; then\n      WATCHDOG_PAUSED=1\n    fi\n  fi\nfi\nresume_watchdog() {\n  if [ "$WATCHDOG_PAUSED" -eq 1 ] && [ -n "$WATCHDOG_PID" ]; then\n    kill -CONT "$WATCHDOG_PID" 2>/dev/null || true\n    WATCHDOG_PAUSED=0\n  fi\n}\ntrap resume_watchdog EXIT INT TERM\n\nEMAIL=$(zenity --entry --title="ČEZ – naměřená data"'''
if text.count(old) != 1:
    raise SystemExit(f'focus patch anchor count={text.count(old)}')
text = text.replace(old, new, 1)

old_end = '''zenity --info --title="ČEZ – naměřená data" --text="Údaje jsou uložené pouze na Prckovi. Spustila jsem první načtení dat z ČEZ; po jeho dokončení se stav objeví v Home Assistantu." 2>/dev/null || true\n'''
new_end = old_end + '''resume_watchdog\ntrap - EXIT INT TERM\n'''
if text.count(old_end) != 1:
    raise SystemExit(f'end patch anchor count={text.count(old_end)}')
text = text.replace(old_end, new_end, 1)

# POSIX /bin/sh does not support Bash's ;;&. Fix the generated case arm to a plain ;;.
text = text.replace('WATCHDOG_PID="" ;;&', 'WATCHDOG_PID="" ;;')
path.write_text(text, encoding='utf-8')
path.chmod(0o700)

# Static shell syntax check.
import subprocess
proc = subprocess.run(['/bin/sh', '-n', str(path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print(proc.stdout)
if proc.returncode != 0:
    raise SystemExit('shell syntax validation failed')
print('PND_SETUP_FOCUS_GUARD_PATCH_OK')
