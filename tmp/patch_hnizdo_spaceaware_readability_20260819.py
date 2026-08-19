#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, re, shutil, sys

ROOT = Path('/config/www')
RES = Path('/config/.storage/lovelace_resources')
TAG_OLD = '20260819-tvbaseline-r1'
TAG_NEW = '20260819-spaceaware-r1'
MARKER = 'Markvarec TV space-aware readability: 20260819-spaceaware-r1'
BACKUP_SUFFIX = '.bak-20260819-1454-spaceaware-r1'
EXPECTED = {'lina-home-card.js': '3e3766e4bea4cc380731aa640bafdf4ff685ae1b1f86816b7c3cca0a89f3659d', 'lina-weather-card.js': 'c67f5f5c63b1fd66228c5c95fb3065664f4012848a100e97a5682bebe1dc7265', 'lina-security-card.js': 'cd5cd0c4d10456bd6c0147bd80bf282f18793f64f5821880072339d990fd4a19', 'lina-climate-safety-card.js': 'e408c12085ba68800d04e696eb6d9b723233f8c5ac85ccd9a8d800944d304708', 'lina-energy-card.js': 'b63f1d050fcef1ae4af2ecb5990d02dd9360e7f07491f901b1f0e51116ed97bf', 'lina-rainwater-card.js': '6f3b93fc2ca5db8546a0f998fecaa8e4135dc45e024684aa23004114f94d6644'}
OVERRIDES = {'lina-home-card.js': ':host([data-tv-kiosk="1"]) .eyebrow,\n:host([data-tv-kiosk="1"]) .sub { font-size:13px; opacity:.80; }\n:host([data-tv-kiosk="1"]) .thought { font-size:14px; }\n:host([data-tv-kiosk="1"]) .chip small { font-size:11px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .chip strong { font-size:14px; }\n:host([data-tv-kiosk="1"]) .activity-title { font-size:12px; opacity:.80; }\n:host([data-tv-kiosk="1"]) .activity time { font-size:12px; opacity:.80; }\n:host([data-tv-kiosk="1"]) .activity strong { font-size:13px; }', 'lina-weather-card.js': ':host([data-tv-kiosk="1"]) .feels { opacity:.82; }\n:host([data-tv-kiosk="1"]) .condition-text { font-size:15px; }\n:host([data-tv-kiosk="1"]) .temp-trend { font-size:13px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .temp-trend small { font-size:12px; opacity:.80; }\n:host([data-tv-kiosk="1"]) .place { font-size:13px; opacity:.80; }\n:host([data-tv-kiosk="1"]) .rain-next small { font-size:12px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .signal small { font-size:12px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .radar-title { font-size:12px; opacity:.80; }\n:host([data-tv-kiosk="1"]) .radar-point small { font-size:11px; opacity:.78; }\n:host([data-tv-kiosk="1"]) .irrigation small { font-size:12px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .group-title { font-size:12px; opacity:.80; }\n:host([data-tv-kiosk="1"]) .forecast-cell small { font-size:11px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .forecast-cell em { font-size:11px; opacity:.78; }\n:host([data-tv-kiosk="1"]) .loading { font-size:12px; opacity:.80; }\n:host([data-tv-kiosk="1"]) .footer { font-size:11px; opacity:.78; }', 'lina-security-card.js': ':host([data-tv-kiosk="1"]) .eyebrow { font-size:13px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .hero p { font-size:15px; line-height:1.30; opacity:.82; }\n:host([data-tv-kiosk="1"]) .chip small { font-size:14px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .chip strong { font-size:16px; }\n:host([data-tv-kiosk="1"]) .extra { font-size:14px; opacity:.82; }', 'lina-climate-safety-card.js': ':host([data-tv-kiosk="1"]) .title small { font-size:12px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .outside-box small { font-size:11px; opacity:.80; }\n:host([data-tv-kiosk="1"]) .outside-box em { font-size:12px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .zone-head strong { font-size:14px; }\n:host([data-tv-kiosk="1"]) .zone-values .hum { font-size:13px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .heater-main small { font-size:11px; opacity:.80; }\n:host([data-tv-kiosk="1"]) .heater-main button { font-size:15px; }\n:host([data-tv-kiosk="1"]) .pill { font-size:12px; }\n:host([data-tv-kiosk="1"]) .more-issues { font-size:12px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .issue strong { font-size:14px; }\n:host([data-tv-kiosk="1"]) .issue small { font-size:12px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .footer { font-size:11px; opacity:.78; }', 'lina-energy-card.js': ':host([data-tv-kiosk="1"]) .title small { font-size:13px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .reading span { font-size:16px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .rate strong { font-size:17px; }\n:host([data-tv-kiosk="1"]) .rate small { font-size:14px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .meta small { font-size:14px; opacity:.82; letter-spacing:.045em; }\n:host([data-tv-kiosk="1"]) .meta strong { font-size:17px; }\n:host([data-tv-kiosk="1"]) .loads-head strong { font-size:14px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .loads-head span { font-size:13px; opacity:.80; }\n:host([data-tv-kiosk="1"]) .load-copy small { font-size:16px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .load-copy strong { font-size:18px; }\n:host([data-tv-kiosk="1"]) .loads-empty { font-size:13px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .issue strong { font-size:14px; }\n:host([data-tv-kiosk="1"]) .issue small { font-size:13px; opacity:.82; }', 'lina-rainwater-card.js': ':host([data-tv-kiosk="1"]) .hero-copy .label { font-size:14px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .estimate { font-size:14px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .advice .eyebrow { font-size:13px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .advice small { font-size:14px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .section-title { font-size:13px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .stat strong { font-size:15px; }\n:host([data-tv-kiosk="1"]) .stat small { font-size:12px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .rain-box small { font-size:13px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .overflow-note strong { font-size:15px; }\n:host([data-tv-kiosk="1"]) .overflow-note small { font-size:13px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .quality .qcopy small { font-size:12px; opacity:.82; }\n:host([data-tv-kiosk="1"]) .quality .qcopy strong { font-size:15px; }\n:host([data-tv-kiosk="1"]) .quality p { font-size:13px; opacity:.80; }\n:host([data-tv-kiosk="1"]) .footer { font-size:12px; opacity:.78; }'}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def backup_path(p):
    return p.with_name(p.name + BACKUP_SUFFIX)

