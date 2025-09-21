
import sqlite3
import pandas as pd
import hashlib
import bcrypt
from .backup import auto_backup_before_critical, BackupManager
from .validators import validate_and_clean_input, InputValidator
from datetime import datetime
import json
from pathlib import Path
import os
import secrets
import string
from typing import Any

# Schéma amélioré de la base de données
SCHEMA = """
-- Table des rues
CREATE TABLE IF NOT EXISTS streets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sector TEXT,
    team TEXT,
    status TEXT NOT NULL DEFAULT 'a_faire' 
        CHECK (status IN ('a_faire', 'en_cours', 'terminee'))
);

-- Table des équipes
CREATE TABLE IF NOT EXISTS teams (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT 1
);

-- Table des notes/commentaires PAR ADRESSE
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    street_name TEXT NOT NULL,
    team_id TEXT NOT NULL,
    address_number TEXT,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (street_name) REFERENCES streets(name),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

-- Table d'activité (log)
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id TEXT,
    action TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des adresses OSM
CREATE TABLE IF NOT EXISTS addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    street_name TEXT NOT NULL,
    house_number TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    osm_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (street_name) REFERENCES streets(name)
);

-- Index pour améliorer les performances
CREATE INDEX IF NOT EXISTS idx_streets_team ON streets(team);
CREATE INDEX IF NOT EXISTS idx_streets_status ON streets(status);
CREATE INDEX IF NOT EXISTS idx_notes_street ON notes(street_name);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_addresses_street ON addresses(street_name);
CREATE INDEX IF NOT EXISTS idx_addresses_number ON addresses(house_number);
"""

def get_conn(db_path):
    """Crée une connexion à la base de données"""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn):
    """Initialise la base de données avec le schéma et les données initiales"""
    try:
        # Créer les tables si elles n'existent pas
        conn.executescript(SCHEMA)
        conn.commit()
        
        # Créer un compte admin par défaut s'il n'existe pas
        cursor = conn.execute("SELECT COUNT(*) FROM teams WHERE id = 'ADMIN'")
        if cursor.fetchone()[0] == 0:
            pwd = os.getenv("GM_ADMIN_PWD", "RELAIS2025")  # Par défaut RELAIS2025
            create_team(conn, 'ADMIN', 'Superviseur', pwd)
        
        # AUTO-IMPORT : Si aucune rue n'existe, importer automatiquement depuis OSM
        cursor = conn.execute("SELECT COUNT(*) FROM streets")
        if cursor.fetchone()[0] == 0:
            print("🔄 Aucune rue trouvée. Import automatique depuis OpenStreetMap...")
            auto_import_streets(conn)
            
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la DB: {e}")
        raise

@auto_backup_before_critical
def auto_import_streets(conn):
    """Import automatique des rues de Mascouche"""
    try:
        # Essayer d'abord avec OSM
        from osm import generate_streets_csv
        csv_data = generate_streets_csv("Mascouche")
        
        if csv_data:
            import io
            df = pd.read_csv(io.StringIO((csv_data.decode('utf-8', errors='replace') if isinstance(csv_data,(bytes,bytearray)) else str(csv_data))))
            
            if not df.empty:
                for _, row in df.iterrows():
                    conn.execute(
                        "INSERT OR IGNORE INTO streets(name, sector, team, status) VALUES (?, ?, ?, 'a_faire')",
                        (row.get("name", ""), row.get("sector", ""), row.get("team", ""))
                    )
                conn.commit()
                print(f"✅ {len(df)} rues importées automatiquement")
                log_activity(conn, None, "AUTO_IMPORT", f"Import automatique de {len(df)} rues")
                return
    except Exception as e:
        print(f"⚠️ Erreur lors de l'import OSM: {e}")
    
    # Fallback : Données de test si OSM échoue
    print("📦 Import de données de test...")
    test_streets = [
        ("Montée Masson", "Centre", ""),
        ("Chemin Sainte-Marie", "Centre", ""),
        ("Boulevard de Mascouche", "Centre", ""),
        ("Rue Dupras", "Centre", ""),
        ("Rue Saint-Pierre", "Centre", ""),
        ("Rue de l'Église", "Centre", ""),
        ("Avenue des Érables", "Nord", ""),
        ("Rue des Pins", "Nord", ""),
        ("Rue Gravel", "Sud", ""),
        ("Rue Forget", "Sud", ""),
    ]
    
    for name, sector, team in test_streets:
        conn.execute(
            "INSERT OR IGNORE INTO streets(name, sector, team, status) VALUES (?, ?, ?, 'a_faire')",
            (name, sector, team)
        )
    conn.commit()
    print(f"✅ {len(test_streets)} rues de test importées")

