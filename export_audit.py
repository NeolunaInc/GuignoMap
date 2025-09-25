#!/usr/bin/env python3
"""
Script d'export d'audit pour GuignoMap.
Génère un fichier exports/export_for_audit_YYYYMMDD_HHMM.txt avec :
- Versions Python et dépendances installées
- Arborescence propre (via tree_clean.py)
- Contenu complet des fichiers critiques
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Fichiers à inclure en entier
FILES_TO_INCLUDE = [
    ".streamlit/config.toml",
    ".streamlit/secrets.toml",
    ".vscode/settings.json",
    ".vscode/tasks.json",
    "guignomap/assets/styles.css",
    "guignomap/__init__.py",
    "guignomap/app.py",
    "guignomap/backup.py",
    "guignomap/db.py",
    "guignomap/db.py.bak",
    "guignomap/export_utils.py",
    "guignomap/helpers_gm.py",
    "guignomap/import_civic.py",
    "guignomap/osm.py",
    "guignomap/reports.py",
    "guignomap/validators.py",
    "tests/smoke_db_missing_api.py",
    "tests/smoke_db_status_api.py",
    "import_postal_codes_v2.py",
    "README.md",
    "requirements.txt",
    "DEPLOYMENT.md",
    ".gitignore"
    ]

def get_python_version():
    return sys.version

def get_installed_packages():
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list"], capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return f"Erreur récupération packages: {e}"

def get_tree():
    try:
        # Exécute tree_clean.py pour générer le fichier
        result = subprocess.run([
            sys.executable, "tree_clean.py"
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        # Cherche le dernier fichier tree_clean_*.txt dans exports
        exports_dir = Path(__file__).parent / "exports"
        tree_files = sorted(exports_dir.glob("tree_clean_*.txt"), reverse=True)
        if tree_files:
            tree_path = tree_files[0]
            try:
                return tree_path.read_text(encoding="utf-8")
            except Exception as e:
                return f"Erreur lecture fichier tree: {e}"
        else:
            return "Aucun fichier tree_clean_*.txt trouvé dans exports."
    except Exception as e:
        return f"Erreur génération tree: {e}"

def read_file_content(filepath):
    try:
        encodings = ['utf-8', 'utf-8-sig', 'utf-16', 'latin-1']
        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        return f"Erreur lecture {filepath}: Impossible de décoder avec les encodages testés"
    except FileNotFoundError:
        return f"Fichier manquant: {filepath}"

def main():
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M")
    timestamp = timestamp[:9] + timestamp[9:11] + "H" + timestamp[11:]
    output_file = Path("exports") / f"export_for_audit_{timestamp}.txt"

    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("============================================================\n")
        f.write("EXPORT D'AUDIT - GUIGNOMAP\n")
        f.write("============================================================\n")
        f.write(f"Généré le: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("Projet développé sous Windows via VSCode (pas WSL)\n")
        f.write(f"Version Python: {get_python_version()}\n")
        f.write("============================================================\n\n")

        # Dépendances installées
        f.write("DÉPENDANCES INSTALLÉES (.venv):\n")
        f.write("============================================================\n")
        f.write(get_installed_packages())
        f.write("============================================================\n\n")

        # Arborescence
        f.write("ARBORESCENCE (via tree_clean.py):\n")
        f.write("============================================================\n")
        f.write(get_tree())
        f.write("============================================================\n\n")

        # Contenu des fichiers
        f.write("CONTENU DES FICHIERS CRITIQUES:\n")
        f.write("============================================================\n")
        for filepath in FILES_TO_INCLUDE:
            f.write(f"\n--- {filepath} ---\n")
            content = read_file_content(filepath)
            f.write(content)
            f.write("\n")

    print(f"Export généré: {output_file}")

if __name__ == "__main__":
    main()