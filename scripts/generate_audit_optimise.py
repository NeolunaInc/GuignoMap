#!/usr/bin/env python3
"""
Script de génération d'export optimisé pour audit GuignoMap
Version allégée - SANS backups, __pycache__, logs, etc.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import subprocess

# Configuration
OUTPUT_FILE = "export_audit_optimise.txt"
PROJECT_ROOT = Path(__file__).parent.parent

# Liste OPTIMISÉE des fichiers essentiels pour l'audit
FICHIERS_AUDIT_ESSENTIELS = [
    # Configuration principale
    ".streamlit/config.toml",
    ".streamlit/secrets.toml.example",  # Template secrets
    "streamlit_app.py",
    "requirements.txt",
    "requirements_freeze.txt",
    ".gitignore",
    "runtime.txt",                      # Version Python Streamlit Cloud
    "alembic.ini",                      # Configuration Alembic
    
    # Application principale (SEULEMENT les fichiers sources)
    "guignomap/__init__.py",
    "guignomap/app.py",
    "guignomap/db_v5.py",
    "guignomap/db.py",                  # Legacy DB (pour migration)
    "guignomap/backup.py",              # Système de sauvegarde
    "guignomap/osm.py",
    "guignomap/validators.py", 
    "guignomap/reports.py",
    "guignomap/assets/styles.css",
    
    # Architecture source
    "src/__init__.py",
    "src/config.py",
    "src/auth/passwords.py",
    "src/database/connection.py",
    "src/database/models.py",
    "src/database/db_v5.py",            # Vérifier si différent de guignomap/db_v5.py
    "src/storage/__init__.py",          # Init module storage
    "src/storage/cloud.py",
    "src/storage/local.py",
    "src/utils/__init__.py",            # Init module utils
    "src/utils/adapters.py",
    
    # Scripts utilitaires essentiels
    "scripts/sanity_db_pandas.py",
    "scripts/smoke_create_map.py",
    "scripts/migrate_password_hashes.py",    # Migration Argon2
    "scripts/migrate_sqlite_to_postgres.py", # Migration DB
    "tools/quick_sanity.py",
    
    # Migration Alembic
    "src/database/migrations/env.py",
    "src/database/migrations/script.py.mako",  # Template migration
    
    # Tests essentiels
    "tests/manual/test_db_connection.py",
    "tests/manual/test_db_simple.py",
    
    # Configuration développement
    ".vscode/tasks.json",               # Tâches automatisées
    ".devcontainer/devcontainer.json",  # Configuration Dev Container
]

# Fichiers à EXCLURE explicitement 
FICHIERS_A_EXCLURE = [
    "__pycache__",
    ".venv",
    "backups",
    "logs", 
    "*.log",
    "*.pyc",
    "*.pyo",
    "*.db",
    "*.sqlite",
    "*.zip",
    "node_modules",
    ".git",
    "exports/export_*.txt",  # Éviter les anciens exports
]

def get_system_info_minimal():
    """Récupère les informations système essentielles"""
    try:
        python_version = subprocess.check_output([sys.executable, "--version"], text=True).strip()
        
        # Packages essentiels seulement
        essential_packages = [
            "streamlit", "pandas", "folium", "sqlalchemy", "psycopg2-binary", 
            "passlib", "boto3", "reportlab", "xlsxwriter", "overpy"
        ]
        
        pip_output = subprocess.check_output([sys.executable, "-m", "pip", "list"], text=True)
        essential_pip = []
        for line in pip_output.split('\n'):
            for pkg in essential_packages:
                if line.lower().startswith(pkg.lower()):
                    essential_pip.append(line)
                    break
        
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        git_branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
        
        return {
            "python_version": python_version,
            "essential_packages": "\n".join(essential_pip),
            "git_commit": git_commit,
            "git_branch": git_branch,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        return {"error": str(e)}

def read_file_safe(file_path):
    """Lit un fichier de manière sécurisée avec limitation de taille"""
    try:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            return None
        
        # Limiter la taille des fichiers lus (max 500KB)
        size = full_path.stat().st_size
        if size > 500 * 1024:  # 500KB max
            return f"## {file_path} (FICHIER TROP VOLUMINEUX - {size/1024:.1f}KB)\n❌ Fichier non inclus (> 500KB)\n\n"
        
        # Essayer plusieurs encodages pour éviter les caractères corrompus
        encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
        content = None
        
        for encoding in encodings:
            try:
                with open(full_path, 'r', encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            # En dernier recours, mode binaire et décodage manuel
            with open(full_path, 'rb') as f:
                raw_content = f.read()
                content = raw_content.decode('utf-8', errors='ignore')
        
        # Déterminer l'extension pour le formatage
        suffix = full_path.suffix.lower()
        if suffix in ['.py']:
            lang = 'python'
        elif suffix in ['.css']:
            lang = 'css'
        elif suffix in ['.toml']:
            lang = 'toml'
        elif suffix in ['.json']:
            lang = 'json'
        elif suffix in ['.txt', '.md']:
            lang = 'text'
        else:
            lang = 'text'
        
        lines_count = len(content.splitlines())
        size_kb = len(content.encode('utf-8')) / 1024
        
        return f"""## {file_path} ({lines_count} lignes, {size_kb:.1f}KB)
