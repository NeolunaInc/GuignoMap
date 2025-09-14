#!/usr/bin/env python3
"""
Quick sanity check script for GuignoMap v4.1
Generates audit CSV files and displays key metrics.
"""

import sqlite3
import csv
import sys
from datetime import datetime
from pathlib import Path

def main():
    """Main sanity check function."""
    # Paths
    db_path = Path("guignomap") / "guigno_map.db"
    exports_dir = Path("exports")
    
    # Create exports directory if missing
    exports_dir.mkdir(exist_ok=True)
    
    # Check if database exists
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("ℹ️  Run the application first to create the database.")
        return 0
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Generate timestamp for files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        print("🔍 GuignoMap v4.1 - Quick Sanity Check")
        print("=" * 50)
        
        # Check if required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        if 'streets' not in tables:
            print("❌ Table 'streets' not found")
            return 0
            
        # 1. Count unassigned streets
        cursor.execute("SELECT COUNT(*) FROM streets WHERE team IS NULL OR team = ''")
        unassigned_count = cursor.fetchone()[0]
        
        # 2. Status distribution
        cursor.execute("""
            SELECT 
                COALESCE(status, 'Non défini') as status,
                COUNT(*) as count
            FROM streets 
            GROUP BY status 
            ORDER BY count DESC
        """)
        status_counts = cursor.fetchall()
        
        # 3. Top 10 streets (alphabetical)
        cursor.execute("""
            SELECT 
                COALESCE(sector, 'Aucun') as sector,
                name,
                COALESCE(team, 'Non assignée') as team,
                COALESCE(status, 'Non défini') as status
            FROM streets 
            ORDER BY name 
            LIMIT 10
        """)
        top_streets = cursor.fetchall()
        
        # 4. Unassigned streets by sector
        cursor.execute("""
            SELECT 
                COALESCE(sector, 'Aucun') as sector,
                name
            FROM streets 
            WHERE team IS NULL OR team = ''
            ORDER BY sector, name
        """)
        unassigned_streets = cursor.fetchall()
        
        # Display results
        print(f"📊 Rues non assignées: {unassigned_count}")
        print()
        
        print("📈 Répartition par statut:")
        for status, count in status_counts:
            print(f"  • {status}: {count}")
        print()
        
        print("📍 Top 10 rues (alphabétique):")
        for sector, name, team, status in top_streets:
            print(f"  • {sector} | {name} | {team} | {status}")
        print()
        
        # Write CSV files
        status_file = exports_dir / f"sanity_status_counts_{timestamp}.csv"
        unassigned_file = exports_dir / f"sanity_unassigned_{timestamp}.csv"
        
        # Status counts CSV
        with open(status_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['status', 'count'])
            writer.writerows(status_counts)
        
        # Unassigned streets CSV
        with open(unassigned_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['secteur', 'rue'])
            writer.writerows(unassigned_streets)
        
        print("📁 Fichiers CSV créés:")
        print(f"  • {status_file}")
        print(f"  • {unassigned_file}")
        print()
        print("✅ Sanity check terminé avec succès!")
        
        conn.close()
        return 0
        
    except sqlite3.Error as e:
        print(f"❌ Erreur base de données: {e}")
        return 0
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return 0

if __name__ == "__main__":
    sys.exit(main())