import sqlite3

c = sqlite3.connect('guignomap/guigno_map.db')
print('Échantillon aléatoire d\'adresses:')
for row in c.execute("SELECT street_name, house_number, postal_code, sector, latitude, longitude FROM addresses ORDER BY RANDOM() LIMIT 5").fetchall():
    geo = f"({row[4]}, {row[5]})" if row[4] and row[5] else "Non géocodé"
    print(f"  {row[0]} {row[1]} | Postal: {row[2] or 'N/A'} | Secteur: {row[3] or 'N/A'} | Geo: {geo}")
c.close()