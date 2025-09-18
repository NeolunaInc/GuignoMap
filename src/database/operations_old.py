"""
GuignoMap v5.0 - Database operations (SQLite Pure)
Migration from SQLAlchemy to pure SQLite3
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
        print(f"'ùå Erreur init_db: {e}")
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
        print(f"'ùå Erreur auto_import_streets: {e}")


# =============================================================================
# AUTHENTIFICATION HELPERS - SUPPORT MULTI-FORMAT
# =============================================================================

def _sha256(txt: str) -> str:
    """Utilitaire SHA-256"""
    import hashlib
    return hashlib.sha256(txt.encode('utf-8')).hexdigest()


def _pbkdf2_verify(stored: str, password: str) -> bool:
    """Vérifie un hash PBKDF2 au format Django/Python"""
    try:
        if not stored.startswith('pbkdf2_sha256$'):
            return False
        parts = stored.split('$')
        if len(parts) != 4:
            return False
        _, iterations, salt, expected = parts
        import hashlib
        import base64
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), int(iterations))
        return base64.b64encode(actual).decode() == expected
    except Exception:
        return False



# =============================================================================
# GESTION DES ÉQUIPES ET AUTHENTIFICATION (RÉÉCRIRE)
# =============================================================================

# Note: hash_password is now imported from src.auth.passwords


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
        print(f"'ùå Erreur create_team: {e}")
        return False


@db_retry(max_retries=2)
def verify_team(team_id: str, password: str) -> bool:
    """Vérifie les identifiants d'une équipe (multi-format compatible)"""
    try:
        # Normalisation des entrées
        team_id = (team_id or "").strip()
        password = (password or "").strip()
        
        if not team_id or not password:
            return False
        
        with get_session() as session:
            # Détecter les colonnes disponibles
            cols_info = session.execute(text("PRAGMA table_info(teams)")).fetchall()
            available_cols = {row[1] for row in cols_info}
            
            # Construire la requête selon les colonnes disponibles
            select_parts = ["id", "name"]
            if "password" in available_cols:
                select_parts.append("COALESCE(password, '') as password")
            else:
                select_parts.append("'' as password")
            
            if "password_hash" in available_cols:
                select_parts.append("COALESCE(password_hash, '') as password_hash")
            else:
                select_parts.append("'' as password_hash")
            
            if "password_salt" in available_cols:
                select_parts.append("COALESCE(password_salt, '') as password_salt")
            else:
                select_parts.append("'' as password_salt")
            
            query = f"SELECT {', '.join(select_parts)} FROM teams WHERE id = :id AND active = 1 LIMIT 1"
            result = session.execute(text(query), {"id": team_id}).first()
            
            if not result:
                return False
            
            _, _, stored_plain, stored_hash, stored_salt = result
            
            # Stratégie de vérification (ordre de priorité)
            
            # 1) Utiliser verify_password avec Argon2/bcrypt support
            if stored_hash:
                try:
                    verification_ok, needs_rehash = verify_password(password, stored_hash)
                    if verification_ok:
                        # Migration paresseuse si nécessaire
                        if needs_rehash:
                            new_hash = hash_password(password)
                            session.execute(
                                text("UPDATE teams SET password_hash = :hash WHERE id = :id"),
                                {"hash": new_hash, "id": team_id}
                            )
                            session.commit()
                            print(f"🔄 Migration hash pour équipe {team_id}: bcrypt → Argon2")
                        return True
                except Exception as e:
                    print(f"⚠️  Erreur verify_password pour {team_id}: {e}")
                    pass
            
            # 2) Format PBKDF2 (legacy)
            if stored_hash and _pbkdf2_verify(stored_hash, password):
                # Migration vers Argon2
                new_hash = hash_password(password)
                session.execute(
                    text("UPDATE teams SET password_hash = :hash WHERE id = :id"),
                    {"hash": new_hash, "id": team_id}
                )
                session.commit()
                print(f"🔄 Migration hash pour équipe {team_id}: PBKDF2 → Argon2")
                return True
            
            # 3) SHA-256 simple (64 hex chars) - avec migration
            if stored_hash and len(stored_hash) == 64:
                if stored_hash == _sha256(password):
                    # Migration vers Argon2
                    new_hash = hash_password(password)
                    session.execute(
                        text("UPDATE teams SET password_hash = :hash WHERE id = :id"),
                        {"hash": new_hash, "id": team_id}
                    )
                    session.commit()
                    print(f"🔄 Migration hash pour équipe {team_id}: SHA-256 → Argon2")
                    return True
                # SHA-256 avec salt environnement
                import os
                salt_env = os.environ.get("GM_PWD_SALT", "")
                if salt_env and stored_hash == _sha256(salt_env + password):
                    # Migration vers Argon2
                    new_hash = hash_password(password)
                    session.execute(
                        text("UPDATE teams SET password_hash = :hash WHERE id = :id"),
                        {"hash": new_hash, "id": team_id}
                    )
                    session.commit()
                    print(f"🔄 Migration hash pour équipe {team_id}: SHA-256+salt → Argon2")
                    return True
            
            # 4) SHA-256 avec salt stocké - avec migration
            if stored_salt and stored_hash:
                if stored_hash == _sha256(stored_salt + password):
                    # Migration vers Argon2
                    new_hash = hash_password(password)
                    session.execute(
                        text("UPDATE teams SET password_hash = :hash, password_salt = NULL WHERE id = :id"),
                        {"hash": new_hash, "id": team_id}
                    )
                    session.commit()
                    print(f"🔄 Migration hash pour équipe {team_id}: SHA-256+salt stocké → Argon2")
                    return True
            
            # 5) Mot de passe en clair (legacy) - avec migration
            if stored_plain and stored_plain == password:
                # Migration vers Argon2
                new_hash = hash_password(password)
                session.execute(
                    text("UPDATE teams SET password_hash = :hash, password = NULL WHERE id = :id"),
                    {"hash": new_hash, "id": team_id}
                )
                session.commit()
                print(f"🔄 Migration hash pour équipe {team_id}: plaintext → Argon2")
                return True
            
            # 6) Fallback MD5 legacy - avec migration
            if stored_hash:
                import hashlib
                if stored_hash == hashlib.md5(password.encode()).hexdigest():
                    # Migration vers Argon2
                    new_hash = hash_password(password)
                    session.execute(
                        text("UPDATE teams SET password_hash = :hash WHERE id = :id"),
                        {"hash": new_hash, "id": team_id}
                    )
                    session.commit()
                    print(f"🔄 Migration hash pour équipe {team_id}: MD5 → Argon2")
                    return True
            
            return False
            
    except Exception as e:
        print(f"⚠️ Erreur verify_team: {e}")
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
        print(f"'ùå Erreur get_all_teams: {e}")
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
        print(f"'ùå Erreur teams: {e}")
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
        print(f"'ùå Erreur delete_team: {e}")
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
        print(f"'ùå Erreur list_streets: {e}")
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
        print(f"'ùå Erreur get_unassigned_streets: {e}")
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
        print(f"'ùå Erreur assign_streets_to_team: {e}")
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
        print(f"'ùå Erreur set_status: {e}")
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
        print(f"'ùå Erreur add_note_for_address: {e}")
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
        print(f"'ùå Erreur get_street_addresses_with_notes: {e}")
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
        print(f"'ùå Erreur get_team_notes: {e}")
        return []