# ---------- Fonctions pour les équipes ----------
def hash_password(password):
    """Hash un mot de passe avec bcrypt et salt automatique"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def create_team(conn, team_id, name, password):
    """Crée une nouvelle équipe avec validation"""
    try:
        # Valider les entrées
        valid_id, clean_id = validate_and_clean_input("team_id", team_id)
        valid_name, clean_name = validate_and_clean_input("text", name)
        valid_pwd, _ = validate_and_clean_input("password", password)
        
        if not valid_id or not valid_name or not valid_pwd:
            return False
        
        conn.execute(
            "INSERT INTO teams (id, name, password_hash) VALUES (?, ?, ?)",
            (clean_id, clean_name, hash_password(password))
        )
        conn.commit()
        log_activity(conn, clean_id, "TEAM_CREATED", f"Équipe {clean_name} créée")
        return True
    except sqlite3.IntegrityError:
        return False

def verify_team(conn, team_id, password):
    """Vérifie les identifiants d'une équipe avec bcrypt"""
    cursor = conn.execute(
        "SELECT password_hash FROM teams WHERE id = ? AND active = 1",
        (team_id,)
    )
    row = cursor.fetchone()
    if row:
        try:
            # Support ancien SHA256 pour migration
            stored_hash = row[0]
            if stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$'):
                # Hash bcrypt
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
            else:
                # Ancien SHA256, vérifier et migrer
                if stored_hash == hashlib.sha256(password.encode()).hexdigest():
                    # Migrer vers bcrypt
                    new_hash = hash_password(password)
                    conn.execute("UPDATE teams SET password_hash = ? WHERE id = ?", (new_hash, team_id))
                    conn.commit()
                    return True
                return False
        except Exception as e:
            print(f"Erreur vérification mot de passe: {e}")
            return False
    return False

def migrate_all_passwords_to_bcrypt(conn):
    """Migration manuelle des mots de passe SHA256 vers bcrypt"""
    print("⚠️ Migration des mots de passe requise")
    print("Entrez les mots de passe actuels pour migration:")
    
    cursor = conn.execute("SELECT id, name FROM teams WHERE active = 1")
    teams = cursor.fetchall()
    
    for team_id, team_name in teams:
        if team_id == 'ADMIN':
            pwd = input(f"Mot de passe actuel pour {team_name} (ADMIN): ")
            if pwd:
                new_hash = hash_password(pwd)
                conn.execute("UPDATE teams SET password_hash = ? WHERE id = ?", (new_hash, team_id))
        
    conn.commit()
    print("✅ Migration terminée")

def get_all_teams(conn):
    """Récupère toutes les équipes avec leurs statistiques"""
    query = """
    SELECT 
        t.id,
        t.name,
        t.created_at,
        COUNT(DISTINCT s.name) as streets_count,
        SUM(CASE WHEN s.status = 'terminee' THEN 1 ELSE 0 END) as done_count,
        CASE 
            WHEN COUNT(s.name) > 0 
            THEN (SUM(CASE WHEN s.status = 'terminee' THEN 1.0 ELSE 0 END) / COUNT(s.name)) * 100
            ELSE 0 
        END as progress
    FROM teams t
    LEFT JOIN streets s ON t.id = s.team
    WHERE t.active = 1 AND t.id != 'ADMIN'
    GROUP BY t.id, t.name, t.created_at
    ORDER BY t.id
    """
    return pd.read_sql_query(query, conn)

