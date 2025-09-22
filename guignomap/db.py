# === Fonctions manquantes pour compatibilité app.py ===========================
from datetime import datetime

def update_street_status(conn, street_name, status, team_id=None):
    """
    Met à jour ou insère une ligne dans street_status pour la rue donnée.
    Status ∈ {"a_faire","en_cours","terminee"}.
    Si absent → INSERT avec statut fourni.
    Si présent → UPDATE du statut et updated_at.
    """
    assert status in {"a_faire", "en_cours", "terminee"}, "Statut invalide"
    cur = conn.cursor()
    cur.execute("SELECT id FROM street_status WHERE street_name = ?", (street_name,))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO street_status (street_name, team_id, status, updated_at) VALUES (?, ?, ?, ?)",
            (street_name, team_id, status, datetime.now().isoformat(timespec="seconds"))
        )
    else:
        cur.execute(
            "UPDATE street_status SET status = ?, team_id = ?, updated_at = ? WHERE street_name = ?",
            (status, team_id, datetime.now().isoformat(timespec="seconds"), street_name)
        )
    conn.commit()
    return True

def get_street_notes_for_team(conn, street_name, team_id):
    """
    Retourne les notes de la table street_status pour la rue et l’équipe.
    Retourne [] si aucune note.
    """
    cur = conn.cursor()
    cur.execute("SELECT notes FROM street_status WHERE street_name = ? AND team_id = ?", (street_name, team_id))
    row = cur.fetchone()
    if row and row[0]:
        return row[0].split('\n')
    return []

def add_street_note(conn, street_name, team_id, note):
    """
    Ajoute une note à la colonne notes (concaténée avec horodatage ISO).
    Met aussi last_checkpoint à note. Ne change pas le statut si déjà défini.
    """
    cur = conn.cursor()
    ts = datetime.now().isoformat(timespec="seconds")
    entry = f"[{ts}] {team_id}: {note}".strip()
    cur.execute("SELECT notes FROM street_status WHERE street_name = ?", (street_name,))
    row = cur.fetchone()
    old_notes = row[0] if row and row[0] else None
    combined = (old_notes + "\n" + entry) if old_notes else entry
    cur.execute(
        "UPDATE street_status SET notes = ?, last_checkpoint = ? WHERE street_name = ?",
        (combined, note, street_name)
    )
    conn.commit()
    return True

def get_visited_addresses_for_street(conn, street_name, team_id=None):
    """
    Retourne la liste des adresses (house_number + comment) marquées comme "Visitée" dans la table notes.
    Si la table notes n’existe plus, retourne [] avec un TODO comment.
    """
    try:
        if team_id:
            query = "SELECT address_number, comment FROM notes WHERE street_name = ? AND team_id = ? AND comment = 'Visitée'"
            params = (street_name, team_id)
        else:
            query = "SELECT address_number, comment FROM notes WHERE street_name = ? AND comment = 'Visitée'"
            params = (street_name,)
        cur = conn.cursor()
        cur.execute(query, params)
        return [(row[0], row[1]) for row in cur.fetchall()]
    except Exception:
        # TODO: Table notes absente, retourner []
        return []
# === end fonctions manquantes =================================================
# === basic DB connection helper ================================================
import sqlite3
from pathlib import Path

DB_PATH_DEFAULT = Path(__file__).parent / "guigno_map.db"

def get_conn(db_path: str | Path = DB_PATH_DEFAULT) -> sqlite3.Connection:
    """Retourne une connexion SQLite vers la base guigno_map.db."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn
# === end helper ===============================================================
def get_addresses_for_street(conn, street_name):
    """Récupère toutes les adresses d'une rue."""
    query = "SELECT house_number FROM addresses WHERE street_name = ?"
    df = pd.read_sql_query(query, conn, params=(street_name,))
    return df
    # except Exception as e:
    #     print(f"Erreur get_addresses_for_street: {e}")
    #     return pd.DataFrame()

