#!/bin/sh
set -eu

WATCHDOG=/home/lina/.local/bin/ha-kiosk-watchdog.sh
OFFLINE_DIR=/home/lina/.local/share/ha-kiosk
OFFLINE_PAGE=$OFFLINE_DIR/offline.html
STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="${WATCHDOG}.bak-offline-guard-${STAMP}"

mkdir -p "$OFFLINE_DIR"
cp "$WATCHDOG" "$BACKUP"

cat > "$OFFLINE_PAGE" <<'HTML'
<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Home Assistant – restart</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  html,body { width:100%; height:100%; margin:0; }
  body {
    display:grid;
    place-items:center;
    overflow:hidden;
    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color:#f7f9ff;
    background:
      radial-gradient(circle at 18% 14%, rgba(79,140,255,.18), transparent 34%),
      radial-gradient(circle at 82% 82%, rgba(158,94,255,.12), transparent 32%),
      linear-gradient(145deg,#090d17 0%,#101725 48%,#070a11 100%);
  }
  .card {
    width:min(920px,84vw);
    padding:52px 58px;
    border:1px solid rgba(255,255,255,.10);
    border-radius:30px;
    background:rgba(18,25,40,.72);
    box-shadow:0 28px 90px rgba(0,0,0,.38);
    backdrop-filter:blur(14px);
  }
  .eyebrow {
    display:flex; align-items:center; gap:13px;
    font-size:18px; font-weight:720; letter-spacing:.10em; text-transform:uppercase;
    color:#a9b8d8;
  }
  .pulse {
    width:15px; height:15px; border-radius:50%; background:#ffb24a;
    box-shadow:0 0 0 0 rgba(255,178,74,.48);
    animation:pulse 1.6s infinite;
  }
  h1 { margin:20px 0 16px; font-size:58px; line-height:1.03; letter-spacing:-.035em; }
  .lead { margin:0; max-width:760px; font-size:28px; line-height:1.35; color:#d9e1f2; }
  .warning {
    margin-top:30px; padding:18px 22px; border-radius:18px;
    font-size:22px; line-height:1.35; font-weight:700;
    color:#ffe4bd; background:rgba(255,166,45,.10); border:1px solid rgba(255,178,74,.24);
  }
  .foot { margin-top:24px; font-size:18px; color:#8f9bb2; }
  @keyframes pulse {
    0% { box-shadow:0 0 0 0 rgba(255,178,74,.48); }
    70% { box-shadow:0 0 0 18px rgba(255,178,74,0); }
    100% { box-shadow:0 0 0 0 rgba(255,178,74,0); }
  }
</style>
</head>
<body>
  <main class="card">
    <div class="eyebrow"><span class="pulse"></span> Home Assistant není připravený</div>
    <h1>HA se restartuje nebo nabíhá</h1>
    <p class="lead">Hnízdo je dočasně odpojené od živých dat. Až bude Home Assistant znovu stabilní, přehled se vrátí automaticky.</p>
    <div class="warning">⚠️ Zobrazeným hodnotám z předchozího Hnízda teď nevěř — nemusí být aktuální.</div>
    <div class="foot">Lina hlídá návrat systému · Markvarec</div>
  </main>
</body>
</html>
HTML

cat > "$WATCHDOG" <<'SH'
#!/bin/bash
set -u

URL="http://localhost:8123/linino-hnizdo/0?kiosk"
BASE="http://localhost:8123/"
OFFLINE_PAGE="/home/lina/.local/share/ha-kiosk/offline.html"
OFFLINE_URL="file://${OFFLINE_PAGE}"
REFRESH_SECONDS=900
CHECK_SECONDS=5
RECOVERY_SUCCESSES=4
LOG="/tmp/ha-kiosk-watchdog.log"
PIDFILE="/tmp/ha-kiosk-watchdog.pid"
LOCKFILE="/tmp/ha-kiosk-watchdog.lock"

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/lina/.Xauthority}"

exec 9>"$LOCKFILE"
if ! flock -n 9; then
  exit 0
fi
printf '%s\n' "$$" > "$PIDFILE"

focus_guard_pid=""
cleanup() {
  rm -f "$PIDFILE"
  if [ -n "${focus_guard_pid:-}" ]; then
    kill "$focus_guard_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT
trap 'cleanup; exit 0' INT TERM

log() {
  printf '%s %s\n' "$(date -Is)" "$*" >> "$LOG"
}

find_firefox_window() {
  wmctrl -lx 2>/dev/null | awk '$3=="Navigator.firefox" {print $1; exit}'
}

navigate() {
  local target="$1"
  local wid
  wid="$(find_firefox_window || true)"
  if [ -z "$wid" ]; then
    nohup firefox --kiosk "$target" >/tmp/firefox-kiosk.log 2>&1 &
    log "started firefox target=$target"
    return 0
  fi
  xdotool windowactivate --sync "$wid" >/dev/null 2>&1 || true
  xdotool key --window "$wid" ctrl+l >/dev/null 2>&1 || true
  sleep 0.15
  xdotool type --window "$wid" --clearmodifiers --delay 1 "$target" >/dev/null 2>&1 || true
  xdotool key --window "$wid" Return >/dev/null 2>&1 || true
}

focus_guard() {
  xprop -spy -root _NET_ACTIVE_WINDOW 2>/dev/null | while IFS= read -r _line; do
    wid="$(find_firefox_window || true)"
    if [ -n "$wid" ]; then
      wmctrl -ia "$wid" >/dev/null 2>&1 || true
    fi
  done
}

focus_guard &
focus_guard_pid=$!

state="starting"
up_streak=0
last_refresh=0
navigate "$OFFLINE_URL"
log "watchdog started; dashboard withheld until HA is stable"

while true; do
  now=$(date +%s)
  if curl -fsS --max-time 2 "$BASE" >/dev/null 2>&1; then
    up_streak=$((up_streak + 1))
    if [ "$state" != "online" ]; then
      if [ "$up_streak" -ge "$RECOVERY_SUCCESSES" ]; then
        navigate "$URL"
        state="online"
        last_refresh="$now"
        log "HA stable after $up_streak successful probes; dashboard restored"
      elif [ "$state" != "recovering" ]; then
        navigate "$OFFLINE_URL"
        state="recovering"
        log "HA responds; waiting for stable recovery ($RECOVERY_SUCCESSES probes)"
      fi
    fi
  else
    up_streak=0
    if [ "$state" != "offline" ]; then
      navigate "$OFFLINE_URL"
      state="offline"
      log "HA unavailable; stale dashboard hidden"
    fi
  fi

  wid="$(find_firefox_window || true)"
  if [ -n "$wid" ]; then
    wmctrl -ir "$wid" -b add,fullscreen,above,sticky >/dev/null 2>&1 || true
    wmctrl -ia "$wid" >/dev/null 2>&1 || true
    if [ "$state" = "online" ] && [ $((now - last_refresh)) -ge "$REFRESH_SECONDS" ]; then
      xdotool windowactivate --sync "$wid" >/dev/null 2>&1 || true
      xdotool key --window "$wid" ctrl+r >/dev/null 2>&1 || true
      last_refresh="$now"
      log "refreshed dashboard"
    fi
  fi

  sleep "$CHECK_SECONDS"
done
SH

chmod 0755 "$WATCHDOG"
command -v flock >/dev/null
bash -n "$WATCHDOG"
test -s "$OFFLINE_PAGE"

PIDS="$(pgrep -f '^/bin/bash /home/lina/.local/bin/ha-kiosk-watchdog.sh$' || true)"
if [ -n "$PIDS" ]; then
  kill $PIDS 2>/dev/null || true
  sleep 1
fi
rm -f /tmp/ha-kiosk-watchdog.pid
nohup "$WATCHDOG" >/tmp/ha-kiosk-watchdog-start.log 2>&1 &
sleep 2

NEWPID="$(cat /tmp/ha-kiosk-watchdog.pid 2>/dev/null || true)"
[ -n "$NEWPID" ]
kill -0 "$NEWPID"
echo "KIOSK_OFFLINE_GUARD_INSTALLED"
echo "BACKUP=$BACKUP"
echo "WATCHDOG_PID=$NEWPID"
sha256sum "$WATCHDOG" "$OFFLINE_PAGE"
