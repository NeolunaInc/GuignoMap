import sqlite3

conn = sqlite3.connect("guignomap/guigno_map.db")
cursor = conn.cursor()

print("✅ VÉRIFICATION POST-RÉIMPORT\n")

# 1. Vérifier addresses
cursor.execute("""
    SELECT 
        street_name,
        house_number,
        postal_code
    FROM addresses 
    LIMIT 5
""")

print("📍 Table addresses (échantillon):")
for street, num, cp in cursor.fetchall():
    print(f"  {num} {street} [{cp or 'Pas de CP'}]")

# 2. Stats globales
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN postal_code IS NOT NULL THEN 1 ELSE 0 END) as avec_cp,
        COUNT(DISTINCT street_name) as rues_uniques
    FROM addresses
""")

stats = cursor.fetchone()
print(f"\n📊 Statistiques:")
print(f"  Total adresses: {stats[0]}")
print(f"  Avec code postal: {stats[1]} ({stats[1]*100/stats[0]:.1f}%)")
print(f"  Rues uniques: {stats[2]}")

# 3. Vérifier streets
cursor.execute("SELECT name FROM streets LIMIT 5")
print(f"\n🏘️ Table streets (échantillon):")
for street in cursor.fetchall():
    print(f"  {street[0]}")

conn.close()