def restore():
    for name in EXPECTED:
        p = ROOT / name
        b = backup_path(p)
        if b.exists():
            shutil.copy2(b, p)
    rb = RES.with_name(RES.name + BACKUP_SUFFIX)
    if rb.exists():
        shutil.copy2(rb, RES)
    print('HNIZDO_SPACEAWARE_ROLLBACK_OK')

if '--rollback' in sys.argv:
    restore()
    raise SystemExit(0)

for name, exp in EXPECTED.items():
    p = ROOT / name
    got = sha(p)
    if got != exp:
        raise SystemExit(f'LIVE_SHA_MISMATCH {name} {got} != {exp}')

for name in EXPECTED:
    p = ROOT / name
    b = backup_path(p)
    shutil.copy2(p, b)
    s = p.read_text(encoding='utf-8')
    if MARKER in s:
        raise SystemExit(f'MARKER_ALREADY_PRESENT {name}')
    pat = re.compile(r'(setConfig\s*\(\s*config\s*\)\s*\{)')
    s, n = pat.subn(r'\1\n    this.dataset.tvKiosk = new URLSearchParams(window.location.search).has("kiosk") ? "1" : "0";', s, count=1)
    if n != 1:
        raise SystemExit(f'SETCONFIG_ANCHOR {name} {n}')
    block = '\n        /* ' + MARKER + ' */\n' + OVERRIDES[name].strip() + '\n'
    if '</style>' not in s:
        raise SystemExit(f'STYLE_ANCHOR_MISSING {name}')
    s = s.replace('</style>', block + '      </style>', 1)
    p.write_text(s, encoding='utf-8')

rb = RES.with_name(RES.name + BACKUP_SUFFIX)
shutil.copy2(RES, rb)
d = json.loads(RES.read_text(encoding='utf-8'))
items = d['data']['items']
for name in EXPECTED:
    old = f'/local/{name}?v={TAG_OLD}'
    new = f'/local/{name}?v={TAG_NEW}'
    matches = [x for x in items if x.get('url') == old]
    if len(matches) != 1:
        restore()
        raise SystemExit(f'RESOURCE_MATCH {name} {len(matches)}')
    matches[0]['url'] = new
RES.write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

for name in EXPECTED:
    p=ROOT/name
    print(name, len(p.read_bytes()), sha(p))
print('RESOURCES', sha(RES))
print('HNIZDO_SPACEAWARE_PATCHED')
