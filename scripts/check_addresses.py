#!/usr/bin/env python3
"""
Script de diagnostic pour analyser l'état de la base de données d'adresses
"""
import sqlite3
import sys
from pathlib import Path
import pandas as pd

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from guignomap.database import get_conn, stats_addresses, get_unassigned_addresses, get_team_addresses


def analyze_database():
    """Analyse complète de la base de données"""
    print("=" * 60)
    print("🔍 DIAGNOSTIC BASE DE DONNÉES - GuignoMap")
    print("=" * 60)
    
    # 1. Tables et index
    print("\n📋 STRUCTURE DE LA BASE")
    with get_conn() as conn:
        cursor = conn.cursor()
        
        # Lister les tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   Tables: {', '.join(tables)}")
        
        # Lister les index
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        indexes = [row[0] for row in cursor.fetchall()]
        print(f"   Index personnalisés: {len(indexes)}")
        for idx in indexes[:5]:  # Afficher les 5 premiers
            print(f"     - {idx}")
        if len(indexes) > 5:
            print(f"     ... et {len(indexes) - 5} autres")
    
    # 2. Statistiques globales
    print("\n📊 STATISTIQUES GLOBALES")
    stats = stats_addresses()
    print(f"   Total adresses: {stats['total']:,}")
    print(f"   Non assignées: {stats['unassigned']:,}")
    print(f"   Assignées: {stats['assigned']:,}")
    print(f"   Géocodées: {stats['percent_geocoded']}%")
    print(f"   Équipes actives: {len(stats['per_team'])}")
    
    # 3. Top 10 non assignées
    print("\n🏠 TOP 10 ADRESSES NON ASSIGNÉES")
    unassigned = get_unassigned_addresses(limit=10)
    if len(unassigned) > 0:
        for _, row in unassigned.iterrows():
            sector_info = f" [{row['sector']}]" if pd.notna(row['sector']) else ""
            print(f"   {row['id']:>6} - {row['street_name']} {row['house_number']}{sector_info}")
    else:
        print("   ✅ Aucune adresse non assignée")
    
    # 4. Top 10 équipes par nombre d'adresses
    print("\n👥 TOP 10 ÉQUIPES PAR NOMBRE D'ADRESSES")
    sorted_teams = sorted(stats['per_team'].items(), key=lambda x: x[1], reverse=True)
    for i, (team, count) in enumerate(sorted_teams[:10], 1):
        percent = round((count / stats['total'] * 100), 1) if stats['total'] > 0 else 0
        print(f"   {i:>2}. {team:<20} : {count:>6,} adresses ({percent:>5.1f}%)")
        
        # Montrer 3 exemples d'adresses pour cette équipe
        team_addresses = get_team_addresses(team, limit=3)
        for _, addr in team_addresses.iterrows():
            sector_info = f" [{addr['sector']}]" if pd.notna(addr['sector']) else ""
            print(f"       ├─ {addr['street_name']} {addr['house_number']}{sector_info}")
    
    # 5. Détection de problèmes potentiels
    print("\n⚠️  DÉTECTION DE PROBLÈMES")
    with get_conn() as conn:
        cursor = conn.cursor()
        
        # Adresses sans nom de rue
        cursor.execute("SELECT COUNT(*) FROM addresses WHERE street_name IS NULL OR street_name = ''")
        no_street = cursor.fetchone()[0]
        if no_street > 0:
            print(f"   ❌ {no_street} adresses sans nom de rue")
        
        # Adresses sans numéro
        cursor.execute("SELECT COUNT(*) FROM addresses WHERE house_number IS NULL OR house_number = ''")
        no_number = cursor.fetchone()[0]
        if no_number > 0:
            print(f"   ❌ {no_number} adresses sans numéro")
        
        # Clés en doublon
        cursor.execute("""
            SELECT addr_key, COUNT(*) as count 
            FROM addresses 
            GROUP BY addr_key 
            HAVING count > 1
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"   ❌ {len(duplicates)} clés addr_key en doublon")
            for key, count in duplicates[:3]:
                print(f"       ├─ '{key}' : {count} occurrences")
        
        # Équipes orphelines (assignées mais pas dans la table teams)
        cursor.execute("""
            SELECT DISTINCT assigned_to 
            FROM addresses 
            WHERE assigned_to IS NOT NULL 
              AND assigned_to != ''
              AND assigned_to NOT IN (SELECT name FROM teams)
        """)
        orphan_teams = [row[0] for row in cursor.fetchall()]
        if orphan_teams:
            print(f"   ⚠️  {len(orphan_teams)} équipes assignées mais non déclarées:")
            for team in orphan_teams[:5]:
                print(f"       ├─ '{team}'")
        
        if no_street == 0 and no_number == 0 and not duplicates and not orphan_teams:
            print("   ✅ Aucun problème détecté")
    
    print("\n" + "=" * 60)
    print("✅ Diagnostic terminé")


if __name__ == "__main__":
    try:
        analyze_database()
    except Exception as e:
        print(f"❌ Erreur lors du diagnostic: {e}")
        sys.exit(1)