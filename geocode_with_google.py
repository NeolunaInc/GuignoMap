import pandas as pd
import sqlite3
import googlemaps
from datetime import datetime
import toml

# Lire la clé API Google depuis .streamlit/secrets.toml
secrets = toml.load('.streamlit/secrets.toml')
gmaps = googlemaps.Client(key=secrets['secrets']['GOOGLE_API_KEY'])

conn = sqlite3.connect('guignomap/guigno_map.db')
cursor = conn.execute("SELECT COUNT(*) FROM addresses WHERE latitude IS NULL")
missing = cursor.fetchone()[0]
print(f"🎯 {missing} adresses à géocoder avec Google Maps API")

cursor = conn.execute("""
    SELECT id, street_name, house_number 
    FROM addresses 
    WHERE latitude IS NULL
""")
addresses = cursor.fetchall()
success = 0
errors = 0

for addr_id, street, number in addresses:
    try:
        address = f"{number} {street}, Mascouche, QC, Canada"
        result = gmaps.geocode(address)
        if result:
            location = result[0]['geometry']['location']
            lat = location['lat']
            lng = location['lng']
            conn.execute(
                "UPDATE addresses SET latitude=?, longitude=? WHERE id=?",
                (lat, lng, addr_id)
            )
            success += 1
            if success % 100 == 0:
                conn.commit()
                print(f"✅ {success} adresses géocodées...")
        else:
            errors += 1
    except Exception as e:
        print(f"❌ Erreur: {e}")
        errors += 1

conn.commit()
print(f"\n🎉 TERMINÉ!")
print(f"✅ Succès: {success}")
print(f"❌ Échecs: {errors}")
print(f"📍 Total avec GPS: {success}/{missing}")
conn.close()
