"""
GuignoMap - Database operations (SQLite Pure)
Unified database layer for GuignoMap
"""
import sqlite3
from pathlib import Path
import threading
from contextlib import contextmanager
from datetime import datetime
import pandas as pd
from typing import Optional, List, Dict, Any
import functools

from guignomap.auth import hash_password, verify_password
from guignomap.backup import auto_backup_before_critical, BackupManager
from guignomap.validators import validate_and_clean_input, InputValidator

# Flag d'initialisation globale
_DB_INITIALIZED = False
_DB_LOCK = threading.Lock()


# =============================================================================
# CACHE SYSTEM
# =============================================================================

def safe_cache(func):
    """Décorateur de cache compatible Streamlit/standalone"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Essayer d'utiliser st.cache_data si Streamlit est disponible
            import streamlit as st
            cached_func = st.cache_data(func)
            return cached_func(*args, **kwargs)
        except ImportError:
            # Fallback : cache simple en mémoire
            if not hasattr(wrapper, '_cache'):
                wrapper._cache = {}
            
            # Créer une clé de cache simple
            cache_key = str(args) + str(sorted(kwargs.items()))
            
            if cache_key in wrapper._cache:
                return wrapper._cache[cache_key]
            
            result = func(*args, **kwargs)
            wrapper._cache[cache_key] = result
            return result
    return wrapper


# =============================================================================
# CONNECTION MANAGEMENT
# =============================================================================

DB_PATH = Path("guignomap/guigno_map.db")
_local = threading.local()

def vacuum_database():
    """Maintenance de la base de données"""
    with get_conn() as conn:
        conn.execute("VACUUM")
        conn.execute("PRAGMA optimize")
        conn.execute("PRAGMA analysis_limit=1000")
        conn.execute("PRAGMA optimize")

def get_conn():
    """Connexion SQLite thread-safe avec optimisations"""
    global _DB_INITIALIZED
    
    if not hasattr(_local, 'conn') or _local.conn is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        _local.conn = sqlite3.connect(
            DB_PATH, 
            check_same_thread=False,
            timeout=30.0
        )
        _local.conn.row_factory = sqlite3.Row
        # Optimisations SQLite pour performance 1000+ équipes
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        _local.conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        _local.conn.execute("PRAGMA foreign_keys=ON")
        _local.conn.execute("PRAGMA temp_store=MEMORY")
        _local.conn.execute("PRAGMA optimize")  # Auto-optimisation
        
        # Initialisation exactement UNE FOIS
        with _DB_LOCK:
            if not _DB_INITIALIZED:
                initialize_database()
                _DB_INITIALIZED = True
                
    return _local.conn

@contextmanager
def get_cursor():
    """Context manager pour cursor avec auto-commit"""
    conn = get_conn()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


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

def create_performance_indexes(conn=None):
    """Crée les INDEX pour optimiser les performances"""
    if conn is None:
        conn = get_conn()
    
    indexes = [
        # INDEX pour les requêtes fréquentes sur streets
        "CREATE INDEX IF NOT EXISTS idx_streets_team ON streets(team)",
        "CREATE INDEX IF NOT EXISTS idx_streets_status ON streets(status)", 
        "CREATE INDEX IF NOT EXISTS idx_streets_name ON streets(name)",
        "CREATE INDEX IF NOT EXISTS idx_streets_sector ON streets(sector)",
        
        # INDEX pour les requêtes fréquentes sur notes (street_name, pas street_id)
        "CREATE INDEX IF NOT EXISTS idx_notes_street_name ON notes(street_name)",
        "CREATE INDEX IF NOT EXISTS idx_notes_team_id ON notes(team_id)",
        "CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at DESC)",
        
        # INDEX pour teams 
        "CREATE INDEX IF NOT EXISTS idx_teams_name ON teams(name)",
        
        # INDEX pour activity_log (si elle existe)
        "CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_activity_team ON activity_log(team_id)",
    ]
    
    for index_sql in indexes:
        try:
            conn.execute(index_sql)
        except Exception as e:
            print(f"Warning: Could not create index: {e}")

def initialize_database():
    """Initialise la base de données avec les données par défaut"""
    try:
        with get_conn() as conn:
            _ensure_foreign_keys(conn)
            
            # Création des INDEX pour optimiser les performances
            create_performance_indexes(conn)
            
            # Vérifier si l'admin existe
            admin_exists = conn.execute(
                "SELECT COUNT(*) FROM teams WHERE id = 'ADMIN'"
            ).fetchone()[0]
            
            if admin_exists == 0:
                # Créer l'équipe ADMIN avec mot de passe RELAIS2025
                admin_password_hash = hash_password("RELAIS2025")
                conn.execute("""
                    INSERT INTO teams(id, name, password_hash) 
                    VALUES ('ADMIN', 'Administrateur', ?)
                """, (admin_password_hash,))
                
                # Vérifier si des rues existent
                street_count = conn.execute("SELECT COUNT(*) FROM streets").fetchone()[0]
                
                conn.commit()
                return {
                    "status": "initialized", 
                    "message": f"Admin créé avec mot de passe RELAIS2025, {street_count} rues existantes"
                }
            else:
                # Admin existe déjà, vérifier le mot de passe
                current_hash = conn.execute(
                    "SELECT password_hash FROM teams WHERE id = 'ADMIN'"
                ).fetchone()[0]
                
                expected_hash = hash_password("RELAIS2025")
                if current_hash != expected_hash:
                    # Mise à jour du mot de passe
                    conn.execute(
                        "UPDATE teams SET password_hash = ? WHERE id = 'ADMIN'",
                        (expected_hash,)
                    )
                    conn.commit()
                    return {"status": "admin_password_updated", "message": "Mot de passe ADMIN mis à jour"}
                else:
                    return {"status": "already_initialized", "message": "Base déjà initialisée, ADMIN OK"}
                    
    except Exception as e:
        return {"status": "error", "message": str(e)}


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
                INSERT INTO teams(id, name, password_hash) 
                VALUES (?, ?, ?)
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
                "SELECT name, password_hash FROM teams WHERE id = ?",
                (team_id,)
            ).fetchone()
            
            if not result:
                return {"success": False, "message": "Équipe introuvable"}
            
            name, password_hash = result
            is_admin = team_id == 'ADMIN'  # ADMIN is admin by definition
            
            if not password_hash:  # Pas de mot de passe
                return {"success": True, "team_name": name, "is_admin": is_admin}
            
            if verify_password(password, password_hash):
                return {"success": True, "team_name": name, "is_admin": is_admin}
            else:
                return {"success": False, "message": "Mot de passe incorrect"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@safe_cache
def list_teams() -> List[Dict]:
    """Liste toutes les équipes"""
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT t.id, t.name, t.active, 
                   COUNT(s.id) as assigned_streets
            FROM teams t
            LEFT JOIN streets s ON t.id = s.team
            GROUP BY t.id, t.name, t.active
            ORDER BY t.name
        """)
        return _row_dicts(cur)


