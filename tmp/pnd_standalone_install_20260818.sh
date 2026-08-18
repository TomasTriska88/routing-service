#!/bin/sh
set -eu
STAGE_REF=${1:?missing staging commit}
BASE="$HOME/.local/share/markvarec-pnd"
CFGDIR="$HOME/.config/markvarec-pnd"
BINDIR="$HOME/.local/bin"
SYSTEMD="$HOME/.config/systemd/user"
UPSTREAM_COMMIT="4d73ffa0d9dff5a6868af6b07cd69d79a7b57460"
UPSTREAM_BLOB="f44f58fee88820c0e2cc7147d497abe7c9cd9243"
ROOT="https://raw.githubusercontent.com/TomasTriska88/routing-service/$STAGE_REF/tmp"

mkdir -p "$BASE/upstream" "$BASE/vendor" "$BASE/bin" "$BASE/data" \
         "$BASE/shim/appdaemon/plugins/hass" "$CFGDIR" "$BINDIR" "$SYSTEMD"
chmod 700 "$CFGDIR"

fetch_blob() {
    URL=$1
    DEST=$2
    SHA=$3
    curl -fsSL "$URL" -o "$DEST"
    GOT=$(git hash-object "$DEST")
    if [ "$GOT" != "$SHA" ]; then
        echo "blob mismatch for $DEST: $GOT" >&2
        exit 70
    fi
}

fetch_blob "$ROOT/pnd_standalone_hassapi_20260818.py" "$BASE/shim/appdaemon/plugins/hass/hassapi.py" "31311ed3ae0136fe86755c2c9958586acbb737e0"
fetch_blob "$ROOT/pnd_standalone_runner_20260818.py" "$BASE/run_standalone.py" "a22be43933670dcfe796bb37cda6fb9807b989b8"
fetch_blob "$ROOT/pnd_standalone_setup_20260818.sh" "$BINDIR/markvarec-pnd-setup" "97e6230c59c630d03e07bab2d2c55af085889946"
fetch_blob "$ROOT/pnd_standalone_run_20260818.sh" "$BINDIR/markvarec-pnd-run" "26db69348c6b3429744b69ab08936e14d866a9af"
chmod 700 "$BINDIR/markvarec-pnd-setup" "$BINDIR/markvarec-pnd-run" "$BASE/run_standalone.py"

for p in "$BASE/shim/appdaemon/__init__.py" "$BASE/shim/appdaemon/plugins/__init__.py" "$BASE/shim/appdaemon/plugins/hass/__init__.py"; do
    : > "$p"
done

UPSTREAM="$BASE/upstream/pnd.py"
curl -fsSL "https://raw.githubusercontent.com/ondrejvysek/HomeAssistant-CEZDistribuce-PND/$UPSTREAM_COMMIT/apps/pnd/pnd.py" -o "$UPSTREAM"
test "$(git hash-object "$UPSTREAM")" = "$UPSTREAM_BLOB"

python3 - "$UPSTREAM" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

def once(old, new, label):
    global s
    if s.count(old) != 1:
        raise SystemExit(f"patch anchor {label} count={s.count(old)}")
    s = s.replace(old, new, 1)

once("import math\n", "import math\nimport re\n", "import-re")
once(
    "firefox_service = FirefoxService('/usr/bin/geckodriver')",
    "firefox_service = FirefoxService(os.environ.get('MARKVAREC_GECKODRIVER', '/usr/bin/geckodriver'))",
    "geckodriver",
)
anchor = """    elm_values_string = ", ".join(elm_values)\n    print(dt.now().strftime("%Y-%m-%d %H:%M:%S") + f": Valid ELM numbers '{elm_values_string}'")\n"""
insert = anchor + """    unique_elm_values = []\n    for elm_label in elm_values:\n        match = re.search(r"ELM\\s*(\\d+)", elm_label)\n        if match and match.group(1) not in unique_elm_values:\n            unique_elm_values.append(match.group(1))\n    if not str(self.ELM).strip():\n        if len(unique_elm_values) == 1:\n            self.ELM = unique_elm_values[0]\n            print(dt.now().strftime("%Y-%m-%d %H:%M:%S") + f": Auto-selected sole ELM '{self.ELM}'")\n        else:\n            raise Exception("ELM_SELECTION_REQUIRED:" + ",".join(unique_elm_values))\n"""
once(anchor, insert, "elm-autodetect")
debug = """    zip_folder(f"/homeassistant/appdaemon/apps/pnd{self.suffix}", f"/homeassistant/appdaemon/apps/debug{self.suffix}.zip")\n    shutil.move(f"/homeassistant/appdaemon/apps/debug{self.suffix}.zip", self.download_folder+"/debug.zip")\n    print(dt.now().strftime("%Y-%m-%d %H:%M:%S") + ": " + "Debug Files Zipped")\n"""
once(debug, "    print(dt.now().strftime(\"%Y-%m-%d %H:%M:%S\") + \": Standalone mode - AppDaemon debug archive skipped\")\n", "debug-archive")
p.write_text(s, encoding="utf-8")
PY

