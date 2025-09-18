from pathlib import Path
import sys
import io
from typing import Iterable
try:
    # installé via reportlab -> charset-normalizer
    from charset_normalizer import from_path as cn_from_path
except Exception:
    cn_from_path = None

TARGET_NEWLINE = "\n"

DEFAULT_FILES = [
    r"check_admin.py",
    r"README.md",
    r"README_VENV.md",
    r"RESUME_ARBRES_EXPORTS.md",
    r"docs\PHASE1_AUDIT_DATAFRAME.md",
    r"docs\PROBLEME_IPV6_SUPABASE.md",
    r"guignomap\app.py",
    r"guignomap\backup.py",
    r"guignomap\db_v5.py",
    r"guignomap\osm.py",
    r"scripts\find_mojibake.py",
    r"scripts\fix_mojibake_db.py",
    r"scripts\fix_mojibake_files.py",
    r"scripts\generate_audit_optimise.py",
    r"scripts\generate_tree_clean.py",
    r"scripts\migrate_password_hashes.py",
    r"scripts\migrate_sqlite_to_postgres.py",
    r"scripts\run_all_tests.py",
    r"scripts\show_hash_stats.py",
    r"scripts\validate_structure.py",
    r"src\database\operations.py",
    r"src\storage\__init__.py",
    r"src\utils\adapters.py",
    r"tests\auth\test_passwords_smoke.py",
    r"tools\quick_sanity.py",
]

def detect_encoding(path: Path) -> str:
    # 1) essayer utf-8 / utf-8-sig en lecture stricte
    for enc in ("utf-8", "utf-8-sig"):
        try:
            path.read_text(encoding=enc)
            return enc
        except Exception:
            pass
    # 2) charset-normalizer si dispo
    if cn_from_path:
        res = cn_from_path(path)
        if res:
            best = res.best()
            if best:
                return best.encoding or "utf-8"
    # 3) fallback latin-1 (ne lève jamais)
    return "latin-1"

def convert_file(path: Path) -> bool:
    enc = detect_encoding(path)
    try:
        raw = path.read_text(encoding=enc, errors="replace")
    except Exception as e:
        print(f"!! Read failed {path}: {e}")
        return False
    # normaliser fins de ligne
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    # écrire en utf-8 sans BOM
    try:
        path.write_text(normalized, encoding="utf-8", newline="\n")
        print(f"✓ Converted to UTF-8 no BOM (from {enc}): {path}")
        return True
    except Exception as e:
        print(f"!! Write failed {path}: {e}")
        return False

def main(files: Iterable[str]):
    root = Path(".").resolve()
    ok = True
    for f in files:
        p = (root / f).resolve()
        if p.exists() and p.is_file():
            ok &= convert_file(p)
        else:
            print(f"-- skip (not found): {p}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    # si aucun argument: utiliser DEFAULT_FILES
    args = sys.argv[1:]
    files = args if args else DEFAULT_FILES
    main(files)