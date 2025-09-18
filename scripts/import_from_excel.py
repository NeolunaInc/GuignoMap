# scripts/import_from_excel.py
import pandas as pd
import sqlite3
import unicodedata
import re
from pathlib import Path

DB_PATH = Path("guignomap/guigno_map.db")
EXCEL_PATH = Path("imports/mascouche_adresses.xlsx")

def _is_null(x):
    """Vérifie si une valeur est nulle, NaN, 'nan' (insensible à la casse) ou chaîne vide"""
    if x is None:
        return True
    if pd.isna(x):
        return True
    
    # Convertir en string et strip
    str_x = str(x).strip()
    
    # Vérifier si c'est une chaîne vide ou "nan" (insensible à la casse)
    if str_x == "" or str_x.lower() == "nan":
        return True
    
    return False

def _build_street(nomrue, odoparti, odospeci):
    """Construit le nom de rue en privilégiant nomrue, sinon en joignant odoparti + odospeci"""
    # Si nomrue est fiable, l'utiliser directement
    if not _is_null(nomrue):
        return str(nomrue).strip()
    
    # Sinon, joindre proprement odoparti et odospeci en ignorant les valeurs nulles
    parts = []
    
    if not _is_null(odoparti):
        parts.append(str(odoparti).strip())
    
    if not _is_null(odospeci):
        parts.append(str(odospeci).strip())
    
    # Joindre avec un seul espace (pas d'espaces doubles)
    return " ".join(parts) if parts else ""

