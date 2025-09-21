"""
GuignoMap v5.0 - Database operation            admin_exists = session.execute(
                text("SELECT COUNT(*) FROM teams WHERE id = 'ADMIN'")
            ).scalar() or 0
            
            if admin_exists > 0:h SQLAlchemy
Migration from raw sqlite3 to SQLAlchemy + PostgreSQL support
"""
import os
import pandas as pd
import hashlib
import bcrypt
from datetime import datetime
import json
from pathlib import Path
import secrets
import string
from typing import Optional, List, Dict, Any

from sqlalchemy import text, and_, or_
from src.database.connection import get_session, db_retry
from src.database.models import Street, Team, Note, ActivityLog, Address
from guignomap.backup import auto_backup_before_critical, BackupManager
from guignomap.validators import validate_and_clean_input, InputValidator


# =============================================================================
# CONFIGURATION & CONSTANTES
# =============================================================================

# Schéma de migration - utilisé pour vérifier les tables existantes
REQUIRED_TABLES = ['streets', 'teams', 'notes', 'activity_log', 'addresses']


# =============================================================================
# FONCTIONS DE CONNEXION ET INITIALISATION
# =============================================================================

@db_retry(max_retries=3)
def init_db():
    """Initialise la base de données avec les données initiales"""
    try:
        with get_session() as session:
            # Vérifier si admin existe
            admin_exists = session.execute(
                text("SELECT COUNT(*) FROM teams WHERE id = 'ADMIN'")
            ).scalar()
            
            if admin_exists == 0:
                pwd = os.getenv("GM_ADMIN_PWD", "RELAIS2025")
                create_team('ADMIN', 'Superviseur', pwd)
            
            # Auto-import des rues si vide
            streets_count = session.execute(
                text("SELECT COUNT(*) FROM streets")
            ).scalar()
            
            if streets_count == 0:
                print("🔄 Aucune rue trouvée. Import automatique depuis OpenStreetMap...")
                auto_import_streets()
                
    except Exception as e:
        print(f"❌ Erreur init_db: {e}")
        raise


def auto_import_streets():
    """Import automatique des rues depuis OSM cache"""
    try:
        from guignomap.osm import load_geometry_cache
        
        with get_session() as session:
            cache = load_geometry_cache()
            if not cache:
                print("⚠️ Aucun cache OSM trouvé. Utilisez 'Construire carte' dans l'admin.")
                return
            
            imported = 0
            for street_name in cache.keys():
                if street_name and street_name.strip():
                    # Vérifier si existe déjà
                    exists = session.execute(
                        text("SELECT COUNT(*) FROM streets WHERE name = :name"),
                        {"name": street_name.strip()}
                    ).scalar()
                    
                    if exists == 0:
                        session.execute(text("""
                            INSERT INTO streets (name, status) 
                            VALUES (:name, 'a_faire')
                        """), {"name": street_name.strip()})
                        imported += 1
            
            session.commit()
            print(f"✅ {imported} rues importées depuis OSM")
            
    except Exception as e:
        print(f"❌ Erreur auto_import_streets: {e}")


# =============================================================================
# GESTION DES ÉQUIPES ET AUTHENTIFICATION
# =============================================================================

def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


@db_retry(max_retries=2)
def create_team(team_id: str, name: str, password: str) -> bool:
    """Crée une nouvelle équipe"""
    try:
        with get_session() as session:
            # Vérifier si l'équipe existe déjà
            exists = session.execute(
                text("SELECT COUNT(*) FROM teams WHERE id = :id"),
                {"id": team_id}
            ).scalar() or 0
            
            if exists > 0:
                return False
            
            password_hash = hash_password(password)
            session.execute(text("""
                INSERT INTO teams (id, name, password_hash, created_at, active)
                VALUES (:id, :name, :hash, CURRENT_TIMESTAMP, 1)
            """), {
                "id": team_id,
                "name": name, 
                "hash": password_hash
            })
            session.commit()
            
            # Log de l'activité
            log_activity(session, team_id, 'create_team', f"Équipe '{name}' créée")
            
            return True
            
    except Exception as e:
        print(f"❌ Erreur create_team: {e}")
        return False


