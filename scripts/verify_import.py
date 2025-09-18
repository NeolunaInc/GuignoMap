# scripts/verify_import.py
import sqlite3
from pathlib import Path

DB_PATH = Path("guignomap/guigno_map.db")

def verify_import():
    with sqlite3.connect(DB_PATH) as conn:
        print("=== Schéma final de la table addresses ===")
        for row in conn.execute("PRAGMA table_info(addresses)").fetchall():
            print(f"{row[1]}: {row[2]}")
        
        print(f"\n=== Nombre total d'adresses ===")
        total = conn.execute("SELECT COUNT(*) FROM addresses").fetchone()[0]
        print(f"Total: {total}")
        
        print(f"\n=== Échantillon des données importées ===")
        for row in conn.execute("SELECT street_name, house_number, postal_code, sector FROM addresses LIMIT 5").fetchall():
            print(f"{row[0]} {row[1]} (postal: {row[2]}, sector: {row[3]})")
        
        print(f"\n=== Répartition par secteur ===")
        for row in conn.execute("SELECT sector, COUNT(*) FROM addresses GROUP BY sector ORDER BY COUNT(*) DESC LIMIT 10").fetchall():
            print(f"Secteur '{row[0]}': {row[1]} adresses")

if __name__ == "__main__":
    verify_import()