BOOT="$BASE/pip-bootstrap"
if [ ! -f "$BOOT/pip/__init__.py" ]; then
    echo "local pip bootstrap missing" >&2
    exit 71
fi
PYTHONPATH="$BOOT" python3 -m pip install --disable-pip-version-check --quiet --upgrade --target "$BASE/vendor" --break-system-packages selenium pandas numpy beautifulsoup4

cat > "$BASE/bin/pip" <<'SH'
#!/bin/sh
BASE="$HOME/.local/share/markvarec-pnd"
PYTHONPATH="$BASE/pip-bootstrap" exec python3 -m pip "$@"
SH
chmod 700 "$BASE/bin/pip"

GECKO=$(find "$HOME/.cache/selenium" -type f -name geckodriver -perm -u+x 2>/dev/null | sort | tail -n 1)
[ -n "$GECKO" ] || { echo "geckodriver cache missing" >&2; exit 72; }
ln -sf "$GECKO" "$BASE/bin/geckodriver"

PYTHONPATH="$BASE/shim:$BASE/vendor:$BASE/upstream" python3 -m py_compile \
    "$BASE/upstream/pnd.py" "$BASE/run_standalone.py" "$BASE/shim/appdaemon/plugins/hass/hassapi.py"
PATH="$BASE/bin:$PATH" PYTHONPATH="$BASE/shim:$BASE/vendor:$BASE/upstream" \
    MARKVAREC_GECKODRIVER="$BASE/bin/geckodriver" \
    python3 -c 'import pnd; print("PND_UPSTREAM_IMPORT_OK", pnd.ver)'

cat > "$SYSTEMD/markvarec-pnd.service" <<'UNIT'
[Unit]
Description=Markvarec - ČEZ measured data collector
After=network-online.target docker.service

[Service]
Type=oneshot
ExecStart=/home/lina/.local/bin/markvarec-pnd-run
UNIT

cat > "$SYSTEMD/markvarec-pnd.timer" <<'UNIT'
[Unit]
Description=Daily ČEZ measured data refresh

[Timer]
OnCalendar=*-*-* 01:15:00
RandomizedDelaySec=600
Persistent=true
Unit=markvarec-pnd.service

[Install]
WantedBy=timers.target
UNIT

systemctl --user daemon-reload
systemctl --user enable --now markvarec-pnd.timer >/dev/null

DESKTOP=$(xdg-user-dir DESKTOP 2>/dev/null || printf '%s/Desktop' "$HOME")
mkdir -p "$DESKTOP"
LAUNCHER="$DESKTOP/CEZ-namerena-data.desktop"
cat > "$LAUNCHER" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=ČEZ – nastavit naměřená data
Comment=Bezpečně uloží přihlášení pouze na Prckovi a spustí načtení spotřeby
Exec=/home/lina/.local/bin/markvarec-pnd-setup
Icon=utilities-system-monitor
Terminal=false
Categories=Utility;
DESKTOP
chmod 700 "$LAUNCHER"
gio set "$LAUNCHER" metadata::trusted true >/dev/null 2>&1 || true

"$BINDIR/markvarec-pnd-run" || true

echo "PND_STANDALONE_INSTALL_OK"
echo "PND_UPSTREAM_COMMIT=$UPSTREAM_COMMIT"
echo "PND_UPSTREAM_PATCHED_SHA256=$(sha256sum "$UPSTREAM" | awk '{print $1}')"
echo "PND_TIMER=$(systemctl --user is-enabled markvarec-pnd.timer 2>/dev/null || true)"
echo "PND_STATE=$(python3 -c 'import json; print(json.load(open("/home/lina/.local/share/markvarec-pnd/state.json"))["status"])')"
echo "PND_LAUNCHER=$LAUNCHER"