@db_retry(max_retries=2)
def verify_team(team_id: str, password: str) -> bool:
    """Vérifie les identifiants d'une équipe"""
    try:
        with get_session() as session:
            result = session.execute(
                text("SELECT password_hash FROM teams WHERE id = :id AND active = 1"),
                {"id": team_id}
            ).first()
            
            if not result:
                return False
            
            stored_hash = result[0]
            
            # Support bcrypt (nouveau) et MD5 legacy (migration)
            if stored_hash.startswith('$2b$'):
                # bcrypt
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
            else:
                # MD5 legacy - migrer automatiquement
                if hashlib.md5(password.encode()).hexdigest() == stored_hash:
                    # Migrer vers bcrypt
                    new_hash = hash_password(password)
                    session.execute(
                        text("UPDATE teams SET password_hash = :hash WHERE id = :id"),
                        {"hash": new_hash, "id": team_id}
                    )
                    session.commit()
                    return True
                return False
                
    except Exception as e:
        print(f"❌ Erreur verify_team: {e}")
        return False


def get_all_teams() -> List[Dict[str, Any]]:
    """Récupère toutes les équipes actives"""
    try:
        with get_session() as session:
            result = session.execute(text("""
                SELECT id, name, created_at, 
                       (SELECT COUNT(*) FROM streets WHERE team = teams.id) as assigned_streets
                FROM teams 
                WHERE active = 1 
                ORDER BY name
            """))
            
            return [dict(row._mapping) for row in result]
            
    except Exception as e:
        print(f"❌ Erreur get_all_teams: {e}")
        return []


def teams() -> List[str]:
    """Récupère la liste des IDs d'équipes actives"""
    try:
        with get_session() as session:
            result = session.execute(
                text("SELECT id FROM teams WHERE active = 1 ORDER BY name")
            )
            return [row[0] for row in result]
            
    except Exception as e:
        print(f"❌ Erreur teams: {e}")
        return []


@auto_backup_before_critical
def delete_team(team_id: str) -> bool:
    """Supprime une équipe (soft delete)"""
    try:
        with get_session() as session:
            session.execute(
                text("UPDATE teams SET active = 0 WHERE id = :id"),
                {"id": team_id}
            )
            session.commit()
            return True
            
    except Exception as e:
        print(f"❌ Erreur delete_team: {e}")
        return False


# =============================================================================
# GESTION DES RUES ET STATUTS  
# =============================================================================

def list_streets(team: Optional[str] = None) -> pd.DataFrame:
    """Liste les rues avec filtrage optionnel par équipe"""
    try:
        with get_session() as session:
            if team:
                query = text("""
                    SELECT id, name, sector, team, status
                    FROM streets 
                    WHERE team = :team
                    ORDER BY name
                """)
                result = session.execute(query, {"team": team})
            else:
                query = text("""
                    SELECT id, name, sector, team, status
                    FROM streets 
                    ORDER BY name
                """)
                result = session.execute(query)
            
            # Convertir en DataFrame
            rows = [dict(row._mapping) for row in result]
            return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['id', 'name', 'sector', 'team', 'status'])
            
    except Exception as e:
        print(f"❌ Erreur list_streets: {e}")
        return pd.DataFrame(columns=['id', 'name', 'sector', 'team', 'status'])


def get_unassigned_streets() -> List[str]:
    """Récupère les rues non assignées à une équipe"""
    try:
        with get_session() as session:
            result = session.execute(text("""
                SELECT name FROM streets 
                WHERE team IS NULL OR team = ''
                ORDER BY name
            """))
            return [row[0] for row in result]
            
    except Exception as e:
        print(f"❌ Erreur get_unassigned_streets: {e}")
        return []


@auto_backup_before_critical
def assign_streets_to_team(street_names: List[str], team_id: str) -> int:
    """Assigne plusieurs rues à une équipe"""
    try:
        with get_session() as session:
            count = 0
            for street_name in street_names:
                # Vérifier si la rue existe et n'est pas assignée
                existing = session.execute(text("""
                    SELECT COUNT(*) FROM streets 
                    WHERE name = :name AND (team IS NULL OR team = '')
                """), {"name": street_name}).scalar() or 0
                
                if existing > 0:
                    session.execute(text("""
                        UPDATE streets 
                        SET team = :team 
                        WHERE name = :name AND (team IS NULL OR team = '')
                    """), {"team": team_id, "name": street_name})
                    count += 1
            
            session.commit()
            
            # Log de l'activité
            if count > 0:
                log_activity(session, team_id, 'assign_streets', 
                           f"{count} rues assignées à l'équipe")
            
            return count
            
    except Exception as e:
        print(f"❌ Erreur assign_streets_to_team: {e}")
        return 0