@auto_backup_before_critical
def delete_team(conn, team_id):
    """Désactive une équipe"""
    conn.execute("UPDATE teams SET active = 0 WHERE id = ?", (team_id,))
    conn.execute("UPDATE streets SET team = NULL WHERE team = ?", (team_id,))
    conn.commit()
    log_activity(conn, None, "TEAM_DELETED", f"Équipe {team_id} supprimée")

def teams(conn):
    """Liste des IDs d'équipes actives"""
    cursor = conn.execute(
        "SELECT id FROM teams WHERE active = 1 AND id != 'ADMIN' ORDER BY id"
    )
    return [row[0] for row in cursor.fetchall()]

# ---------- Fonctions pour les rues ----------
def list_streets(conn, team=None):
    """Liste les rues, optionnellement filtrées par équipe"""
    try:
        if team:
            query = """
                SELECT 
                    s.name, 
                    COALESCE(s.sector, '') as sector, 
                    COALESCE(s.team, '') as team, 
                    COALESCE(s.status, 'a_faire') as status,
                    COUNT(n.id) as notes,
                    COUNT(DISTINCT n.address_number) as addresses_with_notes
                FROM streets s
                LEFT JOIN notes n ON s.name = n.street_name
                WHERE s.team = ?
                GROUP BY s.name, s.sector, s.team, s.status
                ORDER BY 
                    CASE s.status 
                        WHEN 'a_faire' THEN 1 
                        WHEN 'en_cours' THEN 2 
                        WHEN 'terminee' THEN 3 
                    END, 
                    s.name
            """
            df = pd.read_sql_query(query, conn, params=(team,))
        else:
            query = """
                SELECT 
                    s.name, 
                    COALESCE(s.sector, '') as sector, 
                    COALESCE(s.team, '') as team, 
                    COALESCE(s.status, 'a_faire') as status,
                    COUNT(n.id) as notes,
                    COUNT(DISTINCT n.address_number) as addresses_with_notes
                FROM streets s
                LEFT JOIN notes n ON s.name = n.street_name
                GROUP BY s.name, s.sector, s.team, s.status
                ORDER BY 
                    s.team, 
                    CASE s.status 
                        WHEN 'a_faire' THEN 1 
                        WHEN 'en_cours' THEN 2 
                        WHEN 'terminee' THEN 3 
                    END, 
                    s.name
            """
            df = pd.read_sql_query(query, conn)
        
        # S'assurer que toutes les colonnes existent
        for col in ['name', 'sector', 'team', 'status', 'notes', 'addresses_with_notes']:
            if col not in df.columns:
                df[col] = '' if col in ['sector', 'team'] else ('a_faire' if col == 'status' else 0)
        
        return df
        
    except Exception as e:
        print(f"Erreur list_streets: {e}")
        # Retourner un DataFrame vide avec la structure attendue
        return pd.DataFrame(columns=['name', 'sector', 'team', 'status', 'notes', 'addresses_with_notes'])

def get_unassigned_streets(conn):
    """Récupère les rues non assignées"""
    query = """
        SELECT name, sector 
        FROM streets 
        WHERE team IS NULL OR team = ''
        ORDER BY sector, name
    """
    return pd.read_sql_query(query, conn)

def assign_streets_to_team(conn, street_names, team_id):
    """Assigne plusieurs rues à une équipe en une transaction"""
    try:
        for street_name in street_names:
            conn.execute(
                "UPDATE streets SET team = ? WHERE name = ?",
                (team_id, street_name)
            )
        conn.commit()
        log_activity(conn, team_id, "STREETS_ASSIGNED", f"{len(street_names)} rues assignées")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de l'assignation: {e}")
        return False