```{lang}
{content}
```

"""
    except Exception as e:
        return f"❌ ERREUR lecture {file_path}: {str(e)}\n"

def main():
    """Fonction principale optimisée"""
    print(f"🚀 Génération de l'export d'audit OPTIMISÉ pour GuignoMap...")
    
    # Obtenir les infos système
    sys_info = get_system_info_minimal()
    
    # Commencer le fichier
    content = f"""# ================================================================================
# GUIGNOMAP - EXPORT OPTIMISÉ POUR AUDIT
# Date: {sys_info.get('date', 'Inconnue')}
# Python: {sys_info.get('python_version', 'Inconnu')}
# Git: {sys_info.get('git_branch', 'main')} ({sys_info.get('git_commit', 'unknown')[:8]})
# ================================================================================

# ================================================================================
# PACKAGES ESSENTIELS
# ================================================================================

{sys_info.get('essential_packages', 'Packages non disponibles')}

# ================================================================================
# STRUCTURE PROJET (Fichiers essentiels seulement)
# ================================================================================

GuignoMap/
├── .devcontainer/devcontainer.json     # 🔧 Configuration Dev Container  
├── .streamlit/
│   ├── config.toml                     # ⭐ Configuration Streamlit
│   └── secrets.toml.example            # 📋 Template secrets
├── .vscode/tasks.json                  # 🔧 Tâches automatisées VS Code
├── streamlit_app.py                    # ⭐ Point d'entrée Cloud
├── requirements.txt                    # 📦 Dépendances production
├── requirements_freeze.txt             # 📦 Versions exactes
├── runtime.txt                         # 🐍 Version Python (Cloud)
├── alembic.ini                         # 🔧 Configuration Alembic
├── .gitignore                          # 🚫 Exclusions Git
│
├── guignomap/                          # 🎯 Application principale
│   ├── __init__.py
│   ├── app.py                          # ⭐ Interface Streamlit (2000+ lignes)
│   ├── db_v5.py                        # ⭐ Base de données SQLAlchemy
│   ├── db.py                           # 🔄 Legacy DB (migration)
│   ├── backup.py                       # 💾 Système de sauvegarde
│   ├── osm.py                          # ⭐ Intégration OpenStreetMap
│   ├── validators.py                   # 🛡️ Validation sécurisée
│   ├── reports.py                      # 📊 Génération rapports
│   └── assets/styles.css               # 🎨 Styles CSS
│
├── src/                                # 🏗️ Architecture modulaire
│   ├── __init__.py                     # Init module principal
│   ├── config.py                       # ⭐ Configuration centralisée
│   ├── auth/passwords.py               # 🛡️ Authentification Argon2
│   ├── database/
│   │   ├── connection.py               # ⭐ Connexions PostgreSQL
│   │   ├── models.py                   # ⭐ Modèles SQLAlchemy
│   │   ├── db_v5.py                    # 🔄 Opérations DB (duplicate?)
│   │   └── migrations/
│   │       ├── env.py                  # Configuration Alembic
│   │       └── script.py.mako          # Template migration
│   ├── storage/
│   │   ├── __init__.py                 # Init module storage
│   │   ├── cloud.py                    # ☁️ Stockage S3
│   │   └── local.py                    # 💻 Stockage local
│   └── utils/
│       ├── __init__.py                 # Init module utils
│       └── adapters.py                 # 🔄 Adaptateurs données
│
├── scripts/                            # 🔧 Scripts utilitaires
│   ├── sanity_db_pandas.py             # 🔍 Vérification DB
│   ├── smoke_create_map.py             # 🗺️ Test carte
│   ├── migrate_password_hashes.py      # 🔐 Migration Argon2
│   └── migrate_sqlite_to_postgres.py   # 🔄 Migration PostgreSQL
│
├── tests/manual/                       # 🧪 Tests manuels
│   ├── test_db_connection.py           # Test connexion DB
│   └── test_db_simple.py               # Test simple DB
│
└── tools/
    └── quick_sanity.py                 # ⚡ Vérification rapide

