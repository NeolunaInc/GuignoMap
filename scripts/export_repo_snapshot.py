# coding: utf-8
"""
Export complet du code GuignoMap → exports/export_full_YYYYMMDD_HHMMSS.txt
- UTF-8 (sans BOM), normalise les fins de lignes.
- Inclut le contenu des fichiers code/texte utiles.
- Exclut .git, .venv, caches, binaires, gros fichiers.
- Ne lit jamais .streamlit/secrets.toml (sécurité).
"""

from __future__ import annotations
import sys, os, io, time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "exports"
OUTDIR.mkdir(parents=True, exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTFILE = OUTDIR / f"export_full_{ts}.txt"

# Dossiers à exclure
EXCLUDE_DIRS = {
    ".git", ".github", ".venv", ".vscode", "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", "dist", "build", "storage_local", ".idea"
}

# Fichiers à exclure (par nom exact)
EXCLUDE_FILES = {
    "secrets.toml",  # ne jamais exposer des secrets
}

# Extensions à inclure (code/texte)
INCLUDE_EXTS = {
    ".py", ".txt", ".md", ".ps1", ".bat", ".toml", ".ini", ".cfg",
    ".yml", ".yaml", ".json", ".sql"
}

# Extensions à exclure d’office (binaires/pondéreux)
BINARY_EXTS = {
    ".db", ".sqlite", ".sqlite3", ".pkl", ".zip", ".7z", ".rar", ".exe", ".dll",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".parquet"
}

# Taille max (Ko) par fichier pour éviter les énormes blobs
SIZE_LIMIT_KB = 300  # ajuste si besoin

def should_skip(path: Path) -> bool:
    # Exclure par dossier
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
    # Exclure par extension binaire
    if path.suffix.lower() in BINARY_EXTS:
        return True
    # Exclure fichier secrets explicites
    if path.name in EXCLUDE_FILES:
        return True
    # Filtre d’extensions
    if path.suffix and path.suffix.lower() not in INCLUDE_EXTS:
        return True
    # Limite de taille
    try:
        if path.stat().st_size > SIZE_LIMIT_KB * 1024:
            return True
    except Exception:
        return True
    return False

def read_text_safely(path: Path) -> str:
    # Toujours lire en UTF-8 avec remplacement pour éviter les caractères corrompus
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            txt = f.read()
    except Exception as e:
        txt = f"<<ERREUR LECTURE {path}: {e}>>"
    # Normaliser fins de lignes
    return txt.replace("\r\n", "\n").replace("\r", "\n")

def main() -> int:
    files: list[Path] = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if should_skip(p):
            continue
        files.append(p)

    files.sort(key=lambda x: str(x).lower())

    header = f"""# GuignoMap - Export de code COMPLET
# Date : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# Racine : {ROOT}
# Fichiers inclus : {len(files)}
# Encodage : UTF-8 (sans BOM)
# Règles : exclusions .git/.venv/binaires/gros fichiers, NO secrets.toml
"""

    with open(OUTFILE, "w", encoding="utf-8", newline="\n") as out:
        out.write(header + "\n")
        out.write("## INDEX\n")
        for p in files:
            rel = p.relative_to(ROOT)
            out.write(f"- {rel.as_posix()}\n")

        out.write("\n## CONTENU DES FICHIERS\n")
        for p in files:
            rel = p.relative_to(ROOT)
            out.write("\n")
            out.write(f"---8<--- {rel.as_posix()} BEGIN ---\n")
            out.write("```" + f"{p.suffix.lower().lstrip('.') or 'txt'}" + "\n")
            out.write(read_text_safely(p))
            out.write("\n```\n")
            out.write(f"---8<--- {rel.as_posix()} END ---\n")

        out.write("\n## STATISTIQUES\n")
        total_bytes = sum((p.stat().st_size for p in files), 0)
        out.write(f"- Total fichiers exportés : {len(files)}\n")
        out.write(f"- Poids cumulé (approx) : {total_bytes/1024:.1f} Ko\n")
        out.write(f"- Limite par fichier : {SIZE_LIMIT_KB} Ko\n")

    print(f"✅ Export écrit : {OUTFILE}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