@auto_backup_before_critical
def set_status(name: str, status: str) -> bool:
    """Met à jour le statut d'une rue"""
    try:
        # Validation du statut
        valid_statuses = ['a_faire', 'en_cours', 'terminee']
        if status not in valid_statuses:
            return False
        
        with get_session() as session:
            # Vérifier si la rue existe
            exists = session.execute(
                text("SELECT COUNT(*) FROM streets WHERE name = :name"),
                {"name": name}
            ).scalar() or 0
            
            if exists > 0:
                session.execute(text("""
                    UPDATE streets 
                    SET status = :status 
                    WHERE name = :name
                """), {"status": status, "name": name})
                
                session.commit()
                
                # Log de l'activité
                team = session.execute(
                    text("SELECT team FROM streets WHERE name = :name"),
                    {"name": name}
                ).scalar()
                
                if team:
                    log_activity(session, team, 'status_change', 
                               f"Rue '{name}' -> {status}")
                
                return True
            return False
            
    except Exception as e:
        print(f"❌ Erreur set_status: {e}")
        return False


# =============================================================================
# GESTION DES NOTES ET ADRESSES
# =============================================================================

@auto_backup_before_critical
def add_note_for_address(street_name: str, team_id: str, address_number: str, comment: str) -> bool:
    """Ajoute une note pour une adresse spécifique"""
    try:
        # Validation et nettoyage
        _, comment = validate_and_clean_input("comment", comment)
        _, address_number = validate_and_clean_input("address_number", address_number)
        
        with get_session() as session:
            session.execute(text("""
                INSERT INTO notes (street_name, team_id, address_number, comment, created_at)
                VALUES (:street, :team, :addr, :comment, CURRENT_TIMESTAMP)
            """), {
                "street": street_name,
                "team": team_id,
                "addr": address_number,
                "comment": comment
            })
            session.commit()
            
            # Log de l'activité
            log_activity(session, team_id, 'add_note', 
                       f"Note ajoutée: {street_name} #{address_number}")
            
            return True
            
    except Exception as e:
        print(f"❌ Erreur add_note_for_address: {e}")
        return False


def get_street_addresses_with_notes(street_name: str) -> List[Dict[str, Any]]:
    """Récupère les adresses avec notes pour une rue"""
    try:
        with get_session() as session:
            result = session.execute(text("""
                SELECT address_number, comment, team_id, created_at
                FROM notes 
                WHERE street_name = :street
                ORDER BY CAST(address_number AS INTEGER), created_at DESC
            """), {"street": street_name})
            
            return [dict(row._mapping) for row in result]
            
    except Exception as e:
        print(f"❌ Erreur get_street_addresses_with_notes: {e}")
        return []


def get_team_notes(team_id: str) -> List[Dict[str, Any]]:
    """Récupère toutes les notes d'une équipe"""
    try:
        with get_session() as session:
            result = session.execute(text("""
                SELECT street_name, address_number, comment, created_at
                FROM notes 
                WHERE team_id = :team
                ORDER BY created_at DESC
            """), {"team": team_id})
            
            return [dict(row._mapping) for row in result]
            
    except Exception as e:
        print(f"❌ Erreur get_team_notes: {e}")
        return []


# =============================================================================
# STATISTIQUES ET RAPPORTS
# =============================================================================

def extended_stats() -> Dict[str, Any]:
    """Statistiques étendues de l'application"""
    try:
        with get_session() as session:
            # Stats de base
            total_streets = session.execute(text("SELECT COUNT(*) FROM streets")).scalar() or 0
            assigned_streets = session.execute(text("SELECT COUNT(*) FROM streets WHERE team IS NOT NULL AND team != ''")).scalar() or 0
            completed_streets = session.execute(text("SELECT COUNT(*) FROM streets WHERE status = 'terminee'")).scalar() or 0
            in_progress_streets = session.execute(text("SELECT COUNT(*) FROM streets WHERE status = 'en_cours'")).scalar() or 0
            
            # Stats par statut
            status_counts = session.execute(text("""
                SELECT status, COUNT(*) as count
                FROM streets 
                GROUP BY status
            """))
            status_data = {row[0]: row[1] for row in status_counts}
            
            return {
                'total_streets': total_streets,
                'assigned_streets': assigned_streets,
                'unassigned_streets': total_streets - assigned_streets,
                'completed_streets': completed_streets,
                'in_progress_streets': in_progress_streets,
                'todo_streets': total_streets - completed_streets - in_progress_streets,
                'completion_rate': (completed_streets / total_streets * 100) if total_streets > 0 else 0,
                'status_breakdown': status_data
            }
            
    except Exception as e:
        print(f"❌ Erreur extended_stats: {e}")
        return {}


