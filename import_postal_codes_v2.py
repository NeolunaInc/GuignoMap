import sqlite3
import pandas as pd
from pathlib import Path

# Lire le fichier Excel
print("📖 Lecture du fichier Excel...")
df = pd.read_excel("import/nocivique_cp_complement.xlsx")
print(f"✓ {len(df)} lignes lues")

# Filtrer seulement les codes postaux valides
df_valid = df[
    df['code_postal_trouve'].notna() & \
    (df['code_postal_trouve'] != 'NON TROUVÉ') & \
    (df['code_postal_trouve'] != 'ERREUR')
].copy()

print(f"✓ {len(df_valid)} codes postaux valides à importer")

# Connexion DB
conn = sqlite3.connect("guignomap/guigno_map.db")
cursor = conn.cursor()

# Stats avant
cursor.execute("SELECT COUNT(*) FROM addresses WHERE postal_code IS NOT NULL AND postal_code != ''")
before = cursor.fetchone()[0]
print(f"\n📊 Avant import: {before} adresses avec code postal dans la DB")

# Import par batch pour performance
updated = 0
not_matched = []

print("\n🔄 Import en cours...")
for idx, row in enumerate(df_valid.itertuples(index=False), 1):
    street_name = str(row.nomrue).strip()
    house_number = str(row.NoCiv).strip()
    postal_code = str(row.code_postal_trouve).strip().upper()
    
    # Update avec correspondance exacte
    cursor.execute("""
        UPDATE addresses 
        SET postal_code = ?
        WHERE TRIM(street_name) = ? 
        AND TRIM(house_number) = ?
        AND (postal_code IS NULL OR postal_code = '')
    """, (postal_code, street_name, house_number))
    
    if cursor.rowcount > 0:
        updated += 1
    else:
        not_matched.append(f"{house_number} {street_name}")
    
    # Progress et commit périodique
    if idx % 500 == 0:
        conn.commit()
        print(f"  Progress: {updated}/{idx} importés...")

# Commit final
conn.commit()

# Stats après
cursor.execute("SELECT COUNT(*) FROM addresses WHERE postal_code IS NOT NULL AND postal_code != ''")
after = cursor.fetchone()[0]

print(f"\n✅ IMPORT TERMINÉ!")
print(f"  - Codes postaux importés: {updated}")
print(f"  - Non matchés: {len(not_matched)}")
print(f"  - Total avec CP dans DB: {after} (avant: {before})")
print(f"  - Nouveaux codes postaux ajoutés: {after - before}")

# Afficher quelques exemples de succès
cursor.execute("""
    SELECT street_name, house_number, postal_code
    FROM addresses
    WHERE postal_code IS NOT NULL
    ORDER BY RANDOM()
    LIMIT 5
""")

print("\n📍 Exemples d'adresses avec CP importé:")
for street, num, cp in cursor.fetchall():
    print(f"  ✓ {num} {street}: {cp}")

# Sauvegarder les non-matchés pour debug
if not_matched:
    with open("non_matched_addresses.txt", "w", encoding="utf-8") as f:
        f.write(f"Adresses non matchées ({len(not_matched)}):\n")
        for addr in not_matched[:50]:  # Premiers 50 seulement
            f.write(f"{addr}\n")
    print(f"\n⚠️ {len(not_matched)} adresses non matchées sauvées dans non_matched_addresses.txt")

conn.close()