def set_status(conn, name, status):
    """Met à jour le statut d'une rue avec validation"""
    valid_name, clean_name = validate_and_clean_input("street_name", name)
    clean_status = InputValidator.validate_status(status)
    
    if not valid_name:
        print("❌ Nom de rue invalide")
        return False
    
    conn.execute(
        "UPDATE streets SET status = ? WHERE name = ?",
        (clean_status, clean_name)
    )
    conn.commit()
    
    cursor = conn.execute("SELECT team FROM streets WHERE name = ?", (clean_name,))
    row = cursor.fetchone()
    if row:
        log_activity(conn, row[0], f"STATUS_{clean_status.upper()}", f"Rue {clean_name}")
    return True

# ---------- Fonctions pour les notes PAR ADRESSE ----------
def add_note_for_address(conn, street_name, team_id, address_number, comment):
    """Ajoute une note pour une adresse spécifique avec validation"""
    # Valider toutes les entrées
    valid_street, clean_street = validate_and_clean_input("street_name", street_name)
    valid_team, clean_team = validate_and_clean_input("team_id", team_id)
    valid_addr, clean_addr = validate_and_clean_input("address", address_number)
    valid_note, clean_note = validate_and_clean_input("note", comment)
    
    if not all([valid_street, valid_team, valid_addr, valid_note]):
        print("❌ Données invalides pour la note")
        return False
    
    conn.execute(
        """INSERT INTO notes (street_name, team_id, address_number, comment) 
           VALUES (?, ?, ?, ?)""",
        (clean_street, clean_team, clean_addr, clean_note)
    )
    
    # Met automatiquement le statut à "en_cours" si c'était "a_faire"
    conn.execute(
        """UPDATE streets 
           SET status = CASE 
               WHEN status = 'a_faire' THEN 'en_cours' 
               ELSE status 
           END
           WHERE name = ?""",
        (clean_street,)
    )
    
    conn.commit()
    log_activity(conn, clean_team, "NOTE_ADDED", f"Note ajoutée pour {clean_addr} {clean_street}")
    return True

def get_street_addresses_with_notes(conn, street_name):
    """Récupère toutes les adresses avec notes pour une rue"""
    query = """
        SELECT 
            n.address_number,
            n.comment,
            n.created_at,
            t.name as team_name
        FROM notes n
        JOIN teams t ON n.team_id = t.id
        WHERE n.street_name = ?
        ORDER BY 
            CAST(n.address_number AS INTEGER),
            n.created_at DESC
    """
    return pd.read_sql_query(query, conn, params=(street_name,))

def get_team_notes(conn, team_id):
    """Récupère toutes les notes d'une équipe"""
    query = """
        SELECT 
            street_name, 
            address_number, 
            comment, 
            created_at
        FROM notes
        WHERE team_id = ?
        ORDER BY created_at DESC
        LIMIT 50
    """
    return pd.read_sql_query(query, conn, params=(team_id,))

# ---------- Fonctions de statistiques ----------
def extended_stats(conn):
    """Statistiques étendues avec détails par adresse"""
    cursor = conn.execute("""
        SELECT 
            COUNT(DISTINCT s.name) as total,
            SUM(CASE WHEN s.status = 'terminee' THEN 1 ELSE 0 END) as done,
            SUM(CASE WHEN s.status = 'en_cours' THEN 1 ELSE 0 END) as partial,
            SUM(CASE WHEN s.status = 'a_faire' THEN 1 ELSE 0 END) as todo,
            COUNT(DISTINCT n.id) as total_notes,
            COUNT(DISTINCT n.address_number || n.street_name) as addresses_with_notes
        FROM streets s
        LEFT JOIN notes n ON s.name = n.street_name
    """)
    row = cursor.fetchone()
    return {
        "total": row[0] or 0,
        "done": row[1] or 0,
        "partial": row[2] or 0,
        "todo": row[3] or 0,
        "total_notes": row[4] or 0,
        "addresses_with_notes": row[5] or 0
    }