import sqlite3
import pandas as pd
import hashlib
import bcrypt
from datetime import datetime
from pathlib import Path
import os
from typing import Any
from guignomap.backup import auto_backup_before_critical, BackupManager
from guignomap.validators import validate_and_clean_input

def mark_address_visited(conn, street_name, house_number, team_id, note="Visitée"):
    """Ajoute une note pour marquer une adresse comme visitée."""
    try:
        # Cherche si une note "Visitée" existe déjà pour éviter les doublons
        cursor = conn.execute(
            "SELECT id FROM notes WHERE street_name = ? AND address_number = ? AND team_id = ? AND comment = 'Visitée'",
            (street_name, house_number, team_id)
        )
        if cursor.fetchone() is None:
            conn.execute(
                "INSERT INTO notes (street_name, team_id, address_number, comment) VALUES (?, ?, ?, ?)",
                (street_name, team_id, house_number, note)
            )
            conn.commit()
        return True
    except Exception:
        pass

    # --- Schéma de la base de données ---
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS sectors (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS streets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, sector_id INTEGER, team TEXT,
        status TEXT NOT NULL DEFAULT 'a_faire' CHECK (status IN ('a_faire', 'en_cours', 'terminee')),
        FOREIGN KEY (sector_id) REFERENCES sectors(id)
    );
    CREATE TABLE IF NOT EXISTS teams (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, active BOOLEAN DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, street_name TEXT NOT NULL, team_id TEXT NOT NULL,
        address_number TEXT, comment TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (street_name) REFERENCES streets(name), FOREIGN KEY (team_id) REFERENCES teams(id)
    );
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, team_id TEXT, action TEXT NOT NULL, details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, street_name TEXT NOT NULL, house_number TEXT NOT NULL,
        code_postal TEXT, latitude REAL, longitude REAL, osm_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (street_name) REFERENCES streets(name)
    );
    CREATE INDEX IF NOT EXISTS idx_streets_team ON streets(team);
    CREATE INDEX IF NOT EXISTS idx_streets_status ON streets(status);
    CREATE INDEX IF NOT EXISTS idx_notes_street ON notes(street_name);
    CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_addresses_street ON addresses(street_name);
    CREATE INDEX IF NOT EXISTS idx_addresses_number ON addresses(house_number);
    """

    # --- Connexion et Initialisation ---
    def get_conn(db_path):
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(conn):
        try:
            conn.executescript(SCHEMA)
            cursor = conn.execute("SELECT COUNT(*) FROM teams WHERE id = 'ADMIN'")
            if cursor.fetchone()[0] == 0:
                pwd = os.getenv("GM_ADMIN_PWD", "RELAIS2025")
                create_team(conn, 'ADMIN', 'Superviseur', pwd)
            cursor = conn.execute("SELECT COUNT(*) FROM streets")
            if cursor.fetchone()[0] == 0:
                print("INFO: La table des rues est vide. Lancez un import manuel.")
            conn.commit()
        except Exception as e:
            print(f"Erreur lors de l'initialisation de la DB: {e}")
            raise

    # --- Fonctions de Logging ---
    def log_activity(conn, team_id, action, details):
        try:
            conn.execute(
                "INSERT INTO activity_log (team_id, action, details) VALUES (?, ?, ?)",
                (str(team_id) if team_id else 'SYSTEM', str(action), str(details))
            )
            conn.commit()
        except Exception as e:
            print(f"Erreur log_activity: {e}")

    # --- Fonctions pour les Équipes ---
    def hash_password(password):
        salt = bcrypt.gensalt(); return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def create_team(conn, team_id, name, password):
        try:
            hashed_pw = hash_password(password)
            conn.execute("INSERT INTO teams (id, name, password_hash) VALUES (?, ?, ?)", (team_id, name, hashed_pw))
            conn.commit(); log_activity(conn, "ADMIN", "TEAM_CREATED", f"Équipe {team_id} créée"); return True
        except sqlite3.IntegrityError: return False

    def verify_team(conn, team_id, password):
        cursor = conn.execute("SELECT password_hash FROM teams WHERE id = ? AND active = 1", (team_id,)); row = cursor.fetchone()
        if row and bcrypt.checkpw(password.encode('utf-8'), row[0].encode('utf-8')): return True
        return False

    def teams(conn):
        cursor = conn.execute("SELECT id FROM teams WHERE active = 1 AND id != 'ADMIN' ORDER BY id")
        return [row[0] for row in cursor.fetchall()]

    def get_all_teams(conn):
        query = """
            SELECT t.id, t.name, t.created_at, COUNT(s.id) as streets_count
            FROM teams t LEFT JOIN streets s ON t.id = s.team WHERE t.active = 1 AND t.id != 'ADMIN'
            GROUP BY t.id, t.name, t.created_at ORDER BY t.id
        """
        return pd.read_sql_query(query, conn)
    
    def get_teams_list(conn):
        try:
            cursor = conn.execute("SELECT id, name FROM teams WHERE active = 1 AND id != 'ADMIN' ORDER BY name")
            return [(row[0], row[1]) for row in cursor.fetchall()]
        except Exception as e: print(f"Erreur get_teams_list: {e}"); return []

    # --- Fonctions pour les Rues et Secteurs ---
    def list_streets(conn, team=None):
        try:
            base_query = "SELECT s.name, COALESCE(c.name, 'Non assigné') as sector, COALESCE(s.team, '') as team, COALESCE(s.status, 'a_faire') as status FROM streets s LEFT JOIN sectors c ON s.sector_id = c.id"
            if team:
                query = base_query + " WHERE s.team = ? GROUP BY s.name, c.name, s.team, s.status ORDER BY s.status, s.name"
                df = pd.read_sql_query(query, conn, params=(team,))
            else:
                query = base_query + " GROUP BY s.name, c.name, s.team, s.status ORDER BY s.team, s.status, s.name"
                df = pd.read_sql_query(query, conn)
            return df
        except Exception as e: print(f"Erreur list_streets: {e}"); return pd.DataFrame()

    def get_unassigned_streets(conn):
        query = "SELECT s.name, COALESCE(c.name, 'Non assigné') as sector FROM streets s LEFT JOIN sectors c ON s.sector_id = c.id WHERE s.team IS NULL OR s.team = '' ORDER BY sector, s.name"
        return pd.read_sql_query(query, conn)

    def assign_streets_to_team(conn, street_names, team_id):
        try:
            placeholders = ','.join('?' for _ in street_names)
            query = f"UPDATE streets SET team = ? WHERE name IN ({placeholders})"
            params = [team_id] + street_names
            conn.execute(query, params); conn.commit(); return True
        except Exception: conn.rollback(); return False

    def set_status(conn, name, status):
        conn.execute("UPDATE streets SET status = ? WHERE name = ?", (status, name)); conn.commit()

    def create_sector(conn, name):
        try:
            valid_name, clean_name = validate_and_clean_input("text", name)
            if not valid_name: return False, "Nom invalide."
            conn.execute("INSERT INTO sectors (name) VALUES (?)", (clean_name,)); conn.commit()
            return True, f"Secteur '{clean_name}' créé."
        except sqlite3.IntegrityError: return False, "Ce secteur existe déjà."

    def get_sectors_list(conn):
        return pd.read_sql_query("SELECT id, name FROM sectors ORDER BY name", conn)

    def assign_streets_to_sector(conn, street_names, sector_id):
        try:
            placeholders = ','.join('?' for _ in street_names)
            query = f"UPDATE streets SET sector_id = ? WHERE name IN ({placeholders})"
            params = [sector_id] + street_names
            cursor = conn.execute(query, params); conn.commit(); return cursor.rowcount
        except Exception: conn.rollback(); return 0
    
    def bulk_assign_sector(conn, sector_id, team_id):
        try:
            cursor = conn.execute("UPDATE streets SET team = ? WHERE sector_id = ?", (team_id, sector_id)); conn.commit()
            return cursor.rowcount
        except Exception: conn.rollback(); return 0

    # --- Fonctions pour les Notes ---
    def add_note_for_address(conn, street_name, team_id, address_number, comment):
        conn.execute("INSERT INTO notes (street_name, team_id, address_number, comment) VALUES (?, ?, ?, ?)", (street_name, team_id, address_number, comment)); conn.commit()

    def get_street_addresses_with_notes(conn, street_name):
        query = "SELECT n.address_number, n.comment, n.created_at, t.name as team_name FROM notes n JOIN teams t ON n.team_id = t.id WHERE n.street_name = ? ORDER BY CAST(n.address_number AS INTEGER), n.created_at DESC"
        return pd.read_sql_query(query, conn, params=(street_name,))

    def get_team_notes(conn, team_id):
        query = "SELECT street_name, address_number, comment, created_at FROM notes WHERE team_id = ? ORDER BY created_at DESC LIMIT 50"
        return pd.read_sql_query(query, conn, params=(team_id,))

    # --- Fonctions de Statistiques ---
    def extended_stats(conn):
        try:
            cursor = conn.execute("SELECT (SELECT COUNT(*) FROM streets) as total, SUM(CASE WHEN status = 'terminee' THEN 1 ELSE 0 END) as done, SUM(CASE WHEN status = 'en_cours' THEN 1 ELSE 0 END) as partial FROM streets")
            row = cursor.fetchone(); return {"total": row['total'] or 0, "done": row['done'] or 0, "partial": row['partial'] or 0}
        except Exception: return {"total": 0, "done": 0, "partial": 0}

    def stats_by_team(conn):
        query = """
            SELECT s.team, COUNT(s.id) as total, SUM(CASE WHEN s.status = 'terminee' THEN 1 ELSE 0 END) as done,
            ROUND((SUM(CASE WHEN s.status = 'terminee' THEN 1.0 ELSE 0 END) / COUNT(s.id)) * 100, 1) as progress
            FROM streets s WHERE s.team IS NOT NULL AND s.team != '' GROUP BY s.team ORDER BY progress DESC
        """
        return pd.read_sql_query(query, conn)

    def recent_activity(conn, limit=10):
        query = "SELECT datetime(created_at, 'localtime') as timestamp, COALESCE(team_id, 'SYSTEM') as team, action, details FROM activity_log ORDER BY created_at DESC LIMIT ?"
        return pd.read_sql_query(query, conn, params=(limit,))

    # --- Fonctions d'Export ---
    def export_to_csv(conn):
        query = "SELECT s.name as rue, COALESCE(c.name, 'N/A') as secteur, s.team as equipe, s.status FROM streets s LEFT JOIN sectors c ON s.sector_id = c.id ORDER BY s.team, s.name"
        df = pd.read_sql_query(query, conn); return df.to_csv(index=False).encode('utf-8')

    def export_notes_csv(conn):
        query = "SELECT n.street_name as rue, n.address_number as numero, n.team_id as equipe, n.comment, n.created_at FROM notes n ORDER BY n.street_name, CAST(n.address_number AS INTEGER)"
        df = pd.read_sql_query(query, conn); return df.to_csv(index=False).encode('utf-8')

    def get_assignations_export_data(conn):
        query = "SELECT COALESCE(c.name, 'Non assigné') as secteur, s.name as rue, COALESCE(s.team, 'Non assignée') as equipe, s.status FROM streets s LEFT JOIN sectors c ON s.sector_id = c.id ORDER BY secteur, rue"
        return pd.read_sql_query(query, conn)

    # --- Autres Fonctions Utilitaires ---
    def get_backup_manager(db_path):
        return BackupManager(db_path)

    def get_unassigned_streets_count(conn):
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM streets WHERE team IS NULL OR team = ''"); return cursor.fetchone()[0] or 0
        except Exception: return 0

    def import_addresses_from_cache(conn, cache):
        # Cette fonction est probablement obsolète mais conservée pour référence
        return 0# === street_status API (append-only, safe) =====================================
from datetime import datetime
import sqlite3
def init_street_status_schema(conn: sqlite3.Connection) -> None:
    """
    Crée la table de suivi si absente + index sur team_id.
    Idempotent, safe à appeler plusieurs fois.
    """
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS street_status (
            id INTEGER PRIMARY KEY,
            street_name TEXT UNIQUE,
            team_id TEXT,
            status TEXT DEFAULT 'a_faire',       -- 'a_faire' | 'en_cours' | 'terminee'
            last_checkpoint TEXT,
            notes TEXT,
            completed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_street_status_team ON street_status(team_id);")
    conn.commit()
def mark_street_complete(conn: sqlite3.Connection, street_name: str, team_id: str) -> None:
    """
    Marque une rue comme terminée, enregistrement/upsert par street_name.
    """
    init_street_status_schema(conn)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO street_status (street_name, team_id, status, completed_at)
        VALUES (?, ?, 'terminee', CURRENT_TIMESTAMP)
        ON CONFLICT(street_name) DO UPDATE SET
            team_id=excluded.team_id,
            status='terminee',
            completed_at=CURRENT_TIMESTAMP,
            updated_at=CURRENT_TIMESTAMP;
    """, (street_name, team_id))
    conn.commit()
