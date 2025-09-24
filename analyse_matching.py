import sqlite3
import pandas as pd

# 1. Lire les données Excel
df_excel = pd.read_excel("import/nocivique_cp_complement.xlsx")
print("📊 DONNÉES EXCEL:")
print(f"Total: {len(df_excel)} lignes")
print("\nPremiers 5 exemples Excel:")
for _, row in df_excel.head(5).iterrows():
    print(f"  [{row['NoCiv']}] [{row['nomrue']}]")

# 2. Lire les données DB
conn = sqlite3.connect("guignomap/guigno_map.db")

# Échantillon de la DB
cursor = conn.cursor()
cursor.execute("""
    SELECT DISTINCT street_name, house_number 
    FROM addresses 
    WHERE postal_code IS NULL
    ORDER BY street_name, CAST(house_number AS INTEGER)
    LIMIT 10
""")

print("\n📊 DONNÉES BASE DE DONNÉES:")
print("Premiers 10 exemples DB:")
for street, num in cursor.fetchall():
    print(f"  [{num}] [{street}]")

# 3. Analyser les formats de noms de rues
print("\n🔍 ANALYSE DES FORMATS:")

# Noms de rues uniques dans Excel
excel_streets = df_excel['nomrue'].unique()
print(f"Rues uniques Excel: {len(excel_streets)}")
print("Exemples Excel:", list(excel_streets[:5]))

# Noms de rues uniques dans DB
cursor.execute("SELECT DISTINCT street_name FROM addresses")
db_streets = [row[0] for row in cursor.fetchall()]
print(f"\nRues uniques DB: {len(db_streets)}")
print("Exemples DB:", db_streets[:5])

# 4. Chercher des correspondances potentielles
print("\n🔄 TEST DE CORRESPONDANCE:")
test_street = str(excel_streets[0])
print(f"Recherche de '{test_street}' dans la DB...")

# Recherche exacte
cursor.execute("SELECT COUNT(*) FROM addresses WHERE street_name = ?", (test_street,))
exact = cursor.fetchone()[0]
print(f"  Correspondance exacte: {exact}")

# Recherche avec LIKE
cursor.execute("SELECT COUNT(*) FROM addresses WHERE street_name LIKE ?", (f"%{test_street.split()[-1]}%",))
partial = cursor.fetchone()[0]
print(f"  Correspondance partielle (contient '{test_street.split()[-1]}'): {partial}")

# 5. Analyser les différences de format
print("\n⚠️ DIFFÉRENCES POSSIBLES:")
print("  - Majuscules/minuscules")
print("  - Espaces en trop")
print("  - Accents différents")
print("  - Préfixes (Rue, Avenue, etc.)")

conn.close()
