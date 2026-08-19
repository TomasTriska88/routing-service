from pathlib import Path
from datetime import datetime
import hashlib,re
root=Path('/config/www')
files=['lina-home-card.js','lina-weather-card.js','lina-security-card.js','lina-climate-safety-card.js','lina-energy-card.js','lina-rainwater-card.js']
needles={
'lina-home-card.js':['.wrap.normal .thought','activity-title'],
'lina-security-card.js':['.normal .hero p','hero p'],
'lina-climate-safety-card.js':['.title small{display:none','title small'],
'lina-energy-card.js':['.loads-head{display:none','loads-head','7.21'],
'lina-rainwater-card.js':['.section-title{display:none','section-title'],
}
for name in files:
    print('===',name,'===')
    paths=[root/name]+sorted(root.glob(name+'.bak*'),key=lambda p:p.stat().st_mtime)
    for p in paths[-35:]:
        b=p.read_bytes(); t=b.decode('utf-8','replace')
        marks=re.findall(r'Markvarec TV[^*\n<]{0,100}',t)
        flags=[]
        for n in needles.get(name,[]):
            if n in t: flags.append('+'+n)
        low=t.lower()
        if 'instrument' in low: flags.append('INSTR')
        if 'tvread' in low: flags.append('TVREAD')
        if 'balanced reset' in low: flags.append('BAL')
        ts=datetime.fromtimestamp(p.stat().st_mtime).strftime('%m-%d %H:%M:%S')
        print(ts,p.name,len(b),hashlib.sha256(b).hexdigest()[:16],'|',','.join(flags),'|',(marks[-1][:80] if marks else ''))