# =============================================================================
# STATISTIQUES ET RAPPORTS
# =============================================================================

def extended_stats() -> Dict[str, Any]:
    """Statistiques étendues de l'application"""
    try:
        from sqlalchemy import text
        with get_session() as session:
            q = text("""
                SELECT
                  COUNT(*) AS total,
                  SUM(CASE WHEN lower(status) IN ('done','terminee','terminée','complete','completed') THEN 1 ELSE 0 END) AS done,
                  SUM(CASE WHEN lower(status) IN ('en_cours','in_progress') THEN 1 ELSE 0 END) AS in_progress,
                  SUM(CASE WHEN lower(status) IN ('a_faire','à_faire','todo','to_do') THEN 1 ELSE 0 END) AS todo
                FROM streets
            """)
            row = session.execute(q).mappings().one()
            return {k: int((row.get(k) or 0)) for k in ("total","done","in_progress","todo")}
    except Exception:
        # TODO: log error
        return {"total": 0, "done": 0, "in_progress": 0, "todo": 0}


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
        print(f"'ùå Erreur stats_by_team: {e}")
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
        print(f"'ùå Erreur recent_activity: {e}")
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
        print(f"'ùå Erreur export_to_csv: {e}")
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
        print(f"'ùå Erreur log_activity: {e}")


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
        print(f"'ùå Erreur get_team_streets: {e}")
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
        print(f"'ùå Erreur get_unassigned_streets_count: {e}")
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
        print(f"'ùå Erreur get_sectors_list: {e}")
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
        print(f"'ùå Erreur bulk_assign_sector: {e}")
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
        print(f"'ùå Erreur get_assignations_export_data: {e}")
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
        print(f"'ùå Erreur export_notes_csv: {e}")
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
        print(f"'ùå Erreur import_addresses_from_cache: {e}")
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
        print(f"'ùå Erreur get_street_notes_for_team: {e}")
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