def stats_by_team() -> List[Dict[str, Any]]:
    """Statistiques par équipe"""
    try:
        with get_session() as session:
            result = session.execute(text("""
                SELECT 
                    t.id,
                    t.name,
                    COUNT(s.id) as total_streets,
                    SUM(CASE WHEN s.status = 'terminee' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN s.status = 'en_cours' THEN 1 ELSE 0 END) as in_progress,
                    SUM(CASE WHEN s.status = 'a_faire' THEN 1 ELSE 0 END) as todo
                FROM teams t
                LEFT JOIN streets s ON s.team = t.id
                WHERE t.active = 1
                GROUP BY t.id, t.name
                ORDER BY t.name
            """))
            
            return [dict(row._mapping) for row in result]
            
    except Exception as e:
        print(f"❌ Erreur stats_by_team: {e}")
        return []


def recent_activity(limit: int = 10) -> List[Dict[str, Any]]:
    """Activité récente dans l'application"""
    try:
        with get_session() as session:
            result = session.execute(text("""
                SELECT team_id, action, details, created_at
                FROM activity_log 
                ORDER BY created_at DESC 
                LIMIT :limit
            """), {"limit": limit})
            
            return [dict(row._mapping) for row in result]
            
    except Exception as e:
        print(f"❌ Erreur recent_activity: {e}")
        return []


def export_to_csv() -> str:
    """Exporte les données vers CSV"""
    try:
        from datetime import datetime
        
        df = list_streets()
        if df.empty:
            return ""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_dir = Path(__file__).parent.parent / "exports"
        export_dir.mkdir(exist_ok=True)
        
        filename = f"guignomap_export_{timestamp}.csv"
        filepath = export_dir / filename
        
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return str(filepath)
        
    except Exception as e:
        print(f"❌ Erreur export_to_csv: {e}")
        return ""


# =============================================================================
# LOG D'ACTIVITÉ
# =============================================================================

def log_activity(session, team_id: str, action: str, details: str):
    """Log une activité dans la base de données"""
    try:
        session.execute(text("""
            INSERT INTO activity_log (team_id, action, details, created_at)
            VALUES (:team, :action, :details, CURRENT_TIMESTAMP)
        """), {
            "team": team_id,
            "action": action,
            "details": details
        })
        # Note: commit fait par la fonction appelante
        
    except Exception as e:
        print(f"❌ Erreur log_activity: {e}")


# =============================================================================
# FONCTIONS MANQUANTES POUR COMPATIBILITÉ APP.PY
# =============================================================================

def get_team_streets(team_id: str) -> List[Dict[str, Any]]:
    """Récupère les rues assignées à une équipe avec tous les détails"""
    try:
        with get_session() as session:
            result = session.execute(text("""
                SELECT id, name, sector, team, status
                FROM streets 
                WHERE team = :team 
                ORDER BY name
            """), {"team": team_id})
            return [dict(row._mapping) for row in result]
    except Exception as e:
        print(f"❌ Erreur get_team_streets: {e}")
        return []


def get_unassigned_streets_count() -> int:
    """Compte les rues non assignées"""
    try:
        with get_session() as session:
            count = session.execute(text("""
                SELECT COUNT(*) FROM streets 
                WHERE team IS NULL OR team = ''
            """)).scalar() or 0
            return count
    except Exception as e:
        print(f"❌ Erreur get_unassigned_streets_count: {e}")
        return 0


def get_sectors_list() -> List[str]:
    """Récupère la liste des secteurs"""
    try:
        with get_session() as session:
            result = session.execute(text("""
                SELECT DISTINCT sector FROM streets 
                WHERE sector IS NOT NULL AND sector != ''
                ORDER BY sector
            """))
            return [row[0] for row in result]
    except Exception as e:
        print(f"❌ Erreur get_sectors_list: {e}")
        return []


def get_teams_list() -> List[str]:
    """Récupère la liste des équipes (alias pour teams())"""
    return teams()


def bulk_assign_sector(sector: str, team_id: str) -> int:
    """Assigne toutes les rues d'un secteur à une équipe"""
    try:
        with get_session() as session:
            # Récupérer les rues non assignées du secteur
            result = session.execute(text("""
                SELECT name FROM streets 
                WHERE sector = :sector AND (team IS NULL OR team = '')
            """), {"sector": sector})
            
            street_names = [row[0] for row in result]
            
            if street_names:
                return assign_streets_to_team(street_names, team_id)
            return 0
            
    except Exception as e:
        print(f"❌ Erreur bulk_assign_sector: {e}")
        return 0


