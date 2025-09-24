import sqlite3
import pandas as pd
from pathlib import Path

# Fichier à importer
excel_file = Path("import/nocivique_avec_cp.xlsx")
if not excel_file.exists():
    print("ERREUR : nocivique_avec_cp34.xlsx non trouvé!")
    exit(1)

print(f"Lecture de {excel_file}...")
df = pd.read_excel(excel_file)
print(f"✓ {len(df)} lignes lues")

# Afficher les colonnes pour debug
print(f"Colonnes disponibles : {list(df.columns)}")
print("\nÉchantillon :")
print(df.head(3))

# Connexion DB
conn = sqlite3.connect('guignomap/guigno_map.db')
cursor = conn.cursor()

# Créer les tables
conn.executescript("""
DROP TABLE IF EXISTS streets;
DROP TABLE IF EXISTS addresses;

CREATE TABLE streets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sector TEXT,
    team TEXT,
    status TEXT DEFAULT 'a_faire',
    notes TEXT
);

CREATE TABLE addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    street_name TEXT,
    house_number TEXT,
    latitude REAL,
    longitude REAL,
    postal_code TEXT
);

CREATE TABLE IF NOT EXISTS teams (
    id TEXT PRIMARY KEY,
    name TEXT,
    password_hash TEXT,
    active INTEGER DEFAULT 1
);
""")

# Extraire les rues uniques
rues = df.groupby('rue').first().reset_index() if 'rue' in df.columns else df.groupby(df.columns[0]).first().reset_index()
print(f"\n✓ {len(rues)} rues uniques trouvées")

# Importer les rues
for _, row in rues.iterrows():
    rue_name = row.iloc[0]  # Première colonne = nom de rue
    # Déterminer secteur par code postal si disponible
    sector = "Centre"  # Par défaut
    if 'code_postal' in row and pd.notna(row['code_postal']):
        cp = str(row['code_postal'])
        if cp.startswith('J7K'):
            sector = "Centre"
        elif cp.startswith('J7L'):
            sector = "Nord"
        else:
            sector = "Est"
    
    cursor.execute(
        "INSERT OR IGNORE INTO streets (name, sector, team, status) VALUES (?, ?, '', 'a_faire')",
        (rue_name, sector)
    )

# Importer les adresses
for idx, (row_idx, row) in enumerate(df.iterrows()):
    street = row.iloc[0] if pd.notna(row.iloc[0]) else ""
    number = str(row.iloc[1]) if len(row) > 1 and pd.notna(row.iloc[1]) else ""
    # Chercher lat/lon dans les colonnes
    lat = None
    lon = None
    postal = None
    for col in df.columns:
        if 'lat' in col.lower() and pd.notna(row[col]):
            lat = float(row[col])
        elif 'lon' in col.lower() and pd.notna(row[col]):
            lon = float(row[col])
        elif 'code' in col.lower() or 'postal' in col.lower():
            postal = str(row[col]) if pd.notna(row[col]) else None
    cursor.execute(
        "INSERT INTO addresses (street_name, house_number, latitude, longitude, postal_code) VALUES (?, ?, ?, ?, ?)",
        (street, number, lat, lon, postal)
    )
    if idx % 1000 == 0:
        print(f"... {idx}/{len(df)} adresses")

conn.commit()

# Vérifier l'import
streets_count = cursor.execute("SELECT COUNT(*) FROM streets").fetchone()[0]
addresses_count = cursor.execute("SELECT COUNT(*) FROM addresses").fetchone()[0]
addresses_with_gps = cursor.execute("SELECT COUNT(*) FROM addresses WHERE latitude IS NOT NULL").fetchone()[0]

print(f"\n✅ IMPORT TERMINÉ!")
print(f"   - {streets_count} rues")
print(f"   - {addresses_count} adresses")
print(f"   - {addresses_with_gps} avec GPS")

# Créer équipe admin par défaut
cursor.execute(
    "INSERT OR IGNORE INTO teams (id, name, password_hash, active) VALUES ('ADMIN', 'Administrateur', '$2b$12$YourHashHere', 1)"
)
conn.commit()
conn.close()

print("\n✓ Base de données prête!")
