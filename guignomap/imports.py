"""
GuignoMap - Module d'import réutilisable pour adresses
Fonctions normalisées pour l'import de données d'adresses depuis Excel/CSV
"""
import re
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any
import unicodedata
import logging

from guignomap.database import get_conn, _ensure_foreign_keys


def normalize_text(txt: str) -> str:
    """
    Normalise un texte pour l'import :
    - Gère les valeurs 'nan' et None
    - Convertit en ASCII (gère accents/apostrophes)
    - Strip whitespace
    """
    if pd.isna(txt) or txt is None or str(txt).lower() in ['nan', 'none', '']:
        return ""
    
    # Convertir en string et strip
    text = str(txt).strip()
    
    # Normaliser les caractères Unicode (NFD = décomposition)
    # puis supprimer les diacritiques
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    
    # Remplacer les apostrophes typographiques et simples par des espaces
    # pour garantir la stabilité des clés d'adresse
    text = text.replace("'", " ").replace("'", " ").replace("`", " ")
    
    # Nettoyer les espaces multiples
    text = ' '.join(text.split())
    
    return text.strip()


def build_addr_key(street: str, number: str, postal: Optional[str] = None) -> str:
    """
    Construit une clé unique d'adresse normalisée :
    format: "street|number|postal" (lower, ascii, sans espaces)
    """
    street_norm = normalize_text(street).lower().replace(' ', '')
    number_norm = normalize_text(str(number)).lower().replace(' ', '')
    
    if postal and postal.strip():
        postal_norm = normalize_text(postal).lower().replace(' ', '')
        return f"{street_norm}|{number_norm}|{postal_norm}"
    else:
        return f"{street_norm}|{number_norm}|"


def detect_schema(df: pd.DataFrame, city: Optional[str] = None) -> Dict[str, str]:
    """
    Détecte automatiquement le schéma des colonnes dans un DataFrame :
    Retourne un mapping {street, number, postal?, sector?}
    """
    columns = df.columns.tolist()  # Garder les noms originaux
    columns_lower = [col.lower().strip() for col in columns]  # Version lower pour la recherche
    mapping = {}
    
    # Patterns de détection
    street_patterns = ['rue', 'street', 'voie', 'adresse', 'nom']
    number_patterns = ['nociv', 'numero', 'number', 'no', 'num', 'civic']
    postal_patterns = ['postal', 'code', 'zip']
    sector_patterns = ['secteur', 'sector', 'zone', 'district']
    
    def find_column(patterns, columns_list, original_columns):
        for pattern in patterns:
            for i, col in enumerate(columns_list):
                if pattern in col:
                    return original_columns[i]  # Retourner le nom original
        return None
    
    # Détection des colonnes principales
    street_col = find_column(street_patterns, columns_lower, columns)
    number_col = find_column(number_patterns, columns_lower, columns)
    postal_col = find_column(postal_patterns, columns_lower, columns)
    sector_col = find_column(sector_patterns, columns_lower, columns)
    
    if street_col:
        mapping['street'] = street_col
    if number_col:
        mapping['number'] = number_col
    if postal_col:
        mapping['postal'] = postal_col
    if sector_col:
        mapping['sector'] = sector_col
    
    logging.info(f"Schéma détecté pour {city or 'données'}: {mapping}")
    return mapping


def prepare_dataframe(df: pd.DataFrame, mapping: Dict[str, str], city: Optional[str] = None) -> pd.DataFrame:
    """
    Prépare un DataFrame pour l'import avec colonnes standardisées :
    [street_name, house_number, postal_code, sector, addr_key]
    """
    if 'street' not in mapping or 'number' not in mapping:
        raise ValueError("Mapping doit contenir au minimum 'street' et 'number'")
    
    # Création du DataFrame préparé
    prepared = pd.DataFrame()
    
    # Colonnes obligatoires
    prepared['street_name'] = df[mapping['street']].apply(normalize_text)
    prepared['house_number'] = df[mapping['number']].apply(lambda x: normalize_text(str(x)))
    
    # Colonnes optionnelles
    prepared['postal_code'] = ""
    if 'postal' in mapping and mapping['postal'] in df.columns:
        prepared['postal_code'] = df[mapping['postal']].apply(normalize_text)
    
    prepared['sector'] = ""
    if 'sector' in mapping and mapping['sector'] in df.columns:
        prepared['sector'] = df[mapping['sector']].apply(normalize_text)
    
    # Génération de la clé d'adresse
    prepared['addr_key'] = prepared.apply(
        lambda row: build_addr_key(row['street_name'], row['house_number'], row['postal_code']),
        axis=1
    )
    
    # Filtrer les lignes vides ou invalides
    initial_count = len(prepared)
    prepared = prepared[
        (prepared['street_name'] != "") & 
        (prepared['house_number'] != "") &
        (prepared['addr_key'] != "||")
    ].copy()
    
    filtered_count = initial_count - len(prepared)
    if filtered_count > 0:
        logging.warning(f"Filtré {filtered_count} lignes invalides/vides")
    
    # Supprimer les doublons basés sur addr_key
    duplicate_count = len(prepared) - len(prepared.drop_duplicates(subset=['addr_key']))
    if duplicate_count > 0:
        logging.warning(f"Supprimé {duplicate_count} doublons basés sur addr_key")
        prepared = prepared.drop_duplicates(subset=['addr_key'])
    
    logging.info(f"DataFrame préparé: {len(prepared)} adresses uniques")
    return prepared


