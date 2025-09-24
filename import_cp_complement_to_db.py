import sqlite3
import csv

# Chemins
CSV_PATH = "import/nocivique_cp_complement.csv"
DB_PATH = "guignomap/guigno_map.db"

# Connexion à la base
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Lecture du CSV en UTF-8
with open(CSV_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Adapter les noms de colonnes selon le CSV
        num = row.get("house_number") or row.get("numero")
        street = row.get("street_name") or row.get("rue")
        cp = row.get("postal_code") or row.get("code_postal")
        # Optionnel: autres champs
        # id = row.get("id")
        if num and street and cp:
            # Vérifier si l'adresse existe déjà
            cursor.execute("""
                SELECT id FROM addresses WHERE house_number=? AND street_name=?
            """, (num, street))
            result = cursor.fetchone()
            if result:
                # Mise à jour du code postal
                cursor.execute("""
                    UPDATE addresses SET postal_code=? WHERE id=?
                """, (cp, result[0]))
            else:
                # Insertion nouvelle adresse
                cursor.execute("""
                    INSERT INTO addresses (house_number, street_name, postal_code) VALUES (?, ?, ?)
                """, (num, street, cp))

conn.commit()
conn.close()
print("Import terminé : nocivique_cp_complement.csv → guigno_map.db")