def get_assignations_export_data() -> List[Dict[str, Any]]:
    """Données pour export des assignations"""
    try:
        with get_session() as session:
            result = session.execute(text("""
                SELECT s.name as street_name, s.sector, s.team, s.status,
                       t.name as team_name
                FROM streets s
                LEFT JOIN teams t ON s.team = t.id
                ORDER BY s.name
            """))
            return [dict(row._mapping) for row in result]
    except Exception as e:
        print(f"❌ Erreur get_assignations_export_data: {e}")
        return []


def export_notes_csv() -> str:
    """Exporte les notes vers CSV"""
    try:
        from datetime import datetime
        
        with get_session() as session:
            result = session.execute(text("""
                SELECT n.street_name, n.team_id, n.address_number, 
                       n.comment, n.created_at,
                       t.name as team_name
                FROM notes n
                LEFT JOIN teams t ON n.team_id = t.id
                ORDER BY n.created_at DESC
            """))
            
            if not result:
                return ""
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_dir = Path(__file__).parent.parent / "exports"
            export_dir.mkdir(exist_ok=True)
            
            filename = f"notes_export_{timestamp}.csv"
            filepath = export_dir / filename
            
            import pandas as pd
            df = pd.DataFrame([dict(row._mapping) for row in result])
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            
            return str(filepath)
            
    except Exception as e:
        print(f"❌ Erreur export_notes_csv: {e}")
        return ""


def import_addresses_from_cache(addr_cache: Dict) -> int:
    """Importe les adresses depuis le cache OSM"""
    try:
        with get_session() as session:
            imported = 0
            
            for street_name, addresses in addr_cache.items():
                if isinstance(addresses, list):
                    for addr in addresses:
                        # Insérer l'adresse si elle n'existe pas
                        exists = session.execute(text("""
                            SELECT COUNT(*) FROM addresses 
                            WHERE street_name = :street AND house_number = :num
                        """), {"street": street_name, "num": str(addr)}).scalar() or 0
                        
                        if exists == 0:
                            session.execute(text("""
                                INSERT INTO addresses (street_name, house_number)
                                VALUES (:street, :num)
                            """), {"street": street_name, "num": str(addr)})
                            imported += 1
            
            session.commit()
            return imported
            
    except Exception as e:
        print(f"❌ Erreur import_addresses_from_cache: {e}")
        return 0


def update_street_status(street_name: str, status: str, team_id: str) -> bool:
    """Met à jour le statut d'une rue (alias pour set_status)"""
    return set_status(street_name, status)


def get_street_notes_for_team(street_name: str, team_id: str) -> List[Dict[str, Any]]:
    """Récupère les notes d'une rue pour une équipe spécifique"""
    try:
        with get_session() as session:
            result = session.execute(text("""
                SELECT address_number, comment, created_at
                FROM notes 
                WHERE street_name = :street AND team_id = :team
                ORDER BY created_at DESC
            """), {"street": street_name, "team": team_id})
            
            return [dict(row._mapping) for row in result]
            
    except Exception as e:
        print(f"❌ Erreur get_street_notes_for_team: {e}")
        return []


def add_street_note(street_name: str, team_id: str, address_number: str, comment: str) -> bool:
    """Ajoute une note pour une rue (alias pour add_note_for_address)"""
    return add_note_for_address(street_name, team_id, address_number, comment)


# =============================================================================
# COMPATIBILITÉ LEGACY
# =============================================================================

def get_backup_manager(db_path=None):
    """Compatibilité avec backup.py - retourne le BackupManager"""
    # Pour l'instant, utilise encore l'ancien système de backup
    # TODO: Migrer le backup vers SQLAlchemy dans Phase 2
    if db_path is None:
        db_path = Path(__file__).parent / "guigno_map.db"
    return BackupManager(db_path)


# =============================================================================
# MIGRATION PASSWORD LEGACY
# =============================================================================

def migrate_all_passwords_to_bcrypt():
    """Migre tous les mots de passe MD5 vers bcrypt"""
    try:
        with get_session() as session:
            # Récupérer toutes les équipes avec hash MD5
            result = session.execute(text("""
                SELECT id, password_hash 
                FROM teams 
                WHERE password_hash NOT LIKE '$2b$%' AND active = 1
            """))
            
            migrated = 0
            for row in result:
                team_id, old_hash = row
                print(f"⚠️ Équipe {team_id} a un hash MD5 legacy")
                print("La migration automatique se fera lors de la prochaine connexion")
                # Note: la migration se fait automatiquement dans verify_team()
                
            print(f"✅ {migrated} mots de passe à migrer détectés")
            
    except Exception as e:
        print(f"❌ Erreur migrate_all_passwords_to_bcrypt: {e}")