def authoritative_swap(conn: sqlite3.Connection, df_prepared: pd.DataFrame) -> Dict[str, int]:
    """
    Swap atomique autoritatif des adresses :
    - Crée une table staging avec contrainte UNIQUE sur addr_key
    - Swap atomique avec la table addresses
    - Préserve assigned_to si la colonne existe
    - Ajoute les colonnes manquantes avec valeurs par défaut
    """
    _ensure_foreign_keys(conn)
    cursor = conn.cursor()
    
    try:
        # 1. Créer table staging
        cursor.execute("DROP TABLE IF EXISTS addresses_staging")
        cursor.execute("""
            CREATE TABLE addresses_staging (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                street_name TEXT NOT NULL,
                house_number TEXT NOT NULL,
                postal_code TEXT DEFAULT '',
                sector TEXT DEFAULT '',
                assigned_to TEXT DEFAULT NULL,
                latitude REAL DEFAULT NULL,
                longitude REAL DEFAULT NULL,
                osm_type TEXT DEFAULT NULL,
                addr_key TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Vérifier si la table addresses existe et a une colonne assigned_to
        existing_assignments = {}
        try:
            cursor.execute("SELECT addr_key, assigned_to FROM addresses WHERE assigned_to IS NOT NULL AND assigned_to != ''")
            existing_assignments = {row[0]: row[1] for row in cursor.fetchall()}
            logging.info(f"Préservation de {len(existing_assignments)} assignations existantes")
        except sqlite3.OperationalError:
            logging.info("Table addresses n'existe pas ou pas de colonne assigned_to")
        
        # 3. Préparer les données pour l'insertion
        now = datetime.now().isoformat()
        insert_data = []
        
        for _, row in df_prepared.iterrows():
            addr_key = row['addr_key']
            assigned_to = existing_assignments.get(addr_key, None)
            
            insert_data.append((
                row['street_name'],
                row['house_number'],
                row.get('postal_code', ''),
                row.get('sector', ''),
                assigned_to,
                None,  # latitude
                None,  # longitude
                None,  # osm_type
                addr_key,
                now,   # created_at
                now    # updated_at
            ))
        
        # 4. Insertion en staging
        cursor.executemany("""
            INSERT INTO addresses_staging 
            (street_name, house_number, postal_code, sector, assigned_to, 
             latitude, longitude, osm_type, addr_key, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, insert_data)
        
        # 5. Créer les index sur staging
        cursor.execute("CREATE UNIQUE INDEX idx_staging_addr_key ON addresses_staging(addr_key)")
        cursor.execute("CREATE INDEX idx_staging_street_number ON addresses_staging(street_name, house_number)")
        
        # 6. Swap atomique des tables
        cursor.execute("DROP TABLE IF EXISTS addresses_old")
        cursor.execute("ALTER TABLE addresses RENAME TO addresses_old")
        cursor.execute("ALTER TABLE addresses_staging RENAME TO addresses")
        
        # 7. Nettoyer l'ancienne table
        cursor.execute("DROP TABLE IF EXISTS addresses_old")
        
        conn.commit()
        
        # 8. Statistiques
        final_count = len(df_prepared)
        preserved_assignments = len([a for a in existing_assignments.values() if a])
        
        stats = {
            'total_imported': final_count,
            'preserved_assignments': preserved_assignments,
            'new_unassigned': final_count - preserved_assignments
        }
        
        logging.info(f"Swap réussi: {stats}")
        return stats
        
    except Exception as e:
        conn.rollback()
        logging.error(f"Erreur lors du swap: {e}")
        raise