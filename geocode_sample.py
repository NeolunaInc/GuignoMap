import sqlite3
from geopy.geocoders import Nominatim
import time

conn = sqlite3.connect('guignomap/guigno_map.db')
geolocator = Nominatim(user_agent="guignomap_mascouche_v2")

# Géocoder seulement 50 adresses pour tester rapidement
cursor = conn.execute("""
    SELECT id, street_name, house_number 
    FROM addresses 
    WHERE latitude IS NULL 
    LIMIT 50
""")

addresses = cursor.fetchall()
print(f"Géocodage de {len(addresses)} adresses pour test...")

for addr_id, street, number in addresses:
    query = f"{number} {street}, Mascouche, Quebec, Canada"
    try:
        location = geolocator.geocode(query)
        if location:
            conn.execute(
                "UPDATE addresses SET latitude=?, longitude=? WHERE id=?",
                (location.latitude, location.longitude, addr_id)
            )
            print(f"✓ {query}: {location.latitude:.4f}, {location.longitude:.4f}")
        else:
            print(f"✗ Non trouvé: {query}")
        time.sleep(1.2)
    except Exception as e:
        print(f"Erreur: {e}")

conn.commit()

# Vérifier
with_gps = conn.execute("SELECT COUNT(*) FROM addresses WHERE latitude IS NOT NULL").fetchone()[0]
print(f"\nTotal avec GPS: {with_gps}/18655")
conn.close()
