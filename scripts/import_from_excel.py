#!/usr/bin/env python3
# [GM] BEGIN Wrapper import_from_excel
from pathlib import Path
import sys, subprocess

def main() -> int:
    here = Path(__file__).parent
    script = here / "import_city_excel.py"
    if not script.exists():
        print("scripts/import_city_excel.py introuvable", file=sys.stderr)
        return 2
    cmd = [sys.executable, str(script), *sys.argv[1:]]
    return subprocess.call(cmd)

if __name__ == "__main__":
    raise SystemExit(main())
# [GM] END Wrapper import_from_excel
