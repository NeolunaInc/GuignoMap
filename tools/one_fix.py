import sys, shutil, time
from pathlib import Path

# Common mojibake replacements (minimal safe set)
REPL = {
    "Ã©": "é", "Ã¨": "è", "Ã ": "à", "Ã¢": "â", "Ã§": "ç", "Ã´": "ô",
    "Ã€": "À", "Ã‰": "É", "Ãˆ": "È", "Ã‡": "Ç",
}

def fix_text(s: str) -> str:
    try:
        s = s.encode("latin-1", "ignore").decode("utf-8", "ignore")
    except Exception:
        pass
    for k, v in REPL.items():
        s = s.replace(k, v)
    return s.replace("\r\n", "\n").replace("\r", "\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python one_fix.py <filepath>")
        sys.exit(1)

    p = Path(sys.argv[1])
    if not p.exists():
        print(f"File not found: {p}")
        sys.exit(1)

    raw = p.read_text(encoding="utf-8", errors="ignore")
    fixed = fix_text(raw)

    # backup + write
    ts = time.strftime("%Y%m%d_%H%M%S")
    bdir = Path("backups") / f"one_fix_{ts}"
    bdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, bdir / p.name)
    p.write_text(fixed, encoding="utf-8", newline="\n")
    print("✓ fixed:", p)