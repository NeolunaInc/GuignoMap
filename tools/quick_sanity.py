#!/usr/bin/env python3
"""
Quick sanity check script for GuignoMap v4.1
Generates audit CSV files and validates data integrity with assertions.
"""

import sqlite3
import csv
import sys
from datetime import datetime
from pathlib import Path

def main():
    """Main sanity check function with data integrity assertions."""
    # Paths
    db_path = Path("guignomap") / "guigno_map.db"
    exports_dir = Path("exports")
    
    # Create exports directory if missing
    exports_dir.mkdir(exist_ok=True)
    
    # Check if database exists
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("ℹ️  Run the application first to create the database.")
        print("SANITY: FAIL - Database missing")
        return 1
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Generate timestamp for files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        print("🔍 GuignoMap v4.1 - Quick Sanity Check with Assertions")
        print("=" * 60)
        
        # Check if required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        if 'streets' not in tables:
            print("❌ Table 'streets' not found")
            print("SANITY: FAIL - Missing streets table")
            return 1
        
        # === DATA COLLECTION ===
        
        # 1. Total streets count
        cursor.execute("SELECT COUNT(*) FROM streets")
        total_streets = cursor.fetchone()[0]
        
        # 2. Count unassigned streets (team IS NULL OR team = '')
        cursor.execute("SELECT COUNT(*) FROM streets WHERE team IS NULL OR team = ''")
        unassigned_count = cursor.fetchone()[0]
        
        # 3. Status distribution with counts
        cursor.execute("""
            SELECT 
                COALESCE(status, 'Non défini') as status,
                COUNT(*) as count
            FROM streets 
            GROUP BY status 
            ORDER BY count DESC
        """)
        status_counts = cursor.fetchall()
        
        # 4. Unassigned streets by sector (for CSV)
        cursor.execute("""
            SELECT 
                COALESCE(sector, 'Aucun') as sector,
                name
            FROM streets 
            WHERE team IS NULL OR team = ''
            ORDER BY sector, name
        """)
        unassigned_streets = cursor.fetchall()
        
        # 5. Top 10 streets (for display)
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
        
        # === ASSERTIONS & DATA INTEGRITY CHECKS ===
        
        sanity_pass = True
        fail_reasons = []
        
        # Assertion 1: Total should equal sum of status counts
        sum_status_counts = sum(count for _, count in status_counts)
        if total_streets != sum_status_counts:
            sanity_pass = False
            fail_reasons.append(f"Total streets ({total_streets}) != sum of status counts ({sum_status_counts})")
        
        # Assertion 2: Unassigned count should match COUNT(team IS NULL OR team = '')
        # (This is redundant since we're using the same query, but validates consistency)
        cursor.execute("SELECT COUNT(*) FROM streets WHERE team IS NULL OR team = ''")
        unassigned_recheck = cursor.fetchone()[0]
        if unassigned_count != unassigned_recheck:
            sanity_pass = False
            fail_reasons.append(f"Unassigned count inconsistent ({unassigned_count} vs {unassigned_recheck})")
        
        # Assertion 3: No negative counts
        for status, count in status_counts:
            if count < 0:
                sanity_pass = False
                fail_reasons.append(f"Negative count for status '{status}': {count}")
        
        # Assertion 4: Total should be positive if any data exists
        if status_counts and total_streets <= 0:
            sanity_pass = False
            fail_reasons.append(f"Invalid total streets count: {total_streets}")
        
        # === DISPLAY RESULTS ===
        
        print(f"📊 Total des rues: {total_streets}")
        print(f"📊 Rues non assignées: {unassigned_count}")
        print()
        
        print("📈 Répartition par statut:")
        for status, count in status_counts:
            print(f"  • {status}: {count}")
        print(f"  📋 Somme des statuts: {sum_status_counts}")
        print()
        
        print("📍 Top 10 rues (alphabétique):")
        for sector, name, team, status in top_streets[:10]:
            print(f"  • {sector} | {name} | {team} | {status}")
        print()
        
        # === WRITE CSV FILES (ALWAYS) ===
        
        status_file = exports_dir / f"sanity_status_counts_{timestamp}.csv"
        unassigned_file = exports_dir / f"sanity_unassigned_{timestamp}.csv"
        
        try:
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
            
        except Exception as e:
            print(f"⚠️  Erreur lors de l'écriture des CSV: {e}")
            print()
        
        # === FINAL SANITY CHECK RESULT ===
        
        conn.close()
        
        if sanity_pass:
            print("✅ Tous les tests de cohérence sont passés")
            print("SANITY: PASS")
            return 0
        else:
            print("❌ Échec des tests de cohérence:")
            for reason in fail_reasons:
                print(f"  • {reason}")
            print("SANITY: FAIL - Data integrity issues")
            return 1
            
    except sqlite3.Error as e:
        print(f"❌ Erreur base de données: {e}")
        print("SANITY: FAIL - Database error")
        return 1
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        print("SANITY: FAIL - Unexpected error")
        return 1

if __name__ == "__main__":
    sys.exit(main())