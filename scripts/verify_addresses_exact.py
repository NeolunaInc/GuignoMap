# scripts/verify_addresses_exact.py
import pandas as pd
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("guignomap/guigno_map.db")
EXCEL_PATH = Path("imports/mascouche_adresses.xlsx")

def count_valid_excel_lines():
    """Compte les lignes valides dans le fichier Excel"""
    if not EXCEL_PATH.exists():
        print(f"❌ Fichier Excel introuvable: {EXCEL_PATH}")
        return 0
    
    print(f"📖 Lecture du fichier Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)
    
    # Filtrer les lignes valides (au minimum NoCiv et nomrue non vides)
    valid_df = df.dropna(subset=['NoCiv', 'nomrue'])
    valid_df = valid_df[
        (valid_df['NoCiv'].astype(str).str.strip() != '') & 
        (valid_df['nomrue'].astype(str).str.strip() != '')
    ]
    
    total_lines = len(df)
    valid_lines = len(valid_df)
    invalid_lines = total_lines - valid_lines
    
    print(f"📊 Total lignes Excel: {total_lines}")
    print(f"📊 Lignes valides: {valid_lines}")
    if invalid_lines > 0:
        print(f"⚠️ Lignes invalides (NoCiv ou nomrue vide): {invalid_lines}")
    
    return valid_lines

def count_db_addresses():
    """Compte les adresses dans la base de données"""
    if not DB_PATH.exists():
        print(f"❌ Base de données introuvable: {DB_PATH}")
        return 0
    
    with sqlite3.connect(DB_PATH) as conn:
        # Vérifier que la table addresses existe
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "addresses" not in tables:
            print("❌ Table 'addresses' introuvable dans la base")
            return 0
        
        # Compter les adresses
        count = conn.execute("SELECT COUNT(*) FROM addresses").fetchone()[0]
        print(f"📊 Adresses en base: {count}")
        
        return count

def check_duplicates():
    """Vérifie s'il y a des doublons dans la table addresses"""
    duplicates = []
    
    with sqlite3.connect(DB_PATH) as conn:
        # Vérifier les doublons par addr_key
        cursor = conn.execute("""
            SELECT addr_key, COUNT(*) as count
            FROM addresses 
            GROUP BY addr_key 
            HAVING COUNT(*) > 1
            ORDER BY count DESC, addr_key
        """)
        
        for row in cursor.fetchall():
            addr_key, count = row
            duplicates.append((addr_key, count))
        
        if duplicates:
            print(f"❌ {len(duplicates)} clé(s) d'adresse en doublon détectée(s):")
            for addr_key, count in duplicates[:10]:  # Montrer max 10 exemples
                print(f"  - '{addr_key}': {count} occurrences")
            if len(duplicates) > 10:
                print(f"  ... et {len(duplicates) - 10} autre(s)")
        else:
            print("✅ Aucun doublon détecté (addr_key unique)")
    
    return duplicates

def check_data_integrity():
    """Vérifie l'intégrité des données"""
    issues = []
    
    with sqlite3.connect(DB_PATH) as conn:
        # Vérifier les adresses avec street_name ou house_number vide
        empty_street = conn.execute("SELECT COUNT(*) FROM addresses WHERE street_name IS NULL OR TRIM(street_name) = ''").fetchone()[0]
        empty_house = conn.execute("SELECT COUNT(*) FROM addresses WHERE house_number IS NULL OR TRIM(house_number) = ''").fetchone()[0]
        
        if empty_street > 0:
            issues.append(f"❌ {empty_street} adresse(s) avec street_name vide")
        
        if empty_house > 0:
            issues.append(f"❌ {empty_house} adresse(s) avec house_number vide")
        
        # Vérifier les addr_key vides
        empty_key = conn.execute("SELECT COUNT(*) FROM addresses WHERE addr_key IS NULL OR TRIM(addr_key) = ''").fetchone()[0]
        if empty_key > 0:
            issues.append(f"❌ {empty_key} adresse(s) avec addr_key vide")
        
        # Statistiques des assignements
        assigned = conn.execute("SELECT COUNT(*) FROM addresses WHERE assigned_to IS NOT NULL AND TRIM(assigned_to) <> ''").fetchone()[0]
        unassigned = conn.execute("SELECT COUNT(*) FROM addresses WHERE assigned_to IS NULL OR TRIM(assigned_to) = ''").fetchone()[0]
        
        print(f"📊 Adresses assignées: {assigned}")
        print(f"📊 Adresses non assignées: {unassigned}")
        
        if issues:
            for issue in issues:
                print(issue)
        else:
            print("✅ Intégrité des données OK")
    
    return issues

def verify_addresses_exact():
    """Vérification complète post-import"""
    print("=== Vérification Post-Import ===")
    
    exit_code = 0
    
    # 1. Compter les lignes Excel valides
    n_excel = count_valid_excel_lines()
    
    # 2. Compter les adresses en base
    n_db = count_db_addresses()
    
    # 3. Vérifier les doublons
    duplicates = check_duplicates()
    
    # 4. Vérifier l'intégrité
    integrity_issues = check_data_integrity()
    
    print("\n=== RÉSUMÉ FINAL ===")
    
    # Comparaison Excel vs DB
    if n_excel == 0 and n_db == 0:
        print("⚠️ Aucune donnée trouvée (Excel et DB vides)")
        exit_code = 1
    elif n_excel == 0:
        print("⚠️ Fichier Excel vide mais DB contient des données")
        exit_code = 1
    elif n_db == 0:
        print("❌ DB vide mais Excel contient des données")
        exit_code = 1
    else:
        diff = abs(n_excel - n_db)
        if diff == 0:
            print(f"✅ Correspondance parfaite: {n_excel} lignes Excel = {n_db} adresses DB")
        else:
            print(f"❌ Écart détecté: {n_excel} lignes Excel ≠ {n_db} adresses DB (diff: {diff})")
            exit_code = 1
    
    # Vérification doublons
    if duplicates:
        print(f"❌ {len(duplicates)} doublon(s) détecté(s)")
        exit_code = 1
    else:
        print("✅ Aucun doublon")
    
    # Vérification intégrité
    if integrity_issues:
        print(f"❌ {len(integrity_issues)} problème(s) d'intégrité")
        exit_code = 1
    else:
        print("✅ Intégrité OK")
    
    # Résultat final
    if exit_code == 0:
        print("\n🎉 VÉRIFICATION RÉUSSIE - Toutes les données sont cohérentes")
    else:
        print("\n💥 VÉRIFICATION ÉCHOUÉE - Des problèmes ont été détectés")
    
    return exit_code

if __name__ == "__main__":
    exit_code = verify_addresses_exact()
    sys.exit(exit_code)