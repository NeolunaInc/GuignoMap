import sqlite3
import pandas as pd
import hashlib
import bcrypt
from backup import auto_backup_before_critical, BackupManager
from datetime import datetime
import json
from pathlib import Path
import os
import secrets
import string

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
            df = pd.read_csv(io.StringIO(csv_data.decode('utf-8')))
            
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
    """Crée une nouvelle équipe"""
    try:
        conn.execute(
            "INSERT INTO teams (id, name, password_hash) VALUES (?, ?, ?)",
            (team_id, name, hash_password(password))
        )
        conn.commit()
        log_activity(conn, team_id, "TEAM_CREATED", f"Équipe {name} créée")
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
    """Met à jour le statut d'une rue"""
    conn.execute(
        "UPDATE streets SET status = ? WHERE name = ?",
        (status, name)
    )
    conn.commit()
    
    cursor = conn.execute("SELECT team FROM streets WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        log_activity(conn, row[0], f"STATUS_{status.upper()}", f"Rue {name}")

# ---------- Fonctions pour les notes PAR ADRESSE ----------
def add_note_for_address(conn, street_name, team_id, address_number, comment):
    """Ajoute une note pour une adresse spécifique"""
    conn.execute(
        """INSERT INTO notes (street_name, team_id, address_number, comment) 
           VALUES (?, ?, ?, ?)""",
        (street_name, team_id, address_number, comment)
    )
    
    # Met automatiquement le statut à "en_cours" si c'était "a_faire"
    conn.execute(
        """UPDATE streets 
           SET status = CASE 
               WHEN status = 'a_faire' THEN 'en_cours' 
               ELSE status 
           END
           WHERE name = ?""",
        (street_name,)
    )
    
    conn.commit()
    log_activity(conn, team_id, "NOTE_ADDED", f"Note ajoutée pour {address_number} {street_name}")

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
def log_activity(conn, team_id, action, details=None):
    """Enregistre une activité dans le log"""
    try:
        conn.execute(
            "INSERT INTO activity_log (team_id, action, details) VALUES (?, ?, ?)",
            (team_id, action, details)
        )
        conn.commit()
    except:
        pass

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

@auto_backup_before_critical
def import_addresses_from_cache(conn, cache):
    """
    Importe les adresses depuis le cache OSM vers la base de données
    """
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