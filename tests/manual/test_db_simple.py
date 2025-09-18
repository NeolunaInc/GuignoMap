#!/usr/bin/env python3
"""Test simple de connexion base de données SQLite"""

import sys
import os
import pytest
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

RUN_DB_EXT = bool(os.getenv("RUN_DB_EXT_TESTS"))

@pytest.mark.skipif(not RUN_DB_EXT, reason="External DB tests disabled; set RUN_DB_EXT_TESTS=1 to run")
def test_db_simple():
    try:
        import guignomap.database as db
        
        print("=== Test de connexion base de données SQLite ===")
        
        # Test des fonctions de base
        print("1. Test extended_stats():")
        stats = db.extended_stats()
        print(f"✅ Stats: {stats}")

        print("\n2. Test teams():")
        teams = db.teams()
        print(f"✅ Teams: {teams}")
        
        print("✅ Connexion base de données SQLite fonctionnelle!")
        assert True  # Connection successful
        
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        assert False, f"Database connection failed: {e}"

if __name__ == "__main__":
    try:
        test_db_simple()
        success = True
    except AssertionError:
        success = False
    sys.exit(0 if success else 1)