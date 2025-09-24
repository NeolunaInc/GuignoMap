import sqlite3
import pandas as pd
from datetime import datetime

print("🔧 CORRECTION DÉFINITIVE DE LA STRUCTURE\n")

conn = sqlite3.connect("guignomap/guigno_map.db")
cursor = conn.cursor()

# 1. BACKUP
print("💾 Backup de sécurité...")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
cursor.execute(f"DROP TABLE IF EXISTS addresses_backup_{timestamp}")
cursor.execute(f"CREATE TABLE addresses_backup_{timestamp} AS SELECT * FROM addresses")
print(f"✓ Backup créé: addresses_backup_{timestamp}")

# 2. CRÉER UNE NOUVELLE TABLE AVEC LA BONNE STRUCTURE
print("\n📋 Création de la nouvelle structure...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS addresses_new (
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

# 3. IMPORTER DEPUIS LE FICHIER EXCEL AVEC LA BONNE STRUCTURE
print("\n📥 Import des données depuis nocivique_cp_complement.xlsx...")
df = pd.read_excel("import/nocivique_cp_complement.xlsx")

imported = 0
with_cp = 0

for _, row in df.iterrows():
    # Récupérer les valeurs correctement
    house_num = str(row['NoCiv']).strip() if pd.notna(row['NoCiv']) else ""
    street_name = str(row['nomrue']).strip() if pd.notna(row['nomrue']) else ""
    
    # Code postal
    cp = None
    if pd.notna(row.get('code_postal_trouve')) and \
       str(row['code_postal_trouve']) not in ['NON TROUVÉ', 'ERREUR', 'nan']:
        cp = str(row['code_postal_trouve']).strip().upper()
        with_cp += 1
    
    if house_num and street_name:
        cursor.execute("""
            INSERT INTO addresses_new (house_number, street_name, postal_code)
            VALUES (?, ?, ?)
        """, (house_num, street_name, cp))
        imported += 1
    
    if imported % 1000 == 0:
        print(f"  {imported} adresses importées...")
        conn.commit()

conn.commit()
print(f"✓ {imported} adresses importées, {with_cp} avec code postal")

# 4. REMPLACER L'ANCIENNE TABLE
print("\n🔄 Remplacement de la table...")
cursor.execute("DROP TABLE IF EXISTS addresses_old")
cursor.execute("ALTER TABLE addresses RENAME TO addresses_old")
cursor.execute("ALTER TABLE addresses_new RENAME TO addresses")

# 5. CRÉER LES INDEX
cursor.execute("CREATE INDEX IF NOT EXISTS idx_addr_street ON addresses(street_name)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_addr_number ON addresses(house_number)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_addr_postal ON addresses(postal_code)")

# 6. METTRE À JOUR LA TABLE STREETS
print("\n🏘️ Mise à jour des rues...")
cursor.execute("DELETE FROM streets")
cursor.execute("""
    INSERT INTO streets (name, status)
    SELECT DISTINCT street_name, 'a_faire'
    FROM addresses
    WHERE street_name IS NOT NULL
    ORDER BY street_name
""")
streets_count = cursor.rowcount

# 7. VÉRIFICATION FINALE
print("\n✅ VÉRIFICATION FINALE:")

cursor.execute("SELECT COUNT(*) FROM addresses")
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM addresses WHERE postal_code IS NOT NULL")
with_cp_final = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(DISTINCT street_name) FROM addresses")
unique_streets = cursor.fetchone()[0]

print(f"  Total adresses: {total}")
print(f"  Avec code postal: {with_cp_final} ({with_cp_final*100/total:.1f}%)")
print(f"  Rues uniques: {unique_streets}")

# Exemples
print("\n📍 Exemples de données corrigées:")
cursor.execute("""
    SELECT house_number, street_name, postal_code
    FROM addresses
    WHERE postal_code IS NOT NULL
    ORDER BY RANDOM()
    LIMIT 5
""")
for num, street, cp in cursor.fetchall():
    print(f"  ✓ {num} {street} - {cp}")

print("\n🎉 BASE DE DONNÉES CORRIGÉE AVEC SUCCÈS!")
print(f"   {with_cp_final} adresses ont maintenant un code postal")
print("   Prochaine étape: géocodage GPS")

conn.close()