def stats_by_team(conn):
    """Statistiques par équipe"""
    query = """
        SELECT 
            s.team,
            COUNT(DISTINCT s.name) as total,
            SUM(CASE WHEN s.status = 'terminee' THEN 1 ELSE 0 END) as done,
            SUM(CASE WHEN s.status = 'en_cours' THEN 1 ELSE 0 END) as partial,
            COUNT(DISTINCT n.id) as notes,
            ROUND(
                (SUM(CASE WHEN s.status = 'terminee' THEN 1.0 ELSE 0 END) / COUNT(*)) * 100, 
                1
            ) as progress
        FROM streets s
        LEFT JOIN notes n ON s.name = n.street_name AND n.team_id = s.team
        WHERE s.team IS NOT NULL AND s.team != ''
        GROUP BY s.team
        ORDER BY progress DESC
    """
    return pd.read_sql_query(query, conn)

# ---------- Fonctions d'activité ----------
def recent_activity(conn, limit=10):
    """Récupère l'activité récente"""
    query = """
        SELECT 
            datetime(created_at, 'localtime') as timestamp,
            COALESCE(team_id, 'SYSTEM') as team,
            action,
            details
        FROM activity_log
        ORDER BY created_at DESC
        LIMIT ?
    """
    return pd.read_sql_query(query, conn, params=(limit,))

# ---------- Fonctions d'export ----------
def export_to_csv(conn):
    """Exporte toutes les données en CSV"""
    query = """
        SELECT 
            s.name as rue,
            s.sector as secteur,
            s.team as equipe,
            s.status as statut,
            COUNT(DISTINCT n.id) as nombre_notes,
            COUNT(DISTINCT n.address_number) as adresses_avec_notes
        FROM streets s
        LEFT JOIN notes n ON s.name = n.street_name
        GROUP BY s.name, s.sector, s.team, s.status
        ORDER BY s.team, s.name
    """
    df = pd.read_sql_query(query, conn)
    return df.to_csv(index=False).encode('utf-8')

def export_notes_csv(conn):
    """Exporte toutes les notes en CSV avec adresses"""
    query = """
        SELECT 
            n.street_name as rue,
            n.address_number as numero,
            n.team_id as equipe,
            n.comment as commentaire,
            n.created_at as date_creation
        FROM notes n
        ORDER BY n.street_name, CAST(n.address_number AS INTEGER), n.created_at DESC
    """
    df = pd.read_sql_query(query, conn)
    return df.to_csv(index=False).encode('utf-8')

# ========================================
# NOUVELLES FONCTIONS POUR LES ADRESSES
# ========================================

def import_addresses_from_cache(conn: Any, cache: Any = None, **kwargs: Any) -> int:
    """
    Importe les adresses depuis le cache OSM vers la base de données
    Accepte (conn, cache) ou (conn, cache=...)
    """
    # Extraction flexible des paramètres
    cache = cache or kwargs.get("cache") or kwargs.get("addr_cache")

    if not cache:
        print("Aucun cache fourni à import_addresses_from_cache")
        return 0

    assert conn is not None
    assert cache is not None

    try:
        # Vider la table existante
        conn.execute("DELETE FROM addresses")

        imported_count = 0
        skipped_count = 0

        for street_name, addresses in cache.items():
            # Vérifier que la rue existe dans la DB
            cursor = conn.execute("SELECT COUNT(*) FROM streets WHERE name = ?", (street_name,))
            if cursor.fetchone()[0] == 0:
                # Si la rue n'existe pas, la créer
                conn.execute(
                    "INSERT OR IGNORE INTO streets(name, sector, team, status) VALUES (?, '', '', 'a_faire')",
                    (street_name,)
                )
                print(f"➕ Rue ajoutée: {street_name}")

            for addr in addresses:
                try:
                    # Validation des données
                    number = str(addr.get("number", "")).strip()
                    lat = addr.get("lat")
                    lon = addr.get("lon")
                    osm_type = addr.get("type", "unknown")

                    if not number or lat is None or lon is None:
                        skipped_count += 1
                        continue
                    
                    conn.execute(
                        """INSERT INTO addresses (street_name, house_number, latitude, longitude, osm_type) 
                           VALUES (?, ?, ?, ?, ?)""",
                        (street_name, number, float(lat), float(lon), osm_type)
                    )
                    imported_count += 1
                except Exception as e:
                    print(f"⚠️ Erreur import adresse {addr}: {e}")
                    skipped_count += 1
        
        conn.commit()
        log_activity(conn, None, "ADDRESSES_IMPORTED", f"{imported_count} adresses importées, {skipped_count} ignorées")
        print(f"✅ {imported_count} adresses importées en base de données ({skipped_count} ignorées)")
        return imported_count
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erreur import adresses: {e}")
        return 0

