import sqlite3
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import logging

# Configurer le log
logging.basicConfig(filename="geocoding.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

print("🌍 GÉOCODAGE AVEC CODES POSTAUX\n")

conn = sqlite3.connect("guignomap/guigno_map.db")
cursor = conn.cursor()
geolocator = Nominatim(user_agent="guignomap_mascouche_v4")

# 1. Sélectionner les adresses à géocoder
cursor.execute("""
    SELECT id, street_name, house_number, postal_code 
    FROM addresses 
    WHERE postal_code IS NOT NULL 
      AND postal_code NOT IN ('NON TROUVÉ', 'ERREUR')
      AND latitude IS NULL
    LIMIT 200
""")
adresses = cursor.fetchall()

total = len(adresses)
print(f"À géocoder: {total} adresses")

success = 0
fail = 0
for idx, (addr_id, street, num, cp) in enumerate(adresses, 1):
    query = f"{num} {street}, {cp}, Canada"
    try:
        location = geolocator.geocode(query)
        if location is not None:
            cursor.execute("""
                UPDATE addresses SET latitude = ?, longitude = ? WHERE id = ?
            """, (location.latitude, location.longitude, addr_id))
            success += 1
            logging.info(f"OK: {query} -> {location.latitude}, {location.longitude}")
        else:
            fail += 1
            logging.warning(f"NOT FOUND: {query}")
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        fail += 1
        logging.error(f"ERROR: {query} -> {e}")
    except Exception as e:
        fail += 1
        logging.error(f"UNEXPECTED: {query} -> {e}")
    if idx % 25 == 0:
        conn.commit()
        print(f"  Progress: {idx}/{total} géocodés...")
    time.sleep(1.1)

conn.commit()
print(f"\n✅ GÉOCODAGE TERMINÉ!")
print(f"  Succès: {success}")
print(f"  Échecs: {fail}")
print(f"  Log: geocoding.log")

conn.close()
