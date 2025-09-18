"""
GuignoMap v5.0 - Database operations (SQLite Pure)
Migration from SQLAlchemy to pure SQLite3 - essential functions only
"""
import os
import pandas as pd
import hashlib
from datetime import datetime
import json
from pathlib import Path
import secrets
import string
from typing import Optional, List, Dict, Any

from src.database.sqlite_pure import get_conn
from src.auth.passwords import hash_password, verify_password
from guignomap.backup import auto_backup_before_critical, BackupManager
from guignomap.validators import validate_and_clean_input, InputValidator


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _row_dicts(cur):
    """Helper pour convertir curseur en liste de dict"""
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _ensure_foreign_keys(conn):
    """Active les foreign keys pour cette connexion"""
    conn.execute("PRAGMA foreign_keys=ON")


# =============================================================================
# INITIALIZATION FUNCTIONS
# =============================================================================

def initialize_database():
    """Initialise la base de données avec les données par défaut"""
    try:
        with get_conn() as conn:
            _ensure_foreign_keys(conn)
            
            # Vérifier si l'admin existe
            admin_exists = conn.execute(
                "SELECT COUNT(*) FROM teams WHERE id = 'ADMIN'"
            ).fetchone()[0]
            
            if admin_exists > 0:
                return {"status": "already_initialized", "message": "Base déjà initialisée"}
            
            # Créer l'équipe ADMIN
            conn.execute("""
                INSERT INTO teams(id, nom, password_hash, is_admin) 
                VALUES ('ADMIN', 'Administrateur', '', 1)
            """)
            
            # Vérifier si des rues existent
            street_count = conn.execute("SELECT COUNT(*) FROM streets").fetchone()[0]
            
            conn.commit()
            return {
                "status": "initialized", 
                "message": f"Admin créé, {street_count} rues existantes"
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def reset_database():
    """Remet la base à zéro (garde la structure)"""
    with get_conn() as conn:
        _ensure_foreign_keys(conn)
        
        # Vider les tables dans l'ordre des dépendances
        conn.execute("DELETE FROM activity_log")
        conn.execute("DELETE FROM notes")
        conn.execute("DELETE FROM addresses")
        conn.execute("DELETE FROM streets")
        conn.execute("DELETE FROM teams")
        
        conn.commit()


# =============================================================================
# TEAM OPERATIONS
# =============================================================================

def team_exists(team_id: str) -> bool:
    """Vérifie si une équipe existe"""
    with get_conn() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM teams WHERE id = ?", (team_id,)
        ).fetchone()[0]
        return count > 0


def create_team(team_id: str, team_name: str, password: str = "") -> dict:
    """Crée une nouvelle équipe"""
    try:
        with get_conn() as conn:
            _ensure_foreign_keys(conn)
            
            # Vérifier si l'équipe existe déjà
            if team_exists(team_id):
                return {"success": False, "message": "Équipe existe déjà"}
            
            password_hash = hash_password(password) if password else ""
            
            conn.execute("""
                INSERT INTO teams(id, nom, password_hash, is_admin) 
                VALUES (?, ?, ?, 0)
            """, (team_id, team_name, password_hash))
            
            conn.commit()
            return {"success": True, "message": "Équipe créée avec succès"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def authenticate_team(team_id: str, password: str) -> dict:
    """Authentifie une équipe"""
    try:
        with get_conn() as conn:
            result = conn.execute(
                "SELECT nom, password_hash, is_admin FROM teams WHERE id = ?",
                (team_id,)
            ).fetchone()
            
            if not result:
                return {"success": False, "message": "Équipe introuvable"}
            
            nom, password_hash, is_admin = result
            
            if not password_hash:  # Pas de mot de passe
                return {"success": True, "team_name": nom, "is_admin": bool(is_admin)}
            
            if verify_password(password, password_hash):
                return {"success": True, "team_name": nom, "is_admin": bool(is_admin)}
            else:
                return {"success": False, "message": "Mot de passe incorrect"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def list_teams() -> List[Dict]:
    """Liste toutes les équipes"""
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT id, nom, is_admin, 
                   COUNT(s.id) as assigned_streets
            FROM teams t
            LEFT JOIN streets s ON t.id = s.team_id
            GROUP BY t.id, t.nom, t.is_admin
            ORDER BY t.nom
        """)
        return _row_dicts(cur)


# =============================================================================
# STREET OPERATIONS
# =============================================================================

def list_streets() -> pd.DataFrame:
    """Liste toutes les rues avec leurs détails"""
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT s.id, s.name, s.sector, s.status, s.team_id,
                   t.nom as team_name,
                   COUNT(n.id) as notes_count
            FROM streets s
            LEFT JOIN teams t ON s.team_id = t.id
            LEFT JOIN notes n ON s.id = n.street_id
            GROUP BY s.id, s.name, s.sector, s.status, s.team_id, t.nom
            ORDER BY s.name
        """)
        
        data = _row_dicts(cur)
        return pd.DataFrame(data)


def get_street_details(street_id: int) -> Optional[Dict]:
    """Récupère les détails d'une rue"""
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT s.*, t.nom as team_name
            FROM streets s
            LEFT JOIN teams t ON s.team_id = t.id
            WHERE s.id = ?
        """, (street_id,))
        
        result = cur.fetchone()
        if result:
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, result))
        return None


def update_street_status(street_id: int, new_status: str, team_id: Optional[str] = None) -> bool:
    """Met à jour le statut d'une rue"""
    try:
        with get_conn() as conn:
            _ensure_foreign_keys(conn)
            
            if team_id:
                conn.execute("""
                    UPDATE streets 
                    SET status = ?, team_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_status, team_id, street_id))
            else:
                conn.execute("""
                    UPDATE streets 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_status, street_id))
            
            conn.commit()
            return True
    except Exception:
        return False


