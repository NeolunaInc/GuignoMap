import sqlite3
import pandas as pd
from datetime import datetime

print("🔄 RÉIMPORT COMPLET DES DONNÉES\n")

# Lire le fichier avec codes postaux
df = pd.read_excel("import/nocivique_cp_complement.xlsx")
print(f"✓ Lu {len(df)} lignes depuis nocivique_cp_complement.xlsx")

conn = sqlite3.connect("guignomap/guigno_map.db")
cursor = conn.cursor()

# 1. BACKUP
print("\n💾 Backup des tables existantes...")
cursor.execute("DROP TABLE IF EXISTS addresses_backup")
cursor.execute("CREATE TABLE addresses_backup AS SELECT * FROM addresses")
print("✓ Backup créé")

# 2. RECRÉER LA TABLE addresses CORRECTEMENT
print("\n🔧 Recréation de la table addresses...")
cursor.execute("DROP TABLE IF EXISTS addresses")
cursor.execute("""
    CREATE TABLE addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        street_name TEXT NOT NULL,
        house_number TEXT NOT NULL,
        postal_code TEXT,
        latitude REAL,
        longitude REAL,
        osm_type TEXT DEFAULT 'official',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
cursor.execute("CREATE INDEX idx_addr_street ON addresses(street_name)")
cursor.execute("CREATE INDEX idx_addr_number ON addresses(house_number)")

# 3. IMPORTER LES ADRESSES AVEC CODES POSTAUX
print("\n📥 Import des adresses...")
imported = 0
with_cp = 0

for _, row in df.iterrows():
    street_name = str(row['nomrue']).strip() if pd.notna(row['nomrue']) else ""
    house_number = str(row['NoCiv']).strip() if pd.notna(row['NoCiv']) else ""
    
    # Code postal - utiliser code_postal_trouve en priorité
    postal_code = None
    if pd.notna(row.get('code_postal_trouve')) and row['code_postal_trouve'] not in ['NON TROUVÉ', 'ERREUR']:
        postal_code = str(row['code_postal_trouve']).strip().upper()
        with_cp += 1
    
    if street_name and house_number:
        cursor.execute("""
            INSERT INTO addresses (street_name, house_number, postal_code)
            VALUES (?, ?, ?)
        """, (street_name, house_number, postal_code))
        imported += 1
    
    if imported % 1000 == 0:
        print(f"  Progress: {imported} adresses importées...")
        conn.commit()

conn.commit()

# 4. RECRÉER LA TABLE streets AVEC LES VRAIS NOMS
print("\n🏘️ Création des rues uniques...")
cursor.execute("DROP TABLE IF EXISTS streets_backup")
cursor.execute("CREATE TABLE streets_backup AS SELECT * FROM streets")

cursor.execute("DROP TABLE IF EXISTS streets")
cursor.execute("""
    CREATE TABLE streets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        sector TEXT DEFAULT 'Centre',
        team TEXT,
        status TEXT DEFAULT 'a_faire',
        notes TEXT
    )
""")

# Insérer les rues uniques depuis addresses
cursor.execute("""
    INSERT INTO streets (name)
    SELECT DISTINCT street_name 
    FROM addresses 
    WHERE street_name IS NOT NULL AND street_name != ''
    ORDER BY street_name
""")

streets_count = cursor.rowcount

# 5. STATISTIQUES FINALES
print("\n📊 VÉRIFICATION:")
cursor.execute("SELECT COUNT(*) FROM addresses")
total_addr = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM addresses WHERE postal_code IS NOT NULL")
total_cp = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM streets")
total_streets = cursor.fetchone()[0]

print(f"✅ IMPORT TERMINÉ!")
print(f"  - Adresses importées: {total_addr}")
print(f"  - Avec code postal: {total_cp} ({total_cp*100/total_addr:.1f}%)")
print(f"  - Rues créées: {total_streets}")

# Exemples
print("\n📍 Exemples d'adresses importées:")
cursor.execute("""
    SELECT house_number, street_name, postal_code 
    FROM addresses 
    WHERE postal_code IS NOT NULL 
    LIMIT 5
""")
for num, street, cp in cursor.fetchall():
    print(f"  ✓ {num} {street} - {cp}")

conn.close()

print("\n✅ Base de données reconstruite avec succès!")
print("Prochaine étape: géocodage GPS avec les codes postaux")