# =============================================================================
# EXPORT/IMPORT CSV POUR GESTIONNAIRES
# =============================================================================

def export_streets_template(include_assignments: bool = True):
    """Exporte les rues dans un format CSV standardisé pour les gestionnaires"""
    import pandas as pd
    from sqlalchemy import text
    try:
        with get_session() as session:
            rows = session.execute(text("SELECT name, sector, team, status FROM streets ORDER BY sector, name")).mappings().all()
        if not rows:
            df = pd.DataFrame(columns=["name","sector","team","status"])
        else:
            df = pd.DataFrame(rows, columns=["name","sector","team","status"])
        if not include_assignments:
            if "team" in df.columns:
                df["team"] = ""
            if "status" in df.columns:
                df["status"] = "a_faire"
        return df
    except Exception:
        # TODO: log error
        import pandas as pd
        return pd.DataFrame(columns=["name","sector","team","status"])

def upsert_streets_from_csv(file_like) -> dict:
    """Importe/met à jour les rues depuis un CSV (upsert par nom de rue)"""
    import pandas as pd
    from sqlalchemy import text
    
    def normalize_status(s: str) -> str:
        s = (s or "").strip().lower()
        if s in {"done","terminee","terminée","complete","completed"}:
            return "done"
        if s in {"en_cours","in_progress"}:
            return "en_cours"
        # par défaut on considère à faire
        return "a_faire"
    
    try:
        df = pd.read_csv(file_like)
        # normaliser les noms de colonnes
        rename_map = {c: c.strip().lower() for c in df.columns}
        df.columns = [rename_map[c] for c in df.columns]
        required = {"name","sector","team","status"}
        missing = required - set(df.columns)
        if missing:
            return {"inserted":0,"updated":0,"skipped":0,"errors":len(df)}  # tout rejeté car colonnes manquantes
        
        # nettoyage
        for col in ["name","sector","team","status"]:
            df[col] = df[col].fillna("").astype(str).map(lambda x: x.strip())
        df["status"] = df["status"].map(normalize_status)
        
        inserted = updated = skipped = errors = 0
        with get_session() as session:
            for _, row in df.iterrows():
                try:
                    name = row["name"]
                    if not name:
                        skipped += 1
                        continue
                    sector = row["sector"]
                    team = row["team"]
                    status = row["status"]
                    r = session.execute(text("SELECT 1 FROM streets WHERE name=:n"), {"n": name}).first()
                    if r:
                        session.execute(
                            text("UPDATE streets SET sector=:s, team=:t, status=:st WHERE name=:n"),
                            {"s": sector, "t": team, "st": status, "n": name},
                        )
                        updated += 1
                    else:
                        session.execute(
                            text("INSERT INTO streets (name, sector, team, status) VALUES (:n,:s,:t,:st)"),
                            {"n": name, "s": sector, "t": team, "st": status},
                        )
                        inserted += 1
                except Exception:
                    errors += 1
            session.commit()
        return {"inserted": inserted, "updated": updated, "skipped": skipped, "errors": errors}
    except Exception:
        # TODO: log error
        return {"inserted": 0, "updated": 0, "skipped": 0, "errors": 1}


# =============================================================================
# FONCTIONS DE GESTION DES ADRESSES
# =============================================================================

