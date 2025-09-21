import argparse, re, sys, shutil, time
from pathlib import Path

REPL = {
    "Ã©":"é","Ã¨":"è","Ã ":"à","Ãª":"ê","Ã«":"ë","Ã¢":"â","Ã¹":"ù","Ã¼":"ü","Ã§":"ç","Ã®":"î","Ã¯":"ï","Ã´":"ô","Ã¶":"ö",
    "Ã€":"À","Ã‰":"É","Ãˆ":"È","Ã‡":"Ç","Ã‚":"Â","ÃŠ":"Ê","ÃŽ":"Î","Ã™":"Ù","Ãœ":"Ü","Å¸":"Ÿ",
    "â€™":"’","â€˜":"‘","â€œ":"“","â€":"”","â€“":"–","â€”":"—","â€¢":"•","â€¦":"…",
    "Â©":"©","Â®":"®","â„¢":"™","Â°":"°","Â±":"±","Ã—":"×","Ã·":"÷","â‰ ":"≠","â‰¤":"≤","â‰¥":"≥","âˆž":"∞",
}

def fix_mojibake(s: str) -> str:
    # tentative round-trip latin1->utf8 si on voit du mojibake
    if any(x in s for x in ("Ã","â","Â","Å")):
        try:
            s = s.encode("latin-1","ignore").decode("utf-8","ignore")
        except Exception:
            pass
    for k,v in REPL.items():
        s = s.replace(k,v)
    return s.replace("\r\n","\n").replace("\r","\n")

def wrap_header_in_docstring(text: str) -> str:
    # conserve shebang/encoding au tout début
    lines = text.split("\n")
    i = 0
    while i < len(lines) and (lines[i].startswith("#!") or re.match(r"#.*coding[:=]", lines[i])):
        i += 1
    # déjà une docstring ?
    if i < len(lines) and re.match(r'\s*("""|\'\'\')', lines[i]):
        return text
    # trouver le début du code (import/def/class/from) ou fin
    j = i
    pat = re.compile(r'^\s*(import|from|def|class)\b')
    while j < len(lines) and not pat.search(lines[j]):
        j += 1
    header = "\n".join(lines[i:j]).strip("\n")
    rest   = "\n".join(lines[j:])
    doc = '"""GuignoMap — fichier réparé (UTF-8).\nCe bloc contenait du texte libre/©/accents, il est désormais dans une docstring.\n"""\n'
    new = "\n".join(lines[:i]) + (("\n" if i>0 else "") + doc) + (rest if rest.startswith("\n") else ("\n"+rest))
    return new

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    args = ap.parse_args()
    p = Path(args.file)
    raw = p.read_text(encoding="utf-8", errors="ignore")
    fixed = fix_mojibake(raw)
    fixed = wrap_header_in_docstring(fixed)
    # backup
    ts = time.strftime("%Y%m%d_%H%M%S")
    bdir = Path("backups")/f"app_fix_{ts}"; bdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, bdir/p.name)
    p.write_text(fixed, encoding="utf-8", newline="\n")
    print("✓ app.py réparé:", p)
if __name__ == "__main__":
    main()