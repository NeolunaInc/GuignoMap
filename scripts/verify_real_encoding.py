#!/usr/bin/env python3
"""
Script de vérification de l'encodage réel des fichiers
Teste si les fichiers sont vraiment lisibles en UTF-8
"""
import sys
from pathlib import Path

def check_file(filepath):
    """Vérifie l'encodage réel d'un fichier"""
    try:
        # Test 1: UTF-8 strict
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return "UTF-8", len(content), "OK"
    except UnicodeDecodeError as e:
        # Test 2: UTF-8 avec BOM
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                return "UTF-8-BOM", len(content), "Has BOM"
        except:
            # Test 3: Windows-1252
            try:
                with open(filepath, 'r', encoding='windows-1252') as f:
                    content = f.read()
                    return "Windows-1252", len(content), "Legacy"
            except:
                return "Unknown", 0, str(e)

def main():
    # Tester les fichiers problématiques rapportés par validate_structure
    problem_files = [
        "guignomap/app.py",
        "src/database/operations.py", 
        "scripts/validate_structure.py",
        "check_admin.py",
        "README.md",
        "tools/quick_sanity.py"
    ]

    print("🔍 Vérification de l'encodage réel des fichiers")
    print("=" * 50)
    
    all_utf8 = True
    
    for file in problem_files:
        if Path(file).exists():
            encoding, size, status = check_file(file)
            print(f"{file}: {encoding} ({size} chars) - {status}")
            if encoding not in ["UTF-8", "UTF-8-BOM"]:
                all_utf8 = False
        else:
            print(f"{file}: NOT FOUND")
    
    print("=" * 50)
    if all_utf8:
        print("✅ Tous les fichiers testés sont lisibles en UTF-8")
        print("   Le problème vient de la détection charset, pas de l'encodage réel")
    else:
        print("❌ Certains fichiers nécessitent une conversion")

if __name__ == "__main__":
    main()