#!/usr/bin/env python3
"""
Script de ménage sécurisé - Phase 0
Nettoie les stubs et caches connus pour repartir sur des bases propres.

Ce script est idempotent et ne supprime que les fichiers explicitement listés.
"""

import os
import sys
from pathlib import Path

# Configuration des chemins à nettoyer
PATHS_TO_CLEAN = [
    "guignomap/osm.py",
    "guignomap/reports.py",  # Uniquement si c'est un stub vide
    "smoke_create_map.py",
    "tools/quick_sanity.py",
    "osm_cache.json",
    "osm_addresses.json",
]

def is_reports_stub_empty(filepath: Path) -> bool:
    """
    Vérifie si reports.py est un stub vide (contient seulement des méthodes print/fake).
    """
    if not filepath.exists():
        return False

    try:
        content = filepath.read_text(encoding='utf-8')
        # Considère comme stub si contient "Stub:" et des données fake
        return "Stub:" in content and "fake_" in content
    except Exception:
        return False

def safe_delete(path: str) -> bool:
    """
    Supprime un fichier de manière sécurisée.
    Retourne True si supprimé, False sinon.
    """
    filepath = Path(path)

    # Vérification spéciale pour reports.py
    if path == "guignomap/reports.py" and not is_reports_stub_empty(filepath):
        print(f"SKIP (not stub): {path}")
        return False

    if filepath.exists():
        try:
            if filepath.is_file():
                filepath.unlink()
                print(f"DELETE ok: {path}")
                return True
            else:
                print(f"SKIP (not file): {path}")
                return False
        except Exception as e:
            print(f"ERROR deleting {path}: {e}")
            return False
    else:
        print(f"SKIP (missing): {path}")
        return False

def main():
    """Point d'entrée principal."""
    print("=== GuignoMap Cleanup Phase 0 ===")
    print("Nettoyage sécurisé des stubs et caches connus")
    print()

    deleted_count = 0
    total_count = len(PATHS_TO_CLEAN)

    for path in PATHS_TO_CLEAN:
        if safe_delete(path):
            deleted_count += 1

    print()
    print(f"Résumé: {deleted_count}/{total_count} fichiers supprimés")
    print("Cleanup terminé avec succès!")

    return 0

if __name__ == "__main__":
    sys.exit(main())