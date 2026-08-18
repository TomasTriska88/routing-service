#!/bin/sh
set -eu

W=/home/lina/.local/bin/ha-kiosk-watchdog.sh
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="${W}.bak-pid-race-${STAMP}"
cp "$W" "$BACKUP"

python3 - "$W" <<'PY'
from pathlib import Path
import os, sys
p = Path(sys.argv[1])
text = p.read_text(encoding="utf-8")
old = '''focus_guard_pid=""
cleanup() {
  rm -f "$PIDFILE"
  if [ -n "${focus_guard_pid:-}" ]; then
    kill "$focus_guard_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
trap 'cleanup; exit 0' INT TERM
'''
new = '''focus_guard_pid=""
cleanup() {
  current_pid="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ "$current_pid" = "$$" ]; then
    rm -f "$PIDFILE"
  fi
  if [ -n "${focus_guard_pid:-}" ]; then
    kill "$focus_guard_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
trap 'exit 0' INT TERM
'''
if text.count(old) != 1:
    raise SystemExit("expected cleanup block not found exactly once")
tmp = p.with_suffix(p.suffix + ".new-pid-race")
tmp.write_text(text.replace(old, new), encoding="utf-8")
os.replace(tmp, p)
PY

chmod 0755 "$W"
bash -n "$W"
grep -Fq 'current_pid="$(cat "$PIDFILE" 2>/dev/null || true)"' "$W"
grep -Fq "trap 'exit 0' INT TERM" "$W"

kill_tree() {
  p="$1"
  for c in $(pgrep -P "$p" 2>/dev/null || true); do
    kill_tree "$c"
  done
  kill "$p" 2>/dev/null || true
}

PARENTS="$(ps -eo pid=,ppid=,args= | awk '$2==1 && $0 ~ /\/bin\/bash \/home\/lina\/\.local\/bin\/ha-kiosk-watchdog\.sh$/ {print $1}')"
for p in $PARENTS; do
  kill_tree "$p"
done

i=0
while ps -eo ppid=,args= | awk '$1==1 && $0 ~ /\/bin\/bash \/home\/lina\/\.local\/bin\/ha-kiosk-watchdog\.sh$/ {found=1} END{exit found?0:1}'; do
  i=$((i+1))
  [ "$i" -lt 25 ] || { echo "old watchdog still alive" >&2; exit 70; }
  sleep 0.2
done

ORPHANS="$(ps -eo pid=,ppid=,args= | awk '$2==1 && $0 ~ /xprop -spy -root _NET_ACTIVE_WINDOW$/ {print $1}')"
if [ -n "$ORPHANS" ]; then
  kill $ORPHANS 2>/dev/null || true
fi

rm -f /tmp/ha-kiosk-watchdog.pid
nohup "$W" >/tmp/ha-kiosk-watchdog-start.log 2>&1 &
sleep 2

PID="$(cat /tmp/ha-kiosk-watchdog.pid 2>/dev/null || true)"
[ -n "$PID" ]
kill -0 "$PID"
TOP="$(ps -eo pid=,ppid=,args= | awk '$2==1 && $0 ~ /\/bin\/bash \/home\/lina\/\.local\/bin\/ha-kiosk-watchdog\.sh$/ {print $1}')"
[ "$(printf '%s\n' "$TOP" | awk 'NF{n++} END{print n+0}')" -eq 1 ]
[ "$TOP" = "$PID" ]

echo "KIOSK_PID_RACE_FIXED"
echo "BACKUP=$BACKUP"
echo "WATCHDOG_PID=$PID"
sha256sum "$W" /home/lina/.local/share/ha-kiosk/offline.html