def mark_street_in_progress(conn: sqlite3.Connection, street_name: str, team_id: str, checkpoint_note: str = "") -> None:
    """
    Marque une rue comme en cours. Si checkpoint_note est fourni, met à jour last_checkpoint.
    """
    init_street_status_schema(conn)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO street_status (street_name, team_id, status, last_checkpoint)
        VALUES (?, ?, 'en_cours', ?)
        ON CONFLICT(street_name) DO UPDATE SET
            team_id=excluded.team_id,
            status='en_cours',
            last_checkpoint=CASE
                WHEN ? IS NOT NULL AND ? <> '' THEN ?
                ELSE street_status.last_checkpoint
            END,
            updated_at=CURRENT_TIMESTAMP;
    """, (street_name, team_id, checkpoint_note, checkpoint_note, checkpoint_note, checkpoint_note))
    conn.commit()
def save_checkpoint(conn: sqlite3.Connection, street_name: str, team_id: str, note: str) -> None:
    """
    Ajoute une note horodatée au champ notes, et met à jour last_checkpoint.
    Conserve le status courant s'il existe, sinon le force à 'en_cours'.
    """
    init_street_status_schema(conn)
    cur = conn.cursor()
    cur.execute("SELECT notes FROM street_status WHERE street_name = ?;", (street_name,))
    row = cur.fetchone()
    old_notes = row[0] if row and row[0] else None
    ts = datetime.now().isoformat(timespec="seconds")
    entry = f"[{ts}] {team_id}: {note}".strip()
    combined = (old_notes + "\n" + entry) if old_notes else entry
    cur.execute("""
        INSERT INTO street_status (street_name, team_id, status, last_checkpoint, notes)
        VALUES (?, ?, COALESCE((SELECT status FROM street_status WHERE street_name=?), 'en_cours'), ?, ?)
        ON CONFLICT(street_name) DO UPDATE SET
            team_id=excluded.team_id,
            notes=?,
            last_checkpoint=?,
            updated_at=CURRENT_TIMESTAMP;
    """, (street_name, team_id, street_name, note, combined, combined, note))
    conn.commit()
def get_team_streets_status(conn: sqlite3.Connection, team_id: str) -> list[dict]:
    """
    Retourne la vue d'équipe : [{street_name, team_id, status, last_checkpoint, notes, completed_at, updated_at}]
    Triée par nom de rue pour stabilité.
    """
    init_street_status_schema(conn)
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT street_name, team_id, status, last_checkpoint, notes, completed_at, updated_at
        FROM street_status
        WHERE team_id = ?
        ORDER BY street_name ASC;
    """, (team_id,)).fetchall()
    result = []
    for r in rows:
        result.append({
            "street_name": r[0],
            "team_id": r[1],
            "status": r[2],
            "last_checkpoint": r[3],
            "notes": r[4],
            "completed_at": r[5],
            "updated_at": r[6],
        })
    return result
# === end street_status API =====================================================
