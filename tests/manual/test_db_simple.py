#!/usr/bin/env python3
"""Test simple de connexion base de données"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_db_simple():
    try:
        from src.database.connection import get_engine, test_connection
        
        print("=== Test de connexion base de données ===")
        
        # Test avec la fonction dédiée
        print("1. Test avec test_connection():")
        test_connection()
        
        # Test manuel avec engine
        print("\n2. Test manuel avec engine:")
        engine = get_engine()
        print(f"✅ Engine créé: {engine.url}")
        
        # Tester la connexion
        with engine.connect() as conn:
            result = conn.execute("SELECT 1 as test")
            test_value = result.fetchone()[0]
            print(f"✅ Connexion réussie! Test query result: {test_value}")
        
        print("✅ Connexion base de données fonctionnelle!")
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