# =============================================================================
# STREET OPERATIONS
# =============================================================================

@safe_cache
def list_streets(team: Optional[str] = None) -> pd.DataFrame:
    """Liste toutes les rues avec leurs détails"""
    with get_conn() as conn:
        if team:
            cur = conn.execute("""
                SELECT s.id, s.name, s.sector, s.status, s.team_id,
                       t.nom as team_name,
                       COUNT(n.id) as notes_count
                FROM streets s
                LEFT JOIN teams t ON s.team_id = t.id
                LEFT JOIN notes n ON s.id = n.street_id
                WHERE s.team_id = ?
                GROUP BY s.id, s.name, s.sector, s.status, s.team_id, t.nom
                ORDER BY s.name
            """, (team,))
        else:
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

def update_street_status(street_id: int, new_status: str, team_id: Optional[str] = None) -> dict:
    """Met à jour le statut d'une rue de façon robuste"""
    # Validation stricte des statuts autorisés (selon contrainte DB)
    valid_statuses = {"a_faire", "en_cours", "terminee"}
    if new_status not in valid_statuses:
        raise ValueError(f"Statut invalide '{new_status}'. Statuts autorisés: {valid_statuses}")
    
    with get_conn() as conn:
        _ensure_foreign_keys(conn)
        
        # UPDATE en un seul passage selon la présence de team_id
        if team_id:
            cursor = conn.execute("""
                UPDATE streets 
                SET status = ?, team = ?
                WHERE id = ?
            """, (new_status, team_id, street_id))
        else:
            cursor = conn.execute("""
                UPDATE streets 
                SET status = ?
                WHERE id = ?
            """, (new_status, street_id))
        
        # Vérifier que la rue existe (rowcount == 0 si id inexistant)
        if cursor.rowcount == 0:
            raise ValueError(f"Rue avec l'id {street_id} introuvable")
        
        conn.commit()
        return {"id": street_id, "status": new_status, "team": team_id}


# =============================================================================
# STATISTICS & REPORTING
# =============================================================================

@safe_cache
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
                    SET team_id = ?
                    WHERE sector = ? AND (team_id IS NULL OR team_id = '')
                """, (team_id, sector))
            else:
                cur = conn.execute("""
                    UPDATE streets 
                    SET team_id = ?
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


