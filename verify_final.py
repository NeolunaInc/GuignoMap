import sqlite3

conn = sqlite3.connect("guignomap/guigno_map.db")
cursor = conn.cursor()

print("✅ VÉRIFICATION FINALE DE LA STRUCTURE\n")

# 1. Structure
cursor.execute("PRAGMA table_info(addresses)")
print("📋 Structure de addresses:")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

# 2. Échantillon
print("\n📍 Échantillon (10 premières avec CP):")
cursor.execute("""
    SELECT house_number, street_name, postal_code
    FROM addresses
    WHERE postal_code IS NOT NULL
    LIMIT 10
""")
for num, street, cp in cursor.fetchall():
    print(f"  {num} {street} - {cp}")

# 3. Statistiques par code postal
print("\n📊 Distribution par code postal:")
cursor.execute("""
    SELECT postal_code, COUNT(*) as nb
    FROM addresses
    WHERE postal_code IS NOT NULL
    GROUP BY postal_code
    ORDER BY nb DESC
    LIMIT 5
""")
for cp, count in cursor.fetchall():
    print(f"  {cp}: {count} adresses")

# 4. Stats globales
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN postal_code IS NOT NULL THEN 1 ELSE 0 END) as avec_cp,
        SUM(CASE WHEN latitude IS NOT NULL THEN 1 ELSE 0 END) as avec_gps
    FROM addresses
""")
stats = cursor.fetchone()

print(f"\n📈 STATISTIQUES GLOBALES:")
print(f"  Total: {stats[0]} adresses")
print(f"  Avec CP: {stats[1]} ({stats[1]*100/stats[0]:.1f}%)")
print(f"  Avec GPS: {stats[2]} ({stats[2]*100/stats[0]:.1f}%)")
print(f"  Prêtes pour géocodage: {stats[1] - stats[2]}")

conn.close()