@db_retry(max_retries=3)
def ensure_addresses_table():
    """Crée la table addresses si elle n'existe pas"""
    try:
        with get_session() as session:
            # Vérifier si la table existe déjà
            existing = session.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='addresses'
            """)).fetchone()
            
            if existing:
                return True  # Table existe déjà
            
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS addresses (
                    id INTEGER PRIMARY KEY,
                    street_name TEXT NOT NULL,
                    house_number TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    osm_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(street_name, house_number)
                )
            """))
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_addresses_street 
                ON addresses(street_name)
            """))
            session.commit()
        return True
    except Exception:
        return False


@db_retry(max_retries=3)
def bulk_upsert_addresses_from_excel(path_or_buffer, sheet_name=None, chunk_size=1000):
    """
    Import massif d'adresses depuis Excel/CSV avec upsert portable
    
    Args:
        path_or_buffer: chemin vers fichier .xlsx/.csv ou buffer
        sheet_name: nom de feuille Excel (None = première feuille)
        chunk_size: taille des paquets pour commit
    
    Returns:
        dict: {"inserted": int, "updated": int, "skipped": int, "errors": int}
    """
    try:
        ensure_addresses_table()
        
        # Lecture du fichier
        try:
            if str(path_or_buffer).lower().endswith(('.xlsx', '.xls')):
                df_or_dict = pd.read_excel(path_or_buffer, sheet_name=sheet_name, engine="openpyxl")
                # Si sheet_name=None, pandas retourne un dict, prendre la première feuille
                if isinstance(df_or_dict, dict):
                    df = list(df_or_dict.values())[0]
                else:
                    df = df_or_dict
            else:
                df = pd.read_csv(path_or_buffer)
        except Exception:
            return {"inserted": 0, "updated": 0, "skipped": 0, "errors": 1}
        
        if df.empty:
            return {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}
        
        # Mapping colonnes (case-insensitive)
        col_map = {}
        df_cols = [c.lower().strip() for c in df.columns]
        
        # street_name
        for candidate in ["street", "rue", "nom_rue", "street_name", "nomrue"]:
            if candidate in df_cols:
                col_map["street_name"] = df.columns[df_cols.index(candidate)]
                break
        
        # civic_no
        for candidate in ["civic", "civique", "numero", "no", "civic_no", "civic_number", "nociv"]:
            if candidate in df_cols:
                col_map["civic_no"] = df.columns[df_cols.index(candidate)]
                break
        
        # sector (optionnel)
        for candidate in ["sector", "secteur"]:
            if candidate in df_cols:
                col_map["sector"] = df.columns[df_cols.index(candidate)]
                break
        
        # lat (optionnel)
        for candidate in ["lat", "latitude"]:
            if candidate in df_cols:
                col_map["lat"] = df.columns[df_cols.index(candidate)]
                break
        
        # lon (optionnel)
        for candidate in ["lon", "lng", "longitude"]:
            if candidate in df_cols:
                col_map["lon"] = df.columns[df_cols.index(candidate)]
                break
        
        if "street_name" not in col_map or "civic_no" not in col_map:
            return {"inserted": 0, "updated": 0, "skipped": 0, "errors": 1}
        
        inserted = updated = skipped = errors = 0
        
        with get_session() as session:
            for i in range(0, len(df), chunk_size):
                chunk = df.iloc[i:i+chunk_size]
                
                for _, row in chunk.iterrows():
                    try:
                        # Normalisation
                        street_name = str(row[col_map["street_name"]]).strip()
                        house_number = str(row[col_map["civic_no"]]).strip()
                        
                        # Supprimer .0 si Excel a converti en float
                        if house_number.endswith('.0') and house_number[:-2].isdigit():
                            house_number = house_number[:-2]
                        
                        if not street_name or not house_number or street_name.lower() in ['nan', 'null']:
                            skipped += 1
                            continue
                        
                        # Données optionnelles
                        sector = str(row.get(col_map.get("sector", ""), "")).strip() or None
                        if sector and sector.lower() in ['nan', 'null']:
                            sector = None
                        
                        latitude = longitude = None
                        if "lat" in col_map:
                            try:
                                latitude = float(row[col_map["lat"]])
                            except (ValueError, TypeError):
                                latitude = None
                        
                        if "lon" in col_map:
                            try:
                                longitude = float(row[col_map["lon"]])
                            except (ValueError, TypeError):
                                longitude = None
                        
                        # Upsert portable (SELECT puis UPDATE/INSERT)
                        existing = session.execute(
                            text("SELECT id FROM addresses WHERE street_name = :sn AND house_number = :hn"),
                            {"sn": street_name, "hn": house_number}
                        ).fetchone()
                        
                        if existing:
                            session.execute(
                                text("""UPDATE addresses SET latitude = :lat, longitude = :lon 
                                        WHERE street_name = :sn AND house_number = :hn"""),
                                {"lat": latitude, "lon": longitude, "sn": street_name, "hn": house_number}
                            )
                            updated += 1
                        else:
                            session.execute(
                                text("""INSERT INTO addresses (street_name, house_number, latitude, longitude) 
                                        VALUES (:sn, :hn, :lat, :lon)"""),
                                {"sn": street_name, "hn": house_number, "lat": latitude, "lon": longitude}
                            )
                            inserted += 1
                    
                    except Exception:
                        errors += 1
                
                # Commit par paquet
                session.commit()
        
        return {"inserted": inserted, "updated": updated, "skipped": skipped, "errors": errors}
    
    except Exception:
        return {"inserted": 0, "updated": 0, "skipped": 0, "errors": 1}


@db_retry(max_retries=3)
def count_addresses_by_street():
    """
    Compte les adresses par rue
    
    Returns:
        dict[str, int]: {nom_rue: nombre_adresses}
    """
    try:
        with get_session() as session:
            result = session.execute(
                text("SELECT street_name, COUNT(*) as count FROM addresses GROUP BY street_name ORDER BY street_name")
            ).fetchall()
            return {row[0]: row[1] for row in result}
    except Exception:
        return {}


def get_addresses_by_street(street_name: str) -> list[dict]:
    """Retourne les adresses (house_number, lat/lon) pour une rue donnée."""
    try:
        ensure_addresses_table()
        with get_session() as session:
            rows = session.execute(
                text("SELECT house_number, latitude, longitude FROM addresses WHERE street_name = :s"),
                {"s": street_name},
            ).all()
        
        # tri naturel (ex.: 9, 10, 10A, 11)
        import re
        def natkey(s: str):
            parts = re.findall(r"\d+|\D+", str(s or ""))
            return [int(p) if p.isdigit() else p for p in parts]
        
        out = [{"house_number": r[0], "latitude": r[1], "longitude": r[2]} for r in rows]
        out.sort(key=lambda d: natkey(d["house_number"]))
        return out
    except Exception:
        return []


# =============================================================================
# GESTION DES MOTS DE PASSE ÉQUIPES
# =============================================================================

def update_team_password(team_id: str, new_password: str) -> bool:
    """Met à jour le mot de passe (hashé) pour l'équipe."""
    if not team_id or not new_password or len(new_password.strip()) < 4:
        return False
    try:
        with get_session() as session:
            # Vérifier que l'équipe existe
            exists = session.execute(text("SELECT 1 FROM teams WHERE id=:id"), {"id": team_id}).fetchone()
            if not exists:
                return False
            
            cols = [r[1] for r in session.execute(text("PRAGMA table_info(teams)")).fetchall()]
            target = "password_hash" if "password_hash" in cols else ("password" if "password" in cols else None)
            if not target:
                return False
                
            hashed = hash_password(new_password)
            session.execute(text(f"UPDATE teams SET {target}=:p WHERE id=:id"), {"p": hashed, "id": team_id})
            session.commit()
            # Vérifie si l'update a fonctionné en relisant
            check = session.execute(text("SELECT 1 FROM teams WHERE id=:id"), {"id": team_id}).fetchone()
            return check is not None
    except Exception:
        return False


