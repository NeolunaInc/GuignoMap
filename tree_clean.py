from __future__ import annotations
from pathlib import Path
from datetime import datetime
from fnmatch import fnmatch

# Dossiers exclus partout (tu peux enlever 'backups'/'exports' si tu veux les voir)
EXCLUDE_DIRS = {
    "__pycache__", ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".idea",
    "node_modules", "backups", "exports"
}

# Fichiers exclus
EXCLUDE_FILE_PATTERNS = {"*.pyc", "*.pyo", "*.pyd", "*.log", "*.tmp", "*.temp", ".DS_Store", "Thumbs.db"}

def list_entries(path: Path, is_root: bool):
    # Trie: dossiers d’abord, puis fichiers (ordre alpha insensible)
    raw = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    entries = []
    for child in raw:
        # Cas spécial: .venv à la racine -> on le montre mais on ne descend pas
        if is_root and child.name == ".venv" and child.is_dir():
            entries.append((".venv/", "STUB"))  # marqueur « stub »
            continue
        if child.is_dir():
            if child.name in EXCLUDE_DIRS:
                continue
            entries.append(child)
        elif child.is_file():
            if any(fnmatch(child.name, pat) for pat in EXCLUDE_FILE_PATTERNS):
                continue
            entries.append(child)
    return entries

def build_tree_lines(root: Path):
    lines = []
    stats = {"files": 0, "dirs": 0}

    def rec(path: Path, prefix: str = "", is_root: bool = False):
        entries = list_entries(path, is_root)
        for i, entry in enumerate(entries):
            last = (i == len(entries) - 1)
            branch = "└── " if last else "├── "
            cont   = "    " if last else "│   "

            if isinstance(entry, tuple) and entry[1] == "STUB":
                # .venv (stub)
                lines.append(f"{prefix}{branch}.venv/  (contents skipped)")
                stats["dirs"] += 1
                continue

            p = entry
            if p.is_dir():
                lines.append(f"{prefix}{branch}{p.name}/")
                stats["dirs"] += 1
                rec(p, prefix + cont, False)
            else:
                lines.append(f"{prefix}{branch}{p.name}")
                stats["files"] += 1

    # En-tête
    lines.append("# ===================== TREE (clean) =====================")
    lines.append(f"# Racine : {root}")
    lines.append(f"# Généré : {datetime.now().isoformat(timespec='seconds')}")
    lines.append("# Règles : .venv (racine) affiché sans contenu; caches & *.pyc exclus")
    lines.append("# ========================================================")
    lines.append(f"{root.name}/")

    rec(root, "", True)

    lines.append("")
    lines.append(f"# Dossiers: {stats['dirs']} | Fichiers: {stats['files']}")
    return lines

def main():
    root = Path(__file__).resolve().parent
    out_dir = root / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"tree_clean_{stamp}.txt"

    lines = build_tree_lines(root)
    text = "\n".join(lines)

    print(text)
    out_file.write_text(text, encoding="utf-8")
    print(f"\nOK -> {out_file}")

if __name__ == "__main__":
    main()