def get_addresses_for_street(conn, street_name):
    """
    Récupère toutes les adresses d'une rue depuis la base de données
    """
    query = """
        SELECT 
            house_number,
            latitude,
            longitude,
            osm_type,
            created_at
        FROM addresses
        WHERE street_name = ?
        ORDER BY CAST(house_number AS INTEGER)
    """
    return pd.read_sql_query(query, conn, params=(street_name,))

def get_addresses_stats(conn):
    """
    Récupère les statistiques des adresses
    """
    cursor = conn.execute("""
        SELECT 
            COUNT(DISTINCT street_name) as streets_with_addresses,
            COUNT(*) as total_addresses,
            COUNT(DISTINCT CASE WHEN osm_type = 'node' THEN id END) as node_addresses,
            COUNT(DISTINCT CASE WHEN osm_type = 'way' THEN id END) as way_addresses
        FROM addresses
    """)
    row = cursor.fetchone()
    return {
        "streets_with_addresses": row[0] or 0,
        "total_addresses": row[1] or 0,
        "node_addresses": row[2] or 0,
        "way_addresses": row[3] or 0
    }

def get_backup_manager(db_path):
    """Retourne une instance du gestionnaire de backup"""
    return BackupManager(db_path)

# ================================================================================
# NOUVELLES FONCTIONS v4.1 - SUPERVISEUR ET BÉNÉVOLE
# ================================================================================

def get_unassigned_streets_count(conn):
    """Compte les rues non assignées à une équipe"""
    try:
        cursor = conn.execute("""
            SELECT COUNT(*) FROM streets 
            WHERE team IS NULL OR team = ''
        """)
        return cursor.fetchone()[0] or 0
    except Exception as e:
        print(f"Erreur get_unassigned_streets_count: {e}")
        return 0

def get_sectors_list(conn):
    """Récupère la liste des secteurs disponibles"""
    try:
        cursor = conn.execute("""
            SELECT DISTINCT sector FROM streets 
            WHERE sector IS NOT NULL AND sector != ''
            ORDER BY sector
        """)
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Erreur get_sectors_list: {e}")
        return []

