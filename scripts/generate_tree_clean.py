#!/usr/bin/env python3
"""
Script pour générer un arbre propre du projet GuignoMap
Exclut les dossiers polluants comme __pycache__, .venv, backups, exports
"""

import os
from pathlib import Path
from datetime import datetime

def should_exclude(path: Path) -> bool:
    """Détermine si un chemin doit être exclu de l'arbre"""
    excludes = {
        '__pycache__',
        '.venv', 
        'backups',
        'exports',
        '.git',
        'node_modules',
        '.pytest_cache',
        '.coverage',
        '.mypy_cache'
    }
    
    # Exclure les dossiers/fichiers spécifiques
    if path.name in excludes:
        return True
    
    # Exclure les fichiers temporaires
    if path.suffix in {'.pyc', '.pyo', '.pyd', '.so', '.dll'}:
        return True
    
    # Exclure les fichiers de logs
    if path.suffix in {'.log'}:
        return True
        
    # Exclure les bases de données temporaires
    if path.suffix in {'.db', '.sqlite', '.sqlite3'} and 'test' not in path.name.lower():
        return True
    
    # Excluer les fichiers d'export précédents
    if path.name.startswith('export_') and path.suffix == '.txt':
        return True
        
    # Exclure les fichiers zip de backup
    if path.suffix == '.zip' and any(parent.name == 'backups' for parent in path.parents):
        return True
    
    return False

def generate_tree(root_path: Path, prefix: str = "", is_last: bool = True, max_depth: int = 10, current_depth: int = 0) -> list:
    """Génère un arbre des fichiers et dossiers"""
    if current_depth >= max_depth:
        return []
    
    tree_lines = []
    
    if current_depth == 0:
        tree_lines.append(f"{root_path.name}/")
    
    try:
        # Lister tous les éléments du dossier
        items = []
        for item in root_path.iterdir():
            if not should_exclude(item):
                items.append(item)
        
        # Trier : dossiers d'abord, puis fichiers, alphabétiquement
        items.sort(key=lambda x: (x.is_file(), x.name.lower()))
        
        for i, item in enumerate(items):
            is_last_item = i == len(items) - 1
            
            # Créer le préfixe pour cet élément
            connector = "└── " if is_last_item else "├── "
            current_prefix = prefix + connector
            
            if item.is_dir():
                # Dossier
                tree_lines.append(f"{current_prefix}{item.name}/")
                
                # Récursion pour le contenu du dossier
                next_prefix = prefix + ("    " if is_last_item else "│   ")
                subtree = generate_tree(item, next_prefix, is_last_item, max_depth, current_depth + 1)
                tree_lines.extend(subtree)
            else:
                # Fichier
                size_info = ""
                try:
                    size = item.stat().st_size
                    if size < 1024:
                        size_info = f" ({size}B)"
                    elif size < 1024 * 1024:
                        size_info = f" ({size/1024:.1f}KB)"
                    else:
                        size_info = f" ({size/(1024*1024):.1f}MB)"
                except:
                    size_info = ""
                
                tree_lines.append(f"{current_prefix}{item.name}{size_info}")
    
    except PermissionError:
        tree_lines.append(f"{prefix}└── [Permission denied]")
    
    return tree_lines

def main():
    """Fonction principale"""
    project_root = Path(__file__).parent
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("🌳 Génération de l'arbre du projet GuignoMap...")
    
    # Générer l'arbre
    tree_lines = generate_tree(project_root)
    
    # Créer le contenu du fichier
    content = f"""# ================================================================================
# ARBRE DU PROJET GUIGNOMAP - STRUCTURE COMPLÈTE
# Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Exclusions: __pycache__, .venv, backups/, exports/, .git, *.pyc, *.log
# ================================================================================

"""
    
    content += "\n".join(tree_lines)
    
    # Ajouter des statistiques
    total_lines = len(tree_lines)
    content += f"""

# ================================================================================
# STATISTIQUES
# ================================================================================

📊 Total éléments affichés: {total_lines}
🚫 Exclusions appliquées: __pycache__, .venv, backups, exports, *.pyc, *.log, *.db
📅 Généré le: {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')}

# ================================================================================
# LÉGENDE
# ================================================================================

📁 Dossiers se terminent par /
📄 Fichiers avec taille approximative
├── Élément dans la hiérarchie  
└── Dernier élément d'un niveau
│   Continuation de branche
    Espacement pour sous-éléments

# ================================================================================
# NOTES IMPORTANTES
# ================================================================================

✅ INCLUS:
- Tous les fichiers source (.py, .css, .toml, .md, etc.)
- Configuration et documentation 
- Scripts utilitaires et outils
- Fichiers de déploiement

❌ EXCLUS (polluants):
- __pycache__/ et *.pyc (cache Python)
- .venv/ (environnement virtuel)
- backups/ (sauvegardes automatiques)
- exports/ (exports précédents)
- .git/ (métadonnées Git)
- Fichiers temporaires et logs

===============================================================================
FIN ARBRE PROJET GUIGNOMAP - {timestamp}
===============================================================================
"""
    
    # Sauvegarder le fichier
    output_file = project_root / f"project_tree_clean_{timestamp}.txt"
    output_file.write_text(content, encoding='utf-8')
    
    print(f"✅ Arbre généré: {output_file.name}")
    print(f"📊 {total_lines} éléments inclus")
    print(f"📄 Fichier: {output_file}")

if __name__ == "__main__":
    main()