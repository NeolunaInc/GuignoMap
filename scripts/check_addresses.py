#!/usr/bin/env python3
"""
GuignoMap - Diagnostic Tool for Address Database
Check addresses count and sample data
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour l'import
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from guignomap import database as db
import sqlite3


def main():
    """Point d'entrée principal pour le diagnostic des adresses"""
    print("🔍 GuignoMap - Diagnostic des adresses")
    print("=" * 50)
    
    try:
        # Comptage des adresses non assignées
        unassigned_count = db.count_unassigned_addresses()
        print(f"📊 Adresses non assignées: {unassigned_count:,}")
        
        # Échantillon de données
        conn = db.get_conn()
        rows = conn.execute("""
            SELECT id, street_name, house_number, assigned_to 
            FROM addresses 
            LIMIT 5
        """).fetchall()
        
        print("\n📋 Échantillon de données:")
        print("-" * 30)
        for row in rows:
            assigned = row[3] if row[3] else "NON_ASSIGNÉE"
            print(f"  {row[0]:4d} | {row[1][:20]:20s} | {str(row[2]):6s} | {assigned}")
        
        conn.close()
        print("\n✅ Diagnostic terminé")
        
    except Exception as e:
        print(f"❌ Erreur lors du diagnostic: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())