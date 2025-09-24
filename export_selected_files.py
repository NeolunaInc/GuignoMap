# export_selected_files.py
from __future__ import annotations
import hashlib, sys
from pathlib import Path
from datetime import datetime

# --- Liste EXACTE des fichiers à exporter (chemins relatifs à la racine) ---
FILES = [
    "README.md",
    "requirements.txt",
    "lancer_guignomap.ps1",
    "geocode_online.py",
    "geocode_offline.py",
    ".gitignore",
    ".streamlit/config.toml",
    ".streamlit/secrets.toml",
    ".vscode/settings.json",
    ".vscode/tasks.json",
    "guignomap/__init__.py",
    "guignomap/app.py",
    "guignomap/backup.py",
    "guignomap/db.py",
    "guignomap/db.py.bak",
    "guignomap/import_civic.py",
    "guignomap/osm.py",
    "guignomap/reports.py",
    "guignomap/validators.py",
    "guignomap/assets/styles.css",
]

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def read_text_any(path: Path) -> str:
    # lit en UTF-8; si caractère invalide -> remplace (le contenu reste lisible)
    return path.read_text(encoding="utf-8", errors="replace")

def main():
    root = Path(__file__).resolve().parent
    out_dir = root / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"export_selected_{stamp}.txt"

    lines = []
    header = [
        "# ==============================================================================",
        "# EXPORT CONCATÉNÉ – FICHIERS SÉLECTIONNÉS",
        f"# Racine: {root}",
        f"# Généré : {datetime.now().isoformat(timespec='seconds')}",
        "# ATTENTION: contient potentiellement des secrets (.streamlit/secrets.toml)",
        "# ==============================================================================",
        "",
    ]
    lines.extend(header)

    missing = []
    for rel in FILES:
        p = root / rel
        if not p.exists():
            missing.append(rel)
            continue

        data = p.read_bytes()
        text = data.decode("utf-8", errors="replace")
        size = len(data)
        digest = sha256_bytes(data)

        lines.append(f"\n\n########## BEGIN FILE: {rel} ##########")
        lines.append(f"# size={size} bytes | sha256={digest}")
        lines.append(f"########## CONTENT ##########\n")
        lines.append(text.rstrip("\n"))  # évite double-sauts en fin
        lines.append(f"\n########## END FILE: {rel} ##########")

    if missing:
        lines.append("\n\n# --- FICHIERS MANQUANTS ---")
        for m in missing:
            lines.append(f"# MISSING: {m}")

    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"OK -> {out_file}")
    if missing:
        print("⚠️  Manquants:", ", ".join(missing))

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERREUR: {e}", file=sys.stderr)
        sys.exit(1)
