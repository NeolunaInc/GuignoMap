# coding: utf-8
"""
Export d’audit GuignoMap → exports/export_audit_YYYYMMDD_HHMMSS.txt

Objectifs:
- Inclure 100% du contenu de TOUS les fichiers .py (src/, tests/, scripts/, guignomap/…)
- Inclure fichiers importants: config (toml/yaml/ini/json/sql), alembic.ini, migrations, requirements*, pyproject.toml, Dockerfile, .gitignore, README.md
- Exclure: backups, exports, caches, pycache, venv, .git, binaires, secrets (.streamlit/secrets.toml)
- Ajouter une section ENV avec: version Python, chemin exécutable, plateforme, LISTE COMPLETE des paquets installés
Sortie: UTF-8 (LF), sans BOM
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime
import sys, platform, subprocess

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "exports"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUTFILE = OUTDIR / f"export_audit_{datetime.now():%Y%m%d_%H%M%S}.txt"

# Dossiers à exclure totalement
EXCLUDE_DIRS = {
    ".git", ".github", ".venv", "venv", "env", ".vscode", "__pycache__", ".pytest_cache", ".mypy_cache",
    "node_modules", "storage_local", "backups", "exports", "logs", ".idea", ".DS_Store"
}

# Fichiers exactement exclus (secrets etc.)
EXCLUDE_FILES = {
    "secrets.toml",  # ne jamais sortir les secrets
    ".python-version"
}

# Extensions autorisées pour les fichiers non-.py, considérés “importants à auditer”
ALLOW_NONPY_EXTS = {
    ".toml", ".ini", ".cfg", ".conf", ".yml", ".yaml", ".json", ".sql",
    ".md", ".txt", ".ps1", ".bat", ".sh", ".dockerignore"
}

# Fichiers/chemins “importants” acceptés même sans extension (ou spécifiques)
ALLOW_SPECIAL_PATHS = {
    "alembic.ini",
    "Dockerfile",
    ".gitignore",
    ".env.example",
    ".streamlit/config.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
}

# Préfixes utiles (whitelist de zones pertinentes)
ALLOW_PREFIXES = [
    "src/",
    "tests/",
    "scripts/",
    "guignomap/",
    "src/database/migrations/",
]

# Ne PAS limiter la taille des .py (on les veut ENTIEREMENT)
MAX_NONPY_SIZE = 200 * 1024  # 200KB pour les non-.py (pour éviter blobs inutiles)

def is_excluded_path(p: Path) -> bool:
    for part in p.parts:
        if part in EXCLUDE_DIRS:
            return True
    return False

def is_allowed_file(p: Path) -> bool:
    if p.name in EXCLUDE_FILES:
        return False

    rel = p.relative_to(ROOT).as_posix()

    # .py → toujours inclus s'il est dans une zone pertinente
    if p.suffix.lower() == ".py":
        if any(rel == pre or rel.startswith(pre) for pre in ALLOW_PREFIXES):
            return True
        return False

    # Fichiers spéciaux explicitement autorisés
    if rel in ALLOW_SPECIAL_PATHS:
        return True

    # Fichiers non-.py: extension autorisée ET dans une zone pertinente
    if p.suffix.lower() in ALLOW_NONPY_EXTS:
        if any(rel == pre or rel.startswith(pre) for pre in ALLOW_PREFIXES):
            return True

    return False

def read_text_utf8(p: Path) -> str:
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        txt = f"<<ERREUR LECTURE {p}: {e}>>"
    return txt.replace("\r\n", "\n").replace("\r", "\n")

def collect_files() -> list[Path]:
    files: list[Path] = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if is_excluded_path(p):
            continue
        if not is_allowed_file(p):
            continue

        # Taille: .py = aucune limite; autres = borne raisonnable
        if p.suffix.lower() != ".py":
            try:
                if p.stat().st_size > MAX_NONPY_SIZE:
                    continue
            except Exception:
                continue

        files.append(p)

    files.sort(key=lambda x: x.relative_to(ROOT).as_posix().lower())
    return files

def get_installed_packages() -> list[str]:
    """Retourne une liste 'Nom==Version' triée, en évitant les attributs privés."""
    # 1) Tentative avec importlib.metadata (propre)
    try:
        from importlib.metadata import distributions
        pkgs = []
        for dist in distributions():
            meta = getattr(dist, "metadata", None)
            # meta est un email.message.Message (supporte .get)
            name = None
            if meta:
                name = meta.get("Name")
            ver = getattr(dist, "version", None)
            if name and ver:
                pkgs.append(f"{name}=={ver}")
        if pkgs:
            return sorted(pkgs, key=lambda s: s.lower())
    except Exception:
        pass

    # 2) Fallback avec pkg_resources (setuptools)
    try:
        import pkg_resources  # type: ignore
        pkgs = [f"{d.project_name}=={d.version}" for d in pkg_resources.working_set]
        if pkgs:
            return sorted(set(pkgs), key=lambda s: s.lower())
    except Exception:
        pass

    # 3) Dernier recours: pip freeze (synchronisé avec l’environnement courant)
    try:
        out = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True, encoding="utf-8")
        pkgs = [line.strip() for line in out.splitlines() if line.strip()]
        if pkgs:
            return sorted(pkgs, key=lambda s: s.lower())
    except Exception as e:
        return [f"<<ERREUR INVENTAIRE DEPENDANCES: {e}>>"]

    return []

def env_section() -> str:
    lines: list[str] = []
    lines.append("## ENVIRONNEMENT")
    lines.append(f"- Python : {sys.version.splitlines()[0]}")
    lines.append(f"- Exécutable : {sys.executable}")
    lines.append(f"- Plateforme : {platform.platform()}")

    # versions utiles si présentes
    try:
        import streamlit as _st
        lines.append(f"- streamlit : {_st.__version__}")
    except Exception:
        pass
    try:
        import sqlalchemy as _sa
        lines.append(f"- sqlalchemy : {_sa.__version__}")
    except Exception:
        pass
    try:
        import pandas as _pd
        lines.append(f"- pandas : {_pd.__version__}")
    except Exception:
        pass
    try:
        import boto3 as _b3
        lines.append(f"- boto3 : {_b3.__version__}")
    except Exception:
        pass
    try:
        import passlib as _pl  # noqa
        lines.append("- passlib : présent")
    except Exception:
        pass

    lines.append("")
    lines.append("### Dépendances installées (inventaire)")
    pkgs = get_installed_packages() or ["<<Aucune dépendance détectée>>"]
    lines.extend(pkgs)
    lines.append("")
    return "\n".join(lines)

def main() -> int:
    files = collect_files()

    header = [
        "# GuignoMap — Export d’audit COMPLET (code et config utiles)",
        f"# Date : {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"# Racine : {ROOT}",
        "# Contenu : 100% des .py (zones pertinentes) + fichiers de config/migrations essentiels",
        "# Exclus : backups, exports, caches, venv, .git, binaires, secrets (.streamlit/secrets.toml)",
        ""
    ]

    with OUTFILE.open("w", encoding="utf-8", newline="\n") as out:
        out.write("\n".join(header) + "\n")
        out.write(env_section() + "\n")

        out.write("## INDEX DES FICHIERS INCLUS\n")
        for p in files:
            out.write(f"- {p.relative_to(ROOT).as_posix()}\n")

        out.write("\n## CONTENU DES FICHIERS\n")
        for p in files:
            rel = p.relative_to(ROOT).as_posix()
            out.write(f"\n---8<--- {rel} BEGIN ---\n")
            out.write("```" + (p.suffix.lower().lstrip(".") or "txt") + "\n")
            out.write(read_text_utf8(p))
            out.write("\n```\n")
            out.write(f"---8<--- {rel} END ---\n")

        out.write("\n## NOTE\n- Secrets exclus par conception (ex: .streamlit/secrets.toml)\n")
        out.write("- Tous les .py des zones pertinentes sont inclus en intégralité.\n")

    print(f"✅ Export d’audit écrit : {OUTFILE}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
