import sqlite3
import pandas as pd

print("📊 IMPORT DIRECT DES CODES POSTAUX\n")

# Lire le fichier avec les codes postaux
df = pd.read_excel("import/nocivique_cp_complement.xlsx")
df_valid = df[
    df['code_postal_trouve'].notna() & \
    (df['code_postal_trouve'] != 'NON TROUVÉ') & \
    (df['code_postal_trouve'] != 'ERREUR')
]

print(f"✓ {len(df_valid)} codes postaux valides à importer")

conn = sqlite3.connect("guignomap/guigno_map.db")
cursor = conn.cursor()

# Stats avant
cursor.execute("SELECT COUNT(*) FROM addresses WHERE postal_code IS NOT NULL")
before = cursor.fetchone()[0]
print(f"Avant: {before} adresses avec CP")

# Import avec UPDATE sur correspondance exacte
updated = 0
not_found = []

print("\n🔄 Matching et import...")
for _, row in df_valid.iterrows():
    street_name = str(row['nomrue']).strip()
    house_number = str(row['NoCiv']).strip()
    postal_code = str(row['code_postal_trouve']).strip().upper()
    
    # UPDATE direct avec correspondance exacte
    cursor.execute("""
        UPDATE addresses 
        SET postal_code = ?
        WHERE street_name = ? 
        AND house_number = ?
        AND (postal_code IS NULL OR postal_code = '')
    """, (postal_code, street_name, house_number))
    
    if cursor.rowcount > 0:
        updated += cursor.rowcount
    else:
        not_found.append(f"{house_number} {street_name}")
    
    if updated > 0 and updated % 500 == 0:
        print(f"  {updated} codes postaux importés...")
        conn.commit()

conn.commit()

# Stats finales
cursor.execute("SELECT COUNT(*) FROM addresses WHERE postal_code IS NOT NULL")
after = cursor.fetchone()[0]

print(f"\n✅ RÉSULTATS:")
print(f"  - Codes postaux ajoutés: {updated}")
print(f"  - Total avec CP: {after} (avant: {before})")
print(f"  - Taux de couverture: {after*100/18655:.1f}%")

if not_found[:10]:
    print(f"\n⚠️ Exemples non trouvés:")
    for addr in not_found[:10]:
        print(f"  - {addr}")

# Vérifier quelques succès
if updated > 0:
    cursor.execute("""
        SELECT house_number, street_name, postal_code 
        FROM addresses 
        WHERE postal_code IS NOT NULL 
        ORDER BY RANDOM() 
        LIMIT 5
    """)
    print(f"\n✅ Exemples importés:")
    for num, street, cp in cursor.fetchall():
        print(f"  {num} {street} - {cp}")

conn.close()