# ================================================================================
# FICHIERS SOURCES COMPLETS
# ================================================================================

"""
    
    # Lire tous les fichiers essentiels
    print(f"📁 Lecture de {len(FICHIERS_AUDIT_ESSENTIELS)} fichiers essentiels...")
    
    fichiers_lus = 0
    fichiers_manquants = []
    taille_totale = 0
    
    for fichier in FICHIERS_AUDIT_ESSENTIELS:
        print(f"  📄 {fichier}")
        file_content = read_file_safe(fichier)
        
        if file_content is None:
            fichiers_manquants.append(fichier)
            continue
        elif "❌" in file_content and "ERREUR" in file_content:
            fichiers_manquants.append(fichier)
            content += file_content
        else:
            content += file_content
            fichiers_lus += 1
            taille_totale += len(file_content.encode('utf-8'))
    
    # Ajouter JSON essentiels (s'ils existent et sont raisonnables)
    json_essentiels = ["guignomap/osm_addresses.json"]  # Seulement celui-ci
    
    content += """# ================================================================================
# DONNÉES JSON ESSENTIELLES
# ================================================================================

"""
    
    for json_file in json_essentiels:
        json_content = read_file_safe(json_file)
        if json_content and "❌" not in json_content:
            content += json_content
    
    # Résumé final optimisé
    content += f"""
# ================================================================================
# RÉSUMÉ DE L'EXPORT OPTIMISÉ
# ================================================================================

✅ Fichiers inclus: {fichiers_lus}/{len(FICHIERS_AUDIT_ESSENTIELS)}
📊 Taille totale: {taille_totale/1024:.1f}KB
🚫 Exclusions: __pycache__, backups, logs, .venv, *.pyc, *.db

"""
    
    if fichiers_manquants:
        content += f"⚠️ Fichiers non trouvés ({len(fichiers_manquants)}):\n"
        for fichier in fichiers_manquants:
            content += f"  - {fichier}\n"
        content += "\n"
    
    content += f"""
# ================================================================================
# POINTS CLÉS POUR L'AUDIT
# ================================================================================

🔍 SÉCURITÉ (Priorité 1):
- src/auth/passwords.py          # Hachage Argon2
- guignomap/validators.py        # Anti-XSS/injection
- src/config.py                  # Gestion secrets

📊 BASE DE DONNÉES (Priorité 2):  
- guignomap/db_v5.py            # ORM SQLAlchemy
- src/database/connection.py     # Pool PostgreSQL
- src/database/models.py         # Schéma DB

🎨 INTERFACE (Priorité 3):
- guignomap/app.py              # Interface Streamlit
- guignomap/osm.py              # Cartes OpenStreetMap
- streamlit_app.py              # Point d'entrée

⚙️ CONFIGURATION:
- .streamlit/config.toml        # Thème et config
- requirements.txt              # Dépendances

ARCHITECTURE: Streamlit + PostgreSQL + Folium + S3
DÉPLOIEMENT: Compatible Streamlit Cloud
VERSION: v3.0 Production

===============================================================================
FIN EXPORT OPTIMISÉ - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
===============================================================================
"""
    
    # Écrire le fichier final
    output_path = PROJECT_ROOT / OUTPUT_FILE
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    final_size = len(content.encode('utf-8')) / 1024
    print(f"✅ Export optimisé généré: {output_path}")
    print(f"📊 Fichiers inclus: {fichiers_lus}/{len(FICHIERS_AUDIT_ESSENTIELS)}")
    print(f"📄 Taille finale: {final_size:.1f}KB")
    print(f"🚫 Exclusions: __pycache__, backups, logs, .venv")
    
    if fichiers_manquants:
        print(f"⚠️  {len(fichiers_manquants)} fichiers non trouvés")

if __name__ == "__main__":
    main()