def reset_team_password(team_id: str, length: int = 12) -> str:
    """Réinitialise et retourne le nouveau mot de passe en clair (à montrer une seule fois)."""
    if not team_id or length < 4:
        return ""
    try:
        import secrets
        import string
        # longueur sécurisée, au moins 8 caractères
        safe_length = max(8, min(length, 32))
        # Combine lettres, chiffres pour lisibilité terrain
        chars = string.ascii_letters + string.digits
        clear = ''.join(secrets.choice(chars) for _ in range(safe_length))
        return clear if update_team_password(team_id, clear) else ""
    except Exception:
        return ""


def get_teams_list() -> list[tuple]:
    """Récupère la liste des équipes (id, name)"""
    try:
        with get_session() as session:
            result = session.execute(text("SELECT id, name FROM teams WHERE active = 1 ORDER BY id"))
            return [(row[0], row[1]) for row in result]
    except Exception:
        return []


def count_hash_algorithms(conn=None) -> dict:
    """
    Compte les algorithmes de hash utilisés par les équipes
    Utile pour suivre la progression de la migration
    
    Args:
        conn: Connection DB optionnelle (utilise get_session() si None)
    """
    try:
        from src.auth.passwords import detect_hash_algo
        
        with get_session() as session:
            result = session.execute(text("SELECT password_hash FROM teams WHERE active = 1 AND password_hash IS NOT NULL"))
            
            counts = {"argon2": 0, "bcrypt": 0, "sha256": 0, "md5": 0, "pbkdf2_sha256": 0, "other": 0, "empty": 0}
            
            for row in result:
                hash_value = row[0] or ""
                algo = detect_hash_algo(hash_value)
                if algo in counts:
                    counts[algo] += 1
                else:
                    counts["other"] += 1
            
            # Compter aussi les équipes avec des mots de passe en clair ou vides
            empty_hash_result = session.execute(text("SELECT COUNT(*) FROM teams WHERE active = 1 AND (password_hash IS NULL OR password_hash = '')"))
            counts["empty"] = empty_hash_result.scalar() or 0
            
            return counts
            
    except Exception as e:
        print(f"Erreur count_hash_algorithms: {e}")
        return {"error": str(e)}