def _normalize_text(s):
    """Normalise un texte pour créer une clé d'adresse unique - NE JAMAIS retourner 'nan'"""
    if _is_null(s):
        return ""
    
    # Convertir en string et strip
    text = str(s).strip()
    
    # Vérifier encore une fois "nan" après conversion string
    if text.lower() == "nan":
        return ""
    
    # Enlever les accents (NFD normalization puis supprimer les diacritiques)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    
    # Remplacer apostrophes typographiques par simples
    text = text.replace("'", "'").replace("'", "'")
    
    # Minuscules
    text = text.lower()
    
    # Compresser les espaces multiples
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def read_and_prepare_excel():
    """Lit le fichier Excel et prépare les données avec addr_key"""
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Fichier Excel introuvable: {EXCEL_PATH}")

    print(f"📖 Lecture du fichier Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)
    print(f"📊 {len(df)} lignes lues depuis Excel")
    
    # Afficher les colonnes disponibles
    print(f"📋 Colonnes disponibles: {sorted(df.columns.tolist())}")
    
    # Vérifier les colonnes requises pour le schéma Mascouche réel
    required_cols = {"NoCiv", "nomrue"}
    available_cols = set(df.columns)
    
    if not required_cols.issubset(available_cols):
        missing = required_cols - available_cols
        raise ValueError(f"Colonnes manquantes: {missing}. Colonnes disponibles: {sorted(available_cols)}")
    
    print("🔍 Détection du schéma Mascouche (colonnes réelles)")
    
    # Construire les données normalisées
    result_data = []
    
    for _, row in df.iterrows():
        # street_name: utiliser le nouveau helper _build_street
        street_name = _build_street(
            row.get("nomrue"), 
            row.get("OdoParti"), 
            row.get("OdoSpeci")
        )
        
        # house_number: NoCiv + NoCivSuf (si non nul)
        house_number = str(row["NoCiv"]).strip()
        if not _is_null(row.get("NoCivSuf")):
            house_number += " " + str(row["NoCivSuf"]).strip()
        
        # postal_code: pas disponible, laisser None
        postal_code = None
        
        # sector: pas disponible, laisser None
        sector = None
        
        # Créer la clé d'adresse normalisée (JAMAIS de "nan")
        addr_key = f"{_normalize_text(street_name)}|{_normalize_text(house_number)}|{_normalize_text(postal_code or '')}"
        
        result_data.append({
            "street_name": street_name,
            "house_number": house_number,
            "postal_code": postal_code,
            "sector": sector,
            "addr_key": addr_key
        })
    
    result_df = pd.DataFrame(result_data)
    print(f"✅ {len(result_df)} adresses préparées avec clés normalisées")
    
    return result_df

def create_staging_table(conn):
    """Crée la table staging pour l'import"""
    print("🏗️ Création de la table staging")
    
    conn.execute("DROP TABLE IF EXISTS addresses_staging")
    conn.execute("""
        CREATE TABLE addresses_staging (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            street_name TEXT NOT NULL,
            house_number TEXT NOT NULL,
            postal_code TEXT,
            sector TEXT,
            addr_key TEXT NOT NULL UNIQUE
        )
    """)
    
    # Index pour performance
    conn.execute("CREATE UNIQUE INDEX idx_staging_addr_key ON addresses_staging(addr_key)")
    
    print("✅ Table staging créée")

def insert_into_staging(conn, df):
    """Insère les données dans la table staging avec déduplication"""
    print(f"📥 Insertion de {len(df)} adresses dans staging")
    
    cursor = conn.cursor()
    inserted_count = 0
    ignored_count = 0
    
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO addresses_staging 
                (street_name, house_number, postal_code, sector, addr_key)
                VALUES (?, ?, ?, ?, ?)
            """, (
                row["street_name"],
                row["house_number"], 
                row["postal_code"],
                row["sector"],
                row["addr_key"]
            ))
            
            if cursor.rowcount > 0:
                inserted_count += 1
            else:
                ignored_count += 1
                
        except Exception as e:
            print(f"❌ Erreur insertion ligne: {e}")
            ignored_count += 1
    
    conn.commit()
    
    print(f"✅ Staging: {inserted_count} insérées, {ignored_count} doublons ignorés")
    return inserted_count, ignored_count

def atomic_swap_tables(conn):
    """Échange atomique des tables avec préservation des assignements"""
    print("🔄 Échange atomique des tables")
    
    # Nettoyer les tables temporaires qui pourraient exister
    conn.execute("DROP TABLE IF EXISTS addresses_new")
    conn.execute("DROP TABLE IF EXISTS addresses_old")
    
    # Vérifier si addresses existe
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    addresses_exists = "addresses" in tables
    
    if addresses_exists:
        print("📋 Sauvegarde de l'ancienne table addresses")
        conn.execute("ALTER TABLE addresses RENAME TO addresses_old")
    
    # Créer la nouvelle table addresses avec schéma complet
    print("🏗️ Création de la nouvelle table addresses")
    conn.execute("""
        CREATE TABLE addresses_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            street_name TEXT NOT NULL,
            house_number TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            osm_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            postal_code TEXT,
            sector TEXT,
            assigned_to TEXT,
            addr_key TEXT NOT NULL UNIQUE
        )
    """)
    
    # Copier les données depuis staging
    print("📋 Copie des données depuis staging")
    conn.execute("""
        INSERT INTO addresses_new (street_name, house_number, postal_code, sector, addr_key)
        SELECT street_name, house_number, postal_code, sector, addr_key
        FROM addresses_staging
    """)
    
    # Préserver les assignements si possible
    preserved_count = 0
    if addresses_exists:
        print("🔗 Préservation des assignements existants")
        
        # Vérifier si l'ancienne table a une colonne addr_key
        old_columns = {row[1] for row in conn.execute("PRAGMA table_info(addresses_old)").fetchall()}
        
        if "addr_key" in old_columns:
            # L'ancienne table a déjà addr_key (réimport)
            cursor = conn.execute("""
                UPDATE addresses_new 
                SET assigned_to = (
                    SELECT assigned_to 
                    FROM addresses_old 
                    WHERE addresses_old.addr_key = addresses_new.addr_key 
                    AND COALESCE(addresses_old.assigned_to, '') <> ''
                )
                WHERE EXISTS (
                    SELECT 1 
                    FROM addresses_old 
                    WHERE addresses_old.addr_key = addresses_new.addr_key 
                    AND COALESCE(addresses_old.assigned_to, '') <> ''
                )
            """)
            preserved_count = cursor.rowcount
        else:
            # L'ancienne table n'a pas addr_key, faire correspondance par street_name + house_number
            print("⚠️ Ancienne table sans addr_key, correspondance par rue+numéro")
            cursor = conn.execute("""
                UPDATE addresses_new 
                SET assigned_to = (
                    SELECT assigned_to 
                    FROM addresses_old 
                    WHERE LOWER(TRIM(addresses_old.street_name)) = LOWER(TRIM(addresses_new.street_name))
                    AND LOWER(TRIM(addresses_old.house_number)) = LOWER(TRIM(addresses_new.house_number))
                    AND COALESCE(addresses_old.assigned_to, '') <> ''
                    LIMIT 1
                )
                WHERE EXISTS (
                    SELECT 1 
                    FROM addresses_old 
                    WHERE LOWER(TRIM(addresses_old.street_name)) = LOWER(TRIM(addresses_new.street_name))
                    AND LOWER(TRIM(addresses_old.house_number)) = LOWER(TRIM(addresses_new.house_number))
                    AND COALESCE(addresses_old.assigned_to, '') <> ''
                )
            """)
            preserved_count = cursor.rowcount
        
        print(f"✅ {preserved_count} assignements préservés")
    
    # Créer les index
    print("🔗 Création des index")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_addr_key ON addresses_new(addr_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_addr_sector ON addresses_new(sector)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_addr_assigned ON addresses_new(assigned_to)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_addr_street ON addresses_new(street_name)")
    
    # Finaliser l'échange
    conn.execute("DROP TABLE IF EXISTS addresses")
    conn.execute("ALTER TABLE addresses_new RENAME TO addresses")
    
    # Nettoyer
    conn.execute("DROP TABLE IF EXISTS addresses_old")
    conn.execute("DROP TABLE IF EXISTS addresses_staging")
    
    print("✅ Échange atomique terminé")
    return preserved_count

def import_mascouche_addresses_authoritative():
    """Import Excel en mode autoritatif avec staging et préservation assignements"""
    print("=== Import Excel Autoritatif ===")
    
    # 1. Lire et préparer les données Excel
    df = read_and_prepare_excel()
    total_excel = len(df)
    
    # 2. Traitement en base
    with sqlite3.connect(DB_PATH) as conn:
        # 3. Créer table staging
        create_staging_table(conn)
        
        # 4. Insérer dans staging avec déduplication
        inserted_count, ignored_count = insert_into_staging(conn, df)
        
        # 5. Échange atomique avec préservation assignements
        preserved_count = atomic_swap_tables(conn)
        
        # 6. Statistiques finales
        final_count = conn.execute("SELECT COUNT(*) FROM addresses").fetchone()[0]
        
        conn.commit()
    
    # 7. Rapport final
    print("\n=== RAPPORT FINAL ===")
    print(f"📊 Total lignes Excel: {total_excel}")
    print(f"📊 Uniques en staging: {inserted_count}")
    print(f"📊 Doublons Excel ignorés: {ignored_count}")
    print(f"📊 Total final addresses: {final_count}")
    print(f"📊 Assignements préservés: {preserved_count}")
    print("✅ Import autoritatif terminé avec succès!")

if __name__ == "__main__":
    import_mascouche_addresses_authoritative()