# =============================================================================
# STATISTICS & REPORTING
# =============================================================================

def extended_stats() -> Dict:
    """Statistiques étendues du projet"""
    with get_conn() as conn:
        # Compter par statut
        cur = conn.execute("SELECT status, COUNT(*) as count FROM streets GROUP BY status")
        status_counts = dict(cur.fetchall())
        
        total = sum(status_counts.values())
        done = status_counts.get('terminee', 0)
        partial = status_counts.get('en_cours', 0) + status_counts.get('partielle', 0)
        todo = status_counts.get('a_faire', 0)
        
        return {
            'total': total,
            'done': done,
            'partial': partial,
            'todo': todo,
            'progress_pct': (done / total * 100) if total > 0 else 0
        }


def stats_by_team() -> List[Dict]:
    """Statistiques par équipe"""
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT t.id, t.nom as team_name,
                   COUNT(s.id) as total_streets,
                   SUM(CASE WHEN s.status = 'terminee' THEN 1 ELSE 0 END) as completed,
                   SUM(CASE WHEN s.status IN ('en_cours', 'partielle') THEN 1 ELSE 0 END) as in_progress,
                   COUNT(n.id) as total_notes
            FROM teams t
            LEFT JOIN streets s ON t.id = s.team_id
            LEFT JOIN notes n ON s.id = n.street_id
            WHERE t.id != 'ADMIN'
            GROUP BY t.id, t.nom
            ORDER BY completed DESC, t.nom
        """)
        return _row_dicts(cur)


def recent_activity(limit: int = 20) -> List[Dict]:
    """Activité récente du système"""
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT team_id, action, details, created_at
            FROM activity_log 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        return _row_dicts(cur)


# =============================================================================
# NOTES OPERATIONS
# =============================================================================

def add_note(street_id: int, team_id: str, content: str) -> bool:
    """Ajoute une note à une rue"""
    try:
        with get_conn() as conn:
            _ensure_foreign_keys(conn)
            
            conn.execute("""
                INSERT INTO notes(street_id, team_id, content, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (street_id, team_id, content))
            
            # Log de l'activité
            conn.execute("""
                INSERT INTO activity_log(team_id, action, details, created_at)
                VALUES (?, 'note_added', ?, CURRENT_TIMESTAMP)
            """, (team_id, f"Note ajoutée sur rue ID {street_id}"))
            
            conn.commit()
            return True
    except Exception:
        return False


def get_street_notes(street_id: int) -> List[Dict]:
    """Récupère les notes d'une rue"""
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT n.*, t.nom as team_name
            FROM notes n
            LEFT JOIN teams t ON n.team_id = t.id
            WHERE n.street_id = ?
            ORDER BY n.created_at DESC
        """, (street_id,))
        return _row_dicts(cur)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def count_hash_algorithms() -> Dict[str, int]:
    """Compte les algorithmes de hash utilisés"""
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT 
                CASE 
                    WHEN password_hash LIKE 'scrypt:$%' THEN 'scrypt'
                    WHEN password_hash LIKE 'pbkdf2:sha256:$%' THEN 'pbkdf2_sha256'
                    WHEN password_hash LIKE '$2b$%' THEN 'bcrypt'
                    ELSE 'unknown'
                END as algorithm,
                COUNT(*) as count
            FROM teams 
            WHERE password_hash IS NOT NULL AND password_hash != ''
            GROUP BY algorithm
        """)
        return dict(cur.fetchall())


def health_check() -> Dict:
    """Vérification de santé de la base"""
    try:
        with get_conn() as conn:
            # Test de base
            conn.execute("SELECT 1").fetchone()
            
            # Comptes des tables principales
            teams_count = conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
            streets_count = conn.execute("SELECT COUNT(*) FROM streets").fetchone()[0]
            notes_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            
            return {
                "status": "healthy",
                "teams": teams_count,
                "streets": streets_count,
                "notes": notes_count,
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# =============================================================================
# BULK OPERATIONS
# =============================================================================

def bulk_assign_streets(team_id: str, sector: Optional[str] = None) -> Dict:
    """Assigne en lot des rues à une équipe"""
    try:
        with get_conn() as conn:
            _ensure_foreign_keys(conn)
            
            if sector:
                cur = conn.execute("""
                    UPDATE streets 
                    SET team_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE sector = ? AND (team_id IS NULL OR team_id = '')
                """, (team_id, sector))
            else:
                cur = conn.execute("""
                    UPDATE streets 
                    SET team_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE team_id IS NULL OR team_id = ''
                """, (team_id,))
            
            affected = cur.rowcount
            
            # Log de l'activité
            conn.execute("""
                INSERT INTO activity_log(team_id, action, details, created_at)
                VALUES (?, 'bulk_assign', ?, CURRENT_TIMESTAMP)
            """, (team_id, f"Assignation en lot: {affected} rues"))
            
            conn.commit()
            return {"success": True, "affected_count": affected}
    except Exception as e:
        return {"success": False, "message": str(e)}