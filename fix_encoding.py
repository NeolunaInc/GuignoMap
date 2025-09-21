#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
REPL = {
 '':'é','¨':'è',' ':'à','§':'ç','´':'ô','»':'û','¢':'','ª':'ê','':'î','¯':'ï',
 '':'ù','¼':'ü','±':'ñ','¶':'ö','¤':'ä','':'ÿ','€':'À','':'É','':'È','':'Ç',
 '"':'Ô','':'Û','':'','Š':'Ê','Ž':'Î','':'Ù','œ':'Ü',"'":"'",''œ':'"',''\x9d':'"',
 ''"':'',''"':'',''¢':'',''¦':'...','':'','':'','':'','°':'°','±':'±',
 '':'','':'','':'','':'','':'','ž':''
}
def fix_file(p):
    try:
        t = p.read_text(encoding="utf-8", errors="replace")
        for k,v in REPL.items(): t = t.replace(k,v)
        p.write_text(t, encoding="utf-8", newline="\n"); print("", p)
    except Exception as e: print("", p, e)
for pat in ("*.py","*.toml","*.md","*.txt","*.css"):
    for f in Path(".").rglob(pat):
        s=str(f)
        if any(x in s for x in ("/.venv/","\\.venv\\","__pycache__","/backup_","\\backup_")): continue
        fix_file(f)
