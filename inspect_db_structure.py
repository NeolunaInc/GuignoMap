import sqlite3
import pandas as pd

conn = sqlite3.connect("guignomap/guigno_map.db")

# 1. Structure de la table addresses
print("📊 STRUCTURE DE LA TABLE addresses:")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(addresses)")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

# 2. Échantillon des données
print("\n📋 ÉCHANTILLON DES DONNÉES (10 premières lignes):")
df = pd.read_sql_query("SELECT * FROM addresses LIMIT 10", conn)
print(df)

# 3. Vérifier si les noms de rues sont ailleurs
print("\n🔍 ANALYSE DES VALEURS:")
cursor.execute("SELECT street_name, house_number, COUNT(*) as nb FROM addresses GROUP BY street_name, house_number LIMIT 10")
for row in cursor.fetchall():
    print(f"  street_name=[{row[0]}], house_number=[{row[1]}], count={row[2]}")

# 4. Vérifier la table streets
print("\n📊 TABLE streets:")
cursor.execute("SELECT name FROM streets LIMIT 10")
streets = cursor.fetchall()
for street in streets:
    print(f"  {street[0]}")

conn.close()
