import sqlite3
import pandas as pd

# Comparer les formats
df_excel = pd.read_excel("import/nocivique_cp_complement.xlsx")
conn = sqlite3.connect("guignomap/guigno_map.db")

print("🔍 ANALYSE DES DIFFÉRENCES DE FORMAT\n")

# Prendre 5 exemples de chaque
print("EXCEL (nocivique_cp_complement.xlsx):")
for _, row in df_excel.head(5).iterrows():
    print(f"  [{row['NoCiv']}] [{row['nomrue']}] CP:{row.get('code_postal_trouve', 'N/A')}")

print("\nBASE DE DONNÉES (addresses):")
cursor = conn.cursor()
cursor.execute("SELECT house_number, street_name FROM addresses LIMIT 5")
for num, street in cursor.fetchall():
    print(f"  [{num}] [{street}]")

# Tester un matching exact
test_num = str(df_excel.iloc[0]['NoCiv']).strip()
test_street = str(df_excel.iloc[0]['nomrue']).strip()

print(f"\n🔬 TEST DE MATCHING:")
print(f"Recherche: [{test_num}] [{test_street}]")

cursor.execute("""
    SELECT COUNT(*) 
    FROM addresses 
    WHERE house_number = ? AND street_name = ?
""", (test_num, test_street))
exact = cursor.fetchone()[0]
print(f"  Correspondance exacte: {exact}")

# Vérifier les types
cursor.execute("""
    SELECT 
        typeof(house_number) as type_num,
        typeof(street_name) as type_street,
        length(house_number) as len_num,
        length(street_name) as len_street
    FROM addresses 
    LIMIT 1
""")
types = cursor.fetchone()
print(f"\n📏 TYPES ET LONGUEURS DB:")
print(f"  house_number: type={types[0]}, length={types[2]}")
print(f"  street_name: type={types[1]}, length={types[3]}")

conn.close()
