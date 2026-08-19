from pathlib import Path
import hashlib,re,difflib
root=Path('/config/www')
files=['lina-home-card.js','lina-weather-card.js','lina-security-card.js','lina-climate-safety-card.js','lina-energy-card.js','lina-rainwater-card.js']

def split_style(text):
    m=re.search(r'<style>(.*?)</style>',text,re.S)
    if not m: return '',text
    style=m.group(1)
    outside=text[:m.start()]+'<style>__STYLE__</style>'+text[m.end():]
    return style,outside
for name in files:
    cur=(root/name).read_text(encoding='utf-8')
    old=(root/(name+'.bak-20260818-2244-instrument-v1')).read_text(encoding='utf-8')
    cs,co=split_style(cur); os,oo=split_style(old)
    print('===',name,'===')
    print('STYLE',hashlib.sha256(os.encode()).hexdigest()[:16],hashlib.sha256(cs.encode()).hexdigest()[:16],'OUTSIDE',hashlib.sha256(oo.encode()).hexdigest()[:16],hashlib.sha256(co.encode()).hexdigest()[:16],'SAME_OUTSIDE',oo==co)
    if oo!=co:
        diff=list(difflib.unified_diff(oo.splitlines(),co.splitlines(),fromfile='preinstrument',tofile='current',n=1))
        for line in diff[:120]: print(line)