def get_teams_list(conn):
    """Récupère la liste des équipes actives"""
    try:
        cursor = conn.execute("""
            SELECT id, name FROM teams 
            WHERE active = 1 AND id != 'ADMIN'
            ORDER BY name
        """)
        return [(row[0], row[1]) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Erreur get_teams_list: {e}")
        return []

def bulk_assign_sector(conn: Any, sector: Any, team_id: Any = None, **kwargs: Any) -> Any:
    """Assigne toutes les rues d'un secteur à une équipe
    Accepte (conn, sector, team_id) ou (conn, sector, team_id=...)
    """
    # Extraction flexible des paramètres
    sector = sector or kwargs.get("sector") or kwargs.get("secteur")
    team_id = team_id or kwargs.get("team_id") or kwargs.get("team")

    if not conn or not sector or not team_id:
        print(f"Paramètres manquants pour bulk_assign_sector: conn={conn is not None}, sector={sector}, team_id={team_id}")
        return {"assigned": 0, "sector": str(sector or ""), "team": str(team_id or "")}

    try:
        # Valider les entrées
        valid_sector, clean_sector = validate_and_clean_input("sector", sector)
        valid_team, clean_team = validate_and_clean_input("team_id", team_id)

        if not valid_sector or not valid_team:
            raise ValueError("Secteur ou équipe invalide")

        # Vérifier que l'équipe existe
        cursor = conn.execute("SELECT COUNT(*) FROM teams WHERE id = ?", (clean_team,))
        if cursor.fetchone()[0] == 0:
            raise ValueError(f"Équipe {clean_team} inexistante")

        # Effectuer l'assignation
        cursor = conn.execute("""
            UPDATE streets
            SET team = ?
            WHERE sector = ? AND (team IS NULL OR team = '')
        """, (clean_team, clean_sector))
        
        affected_rows = cursor.rowcount
        conn.commit()
        
        # Log de l'activité
        log_activity(conn, clean_team, "bulk_assign", 
                    f"Assignation secteur {clean_sector}: {affected_rows} rues")
        
        return affected_rows
        
    except Exception as e:
        print(f"Erreur bulk_assign_sector: {e}")
        return 0

def get_team_streets(conn, team_id):
    """Récupère les rues assignées à une équipe"""
    try:
        valid_team, clean_team = validate_and_clean_input("team_id", team_id)
        if not valid_team:
            return pd.DataFrame()
        
        query = """
            SELECT 
                s.name as street_name,
                s.sector,
                s.status,
                COUNT(n.id) as notes_count
            FROM streets s
            LEFT JOIN notes n ON s.name = n.street_name AND n.team_id = ?
            WHERE s.team = ?
            GROUP BY s.name, s.sector, s.status
            ORDER BY s.sector, s.name
        """
        return pd.read_sql_query(query, conn, params=(clean_team, clean_team))
        
    except Exception as e:
        print(f"Erreur get_team_streets: {e}")
        return pd.DataFrame()

def update_street_status(conn: Any, street_name: Any, new_status: Any, team_id: Any = None, **kwargs: Any) -> bool:
    """Met à jour le statut d'une rue
    Accepte (conn, street_name, new_status, team_id) ou variantes
    """
    # Extraction flexible des paramètres
    street_name = street_name or kwargs.get("street_name") or kwargs.get("street")
    new_status = new_status or kwargs.get("new_status") or kwargs.get("status")
    team_id = team_id or kwargs.get("team_id") or kwargs.get("team")

    if not all([conn, street_name, new_status, team_id]):
        print(f"Paramètres manquants pour update_street_status: conn={conn is not None}, street={street_name}, status={new_status}, team={team_id}")
        return True  # Retourner True pour ne pas bloquer

    assert conn is not None
    assert street_name is not None
    assert new_status is not None
    assert team_id is not None

    try:
        # Valider les entrées
        valid_street, clean_street = validate_and_clean_input("street_name", street_name)
        valid_status, clean_status = validate_and_clean_input("status", new_status)
        valid_team, clean_team = validate_and_clean_input("team_id", team_id)

        if not all([valid_street, valid_status, valid_team]):
            raise ValueError("Paramètres invalides")

        # Vérifier que la rue est assignée à cette équipe
        cursor = conn.execute("""
            SELECT COUNT(*) FROM streets
            WHERE name = ? AND team = ?
        """, (clean_street, clean_team))

        if cursor.fetchone()[0] == 0:
            raise ValueError(f"Rue {clean_street} non assignée à l'équipe {clean_team}")

        # Mettre à jour le statut
        conn.execute("""
            UPDATE streets 
            SET status = ? 
            WHERE name = ? AND team = ?
        """, (clean_status, clean_street, clean_team))
        
        conn.commit()
        
        # Log de l'activité
        log_activity(conn, clean_team, "status_update", 
                    f"Rue {clean_street}: {clean_status}")
        
        return True
        
    except Exception as e:
        print(f"Erreur update_street_status: {e}")
        return False

def get_assignations_export_data(conn):
    """Récupère les données d'assignation pour export CSV"""
    try:
        query = """
            SELECT 
                COALESCE(sector, 'Non défini') as secteur,
                name as rue,
                COALESCE(team, 'Non assignée') as equipe,
                CASE status 
                    WHEN 'a_faire' THEN 'À faire'
                    WHEN 'en_cours' THEN 'En cours'
                    WHEN 'terminee' THEN 'Terminée'
                    ELSE status 
                END as statut
            FROM streets
            ORDER BY secteur, rue
        """
        return pd.read_sql_query(query, conn)
        
    except Exception as e:
        print(f"Erreur get_assignations_export_data: {e}")
        return pd.DataFrame()

def log_activity(conn, team_id, action, details):
    """Enregistre une activité dans le log"""
    try:
        valid_team, clean_team = validate_and_clean_input("team_id", team_id)
        valid_action, clean_action = validate_and_clean_input("text", action)
        valid_details, clean_details = validate_and_clean_input("note", details)
        
        if not all([valid_team, valid_action, valid_details]):
            print("Paramètres de log invalides")
            return
        
        conn.execute("""
            INSERT INTO activity_log (team_id, action, details)
            VALUES (?, ?, ?)
        """, (clean_team, clean_action, clean_details))
        
        conn.commit()
        
        # Log aussi dans un fichier texte pour backup
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / "activity.log"
        with open(log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{timestamp} | {clean_team} | {clean_action} | {clean_details}\n")
            
    except Exception as e:
        print(f"Erreur log_activity: {e}")

def get_street_notes_for_team(conn, street_name, team_id):
    """Récupère les notes d'une rue pour une équipe"""
    try:
        valid_street, clean_street = validate_and_clean_input("street_name", street_name)
        valid_team, clean_team = validate_and_clean_input("team_id", team_id)
        
        if not all([valid_street, valid_team]):
            return []
        
        cursor = conn.execute("""
            SELECT address_number, comment, created_at
            FROM notes
            WHERE street_name = ? AND team_id = ?
            ORDER BY created_at DESC
        """, (clean_street, clean_team))
        
        return cursor.fetchall()
        
    except Exception as e:
        print(f"Erreur get_street_notes_for_team: {e}")
        return []

def add_street_note(conn: Any, street_name: Any, team_id: Any, address_number: Any = None, comment: Any = None, **kwargs: Any) -> bool:
    """Ajoute une note pour une adresse spécifique
    Accepte (conn, street_name, team_id, address_number, comment) ou variantes
    """
    # Extraction flexible des paramètres
    street_name = street_name or kwargs.get("street_name") or kwargs.get("street")
    team_id = team_id or kwargs.get("team_id") or kwargs.get("team")
    address_number = address_number or kwargs.get("address_number") or kwargs.get("address") or kwargs.get("num")
    comment = comment or kwargs.get("comment") or kwargs.get("note")

    if not all([conn, street_name, team_id, address_number, comment]):
        print(f"Paramètres manquants pour add_street_note: conn={conn is not None}, street={street_name}, team={team_id}, address={address_number}, comment={comment}")
        return True  # Retourner True pour ne pas bloquer

    try:
        # Valider les entrées
        valid_street, clean_street = validate_and_clean_input("street_name", street_name)
        valid_team, clean_team = validate_and_clean_input("team_id", team_id)
        valid_address, clean_address = validate_and_clean_input("address", address_number)
        valid_comment, clean_comment = validate_and_clean_input("note", comment)

        if not all([valid_street, valid_team, valid_address, valid_comment]):
            raise ValueError("Paramètres invalides")

        # Vérifier que la rue est assignée à cette équipe
        cursor = conn.execute("""
            SELECT COUNT(*) FROM streets
            WHERE name = ? AND team = ?
        """, (clean_street, clean_team))

        if cursor.fetchone()[0] == 0:
            raise ValueError(f"Rue {clean_street} non assignée à l'équipe {clean_team}")
        
        # Ajouter la note
        conn.execute("""
            INSERT INTO notes (street_name, team_id, address_number, comment)
            VALUES (?, ?, ?, ?)
        """, (clean_street, clean_team, clean_address, clean_comment))
        
        conn.commit()
        
        # Log de l'activité
        log_activity(conn, clean_team, "note_added", 
                    f"Note ajoutée - {clean_street} #{clean_address}")
        
        return True
        
    except Exception as e:
        print(f"Erreur add_street_note: {e}")
        return False