# =============================================================================
# UTILITY QUERY FUNCTIONS (Legacy compatibility)
# =============================================================================

def execute_query(query, params=None):
    """Exécute une query avec gestion d'erreurs (legacy compatibility)"""
    with get_cursor() as cursor:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()

def fetchone_query(query, params=None):
    """Exécute une query et retourne le premier résultat"""
    conn = get_conn()
    if params:
        result = conn.execute(query, params).fetchone()
    else:
        result = conn.execute(query).fetchone()
    return result

def fetchall_query(query, params=None):
    """Exécute une query et retourne tous les résultats"""
    conn = get_conn()
    if params:
        results = conn.execute(query, params).fetchall()
    else:
        results = conn.execute(query).fetchall()
    return results


# =============================================================================
# ALIAS & COMPATIBILITY FUNCTIONS
# =============================================================================

# Alias pour compatibilité avec l'ancienne API
init_db = initialize_database
verify_team = authenticate_team

def teams() -> List[str]:
    """Retourne la liste des noms d'équipes (compatibilité)"""
    teams_list = list_teams()
    return [team['name'] for team in teams_list if team['id'] != 'ADMIN']

def get_teams_list() -> List[tuple]:
    """Retourne liste des équipes sous forme (id, nom)"""
    teams_list = list_teams()
    return [(team['id'], team['name']) for team in teams_list]
    return [(team['id'], team['nom']) for team in teams_list if team['id'] != 'ADMIN']

def get_all_teams() -> pd.DataFrame:
    """Retourne DataFrame des équipes"""
    teams_list = list_teams()
    return pd.DataFrame(teams_list)

def set_status(street_name: str, status: str) -> bool:
    """Met à jour le statut d'une rue par nom (legacy)"""
    with get_conn() as conn:
        cur = conn.execute("SELECT id FROM streets WHERE name = ?", (street_name,))
        result = cur.fetchone()
        if result:
            try:
                update_street_status(result[0], status)
                return True
            except ValueError:
                return False
        return False

def get_unassigned_streets() -> List[Dict]:
    """Rues non assignées"""
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT id, name, sector FROM streets 
            WHERE team_id IS NULL OR team_id = ''
            ORDER BY name
        """)
        return _row_dicts(cur)

def get_unassigned_streets_count() -> int:
    """Nombre de rues non assignées"""
    with get_conn() as conn:
        count = conn.execute("""
            SELECT COUNT(*) FROM streets 
            WHERE team_id IS NULL OR team_id = ''
        """).fetchone()[0]
        return count

@safe_cache
def get_sectors_list() -> List[str]:
    """Liste des secteurs"""
    with get_conn() as conn:
        cur = conn.execute("SELECT DISTINCT sector FROM streets WHERE sector IS NOT NULL ORDER BY sector")
        return [row[0] for row in cur.fetchall()]

def assign_streets_to_team(street_names: List[str], team_id: str) -> int:
    """Assigne des rues à une équipe"""
    count = 0
    with get_conn() as conn:
        _ensure_foreign_keys(conn)
        for street_name in street_names:
            cur = conn.execute("""
                UPDATE streets SET team_id = ?
                WHERE name = ?
            """, (team_id, street_name))
            count += cur.rowcount
        conn.commit()
    return count

def bulk_assign_sector(sector: str, team_id: str) -> int:
    """Assigne toutes les rues d'un secteur à une équipe"""
    result = bulk_assign_streets(team_id, sector)
    return result.get("affected_count", 0)

def get_team_streets(team_id: str) -> List[Dict]:
    """Rues assignées à une équipe"""
    df = list_streets(team=team_id)
    return df.to_dict('records')

def add_street_note(street_name: str, team_id: str, address_num: str, content: str) -> bool:
    """Ajoute une note à une rue par nom"""
    with get_conn() as conn:
        cur = conn.execute("SELECT id FROM streets WHERE name = ?", (street_name,))
        result = cur.fetchone()
        if result:
            return add_note(result[0], team_id, f"{address_num}: {content}")
        return False

def get_street_notes_for_team(street_name: str, team_id: str) -> List[Dict]:
    """Notes d'une rue pour une équipe"""
    with get_conn() as conn:
        cur = conn.execute("""
            SELECT n.*, t.nom as team_name
            FROM notes n
            LEFT JOIN teams t ON n.team_id = t.id
            LEFT JOIN streets s ON n.street_id = s.id
            WHERE s.name = ? AND n.team_id = ?
            ORDER BY n.created_at DESC
        """, (street_name, team_id))
        return _row_dicts(cur)

