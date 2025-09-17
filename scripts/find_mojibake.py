#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scanner de fichiers pour détecter les chaînes mojibakées

Parcourt les fichiers texte (.py/.md/.toml/.json/.csv) et signale les lignes
contenant des motifs fréquents de corruption d'encodage.

Usage:
    python scripts/find_mojibake.py
    python scripts/find_mojibake.py --verbose
    python scripts/find_mojibake.py --extensions .py,.md,.txt
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Set, Tuple

# Ajouter le répertoire parent au path pour importer src/
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Motifs fréquents de mojibake (CP1252 -> UTF-8 mal interprété)
MOJIBAKE_PATTERNS = [
    "Ã",      # À mal encodé
    "√©",     # é mal encodé  
    "√≠",     # í mal encodé
    "√†",     # à mal encodé
    "√®",     # è mal encodé
    "√§",     # ç mal encodé
    "Ñ",      # caractères spéciaux
    "ü",      # caractères étendus
    "Ô",      # caractères maths/spéciaux
    "∏",      # symboles
    "´",      # accents isolés
    "ˆ",      # accents isolés
    "¬",      # symboles logiques
    "∙",      # puces spéciales
    "Ã©",     # é spécifique
    "Ã¨",     # è spécifique  
    "Ã ",     # à spécifique
    "Ã´",     # ô spécifique
    "Ã»",     # û spécifique
    "â€",     # guillemets/tirets problématiques
]

# Extensions de fichiers à scanner par défaut
DEFAULT_EXTENSIONS = {'.py', '.md', '.toml', '.json', '.csv', '.txt', '.sql'}

# Répertoires à ignorer
IGNORE_DIRS = {'.git', '.venv', '__pycache__', 'node_modules', '.pytest_cache', 'backups'}

# Fichiers à ignorer complètement (contiennent volontairement des patterns mojibake)
ALLOWLIST_FILES = {"scripts/find_mojibake.py", "scripts/fix_mojibake_db.py", "scripts/fix_mojibake_files.py"}


def find_mojibake_in_file(file_path: Path, patterns: List[str], verbose: bool = False) -> List[Tuple[int, str]]:
    """
    Analyse un fichier et retourne les lignes contenant du mojibake
    
    Returns:
        List de tuples (numéro_ligne, ligne_contenu)
    """
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line_num, line in enumerate(f, 1):
                for pattern in patterns:
                    if pattern in line:
                        issues.append((line_num, line.strip()))
                        if verbose:
                            print(f"  -> L{line_num}: motif '{pattern}' trouvé")
                        break  # Une seule alerte par ligne
                        
    except Exception as e:
        if verbose:
            print(f"⚠️  Erreur lecture {file_path}: {e}")
    
    return issues


def scan_directory(root_dir: Path, extensions: Set[str], patterns: List[str], verbose: bool = False) -> dict:
    """
    Scanne récursivement un répertoire
    
    Returns:
        Dict {file_path: [(line_num, line_content), ...]}
    """
    results = {}
    files_scanned = 0
    
    for file_path in root_dir.rglob('*'):
        # Ignorer les répertoires exclus
        if any(part in IGNORE_DIRS for part in file_path.parts):
            continue
        
        # Vérifier si le fichier est dans l'allowlist (chemin relatif)
        try:
            relative_path = file_path.relative_to(root_dir)
            if str(relative_path).replace('\\', '/') in ALLOWLIST_FILES:
                if verbose:
                    print(f"⚪ Ignoré (allowlist): {file_path}")
                continue
        except ValueError:
            pass
            
        # Vérifier l'extension
        if file_path.suffix.lower() not in extensions:
            continue
            
        if file_path.is_file():
            files_scanned += 1
            if verbose:
                print(f"📄 Scan: {file_path}")
                
            issues = find_mojibake_in_file(file_path, patterns, verbose)
            if issues:
                results[file_path] = issues
    
    if verbose:
        print(f"\n📊 {files_scanned} fichiers scannés")
    
    return results


def print_results(results: dict, verbose: bool = False):
    """Affiche les résultats du scan"""
    if not results:
        print("✅ Aucun mojibake détecté !")
        return
    
    print(f"🔍 {len(results)} fichier(s) avec du mojibake potentiel détecté:\n")
    
    total_issues = 0
    for file_path, issues in results.items():
        print(f"📁 {file_path}")
        for line_num, line_content in issues:
            total_issues += 1
            # Limiter l'affichage de la ligne pour la lisibilité
            display_line = line_content[:100] + "..." if len(line_content) > 100 else line_content
            print(f"   L{line_num:3d}: {display_line}")
        print()
    
    print(f"🎯 Total: {total_issues} ligne(s) problématique(s)")


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Scanner de mojibake dans les fichiers texte")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Affichage détaillé du scan")
    parser.add_argument("--extensions", "-e", type=str, 
                       help="Extensions à scanner (ex: .py,.md,.txt)")
    parser.add_argument("--directory", "-d", type=str, default=".",
                       help="Répertoire à scanner (défaut: .)")
    
    args = parser.parse_args()
    
    # Parse des extensions
    if args.extensions:
        extensions = {ext.strip() for ext in args.extensions.split(',')}
        if not all(ext.startswith('.') for ext in extensions):
            print("❌ Les extensions doivent commencer par un point (ex: .py,.md)")
            return 1
    else:
        extensions = DEFAULT_EXTENSIONS
    
    root_dir = Path(args.directory).resolve()
    if not root_dir.exists():
        print(f"❌ Répertoire introuvable: {root_dir}")
        return 1
    
    print(f"🔍 Scan mojibake dans: {root_dir}")
    print(f"📋 Extensions: {', '.join(sorted(extensions))}")
    print(f"🎯 Motifs recherchés: {len(MOJIBAKE_PATTERNS)}")
    if args.verbose:
        print(f"🔎 Motifs: {', '.join(MOJIBAKE_PATTERNS[:10])}...")
    print()
    
    # Scan
    results = scan_directory(root_dir, extensions, MOJIBAKE_PATTERNS, args.verbose)
    
    # Affichage
    print_results(results, args.verbose)
    
    return 0 if not results else 1


if __name__ == "__main__":
    sys.exit(main())