# Fonctions export (placeholders pour l'instant)
def export_to_csv():
    """Export CSV placeholder"""
    return "CSV export placeholder"

def export_notes_csv():
    """Export notes CSV placeholder"""
    return "Notes CSV export placeholder"

def export_streets_template(include_assignments=True):
    """Export template placeholder"""
    return pd.DataFrame()

def upsert_streets_from_csv(file_like):
    """Import CSV placeholder"""
    return {"success": False, "message": "Import not implemented"}

def get_assignations_export_data():
    """Export assignations placeholder"""
    return []

# Fonctions adresses (placeholders)
def get_street_addresses_with_notes(street_name):
    """Placeholder adresses avec notes"""
    return []

def get_addresses_by_street(street_name):
    """Placeholder adresses par rue"""
    return []

def add_note_for_address(street_name, team_id, address_num, content):
    """Placeholder note pour adresse"""
    return False

def get_team_notes(team_id):
    """Placeholder notes équipe"""
    return []

def update_team_password(team_id, new_password):
    """Met à jour le mot de passe d'une équipe"""
    try:
        with get_conn() as conn:
            password_hash = hash_password(new_password)
            conn.execute("""
                UPDATE teams SET password_hash = ? WHERE id = ?
            """, (password_hash, team_id))
            conn.commit()
            return True
    except Exception:
        return False

def reset_team_password(team_id):
    """Remet à zéro le mot de passe d'une équipe"""
    try:
        with get_conn() as conn:
            conn.execute("""
                UPDATE teams SET password_hash = '' WHERE id = ?
            """, (team_id,))
            conn.commit()
            return "password_reset"
    except Exception:
        return None

def import_addresses_from_cache(cache_data):
    """Import adresses depuis cache"""
    return 0

def get_backup_manager():
    """Retourne backup manager"""
    return BackupManager(str(DB_PATH))


# =============================================================================
# CACHE MANAGEMENT
# =============================================================================

def invalidate_caches():
    """Invalide tous les caches (Streamlit et fallback mémoire)"""
    try:
        # Si Streamlit est disponible, utiliser son système de cache
        import streamlit as st
        st.cache_data.clear()
    except ImportError:
        # Fallback : nettoyer les caches mémoire des fonctions @safe_cache
        import inspect
        
        # Parcourir toutes les fonctions du module actuel
        current_module = inspect.getmodule(invalidate_caches)
        for name, obj in inspect.getmembers(current_module):
            if callable(obj) and hasattr(obj, '_cache'):
                obj._cache.clear()


# =============================================================================
# ADDRESSES (import et lecture/assignation)
# =============================================================================

def assign_addresses_to_team(address_ids, team_id):
    """Assigne une liste d'adresses à une équipe (team_id) - retourne nb lignes affectées"""
    if not address_ids:
        return 0
    with get_conn() as conn:
        cursor = conn.cursor()
        placeholders = ','.join('?' for _ in address_ids)
        cursor.execute(f"""
            UPDATE addresses
            SET assigned_to = ?
            WHERE id IN ({placeholders})
        """, [str(team_id).strip()] + [int(aid) for aid in address_ids])
        conn.commit()
        rowcount = cursor.rowcount
        invalidate_caches()
        return rowcount

def get_unassigned_addresses(limit=500, offset=0, street_filter=None, sector=None):
    """Adresses non assignées, triées Rue + numéro avec pagination et filtres"""
    with get_conn() as conn:
        where_conditions = ["(assigned_to IS NULL OR assigned_to = '')"]
        params = []
        
        if street_filter:
            where_conditions.append("street_name LIKE ?")
            params.append(f"%{str(street_filter).strip()}%")
        
        if sector:
            where_conditions.append("sector = ?")
            params.append(str(sector).strip())
        
        where_clause = " AND ".join(where_conditions)
        params.extend([limit, offset])
        
        return pd.read_sql_query(f"""
            SELECT id, street_name, house_number, sector
            FROM addresses
            WHERE {where_clause}
            ORDER BY street_name ASC, CAST(house_number AS INTEGER) ASC NULLS LAST
            LIMIT ? OFFSET ?
        """, conn, params=params)

def get_team_addresses(team_id, limit=500, offset=0):
    """Adresses assignées à une équipe avec pagination"""
    with get_conn() as conn:
        return pd.read_sql_query("""
            SELECT id, street_name, house_number, postal_code, sector, assigned_to
            FROM addresses
            WHERE assigned_to = ?
            ORDER BY street_name ASC, CAST(house_number AS INTEGER) ASC NULLS LAST
            LIMIT ? OFFSET ?
        """, conn, params=(str(team_id).strip(), limit, offset))