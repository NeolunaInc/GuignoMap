"""
Connexion SQLite pure pour GuignoMap - Sans SQLAlchemy
Thread-safe avec optimisations WAL et connection pooling simple
"""
import sqlite3
from pathlib import Path
import threading
from contextlib import contextmanager
import time

DB_PATH = Path("guignomap/guigno_map.db")
_local = threading.local()

def get_conn():
    """Connexion SQLite thread-safe avec optimisations"""
    if not hasattr(_local, 'conn') or _local.conn is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        _local.conn = sqlite3.connect(
            DB_PATH, 
            check_same_thread=False,
            timeout=30.0
        )
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
        _local.conn.execute("PRAGMA temp_store=MEMORY")
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

def execute_query(query, params=None):
    """Exécute une query avec gestion d'erreurs"""
    with get_cursor() as cursor:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchall()

def execute_single(query, params=None):
    """Exécute une query et retourne un seul résultat"""
    with get_cursor() as cursor:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.fetchone()

def execute_write(query, params=None):
    """Exécute une query d'écriture (INSERT/UPDATE/DELETE)"""
    with get_cursor() as cursor:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor.lastrowid

def test_connection():
    """Test simple de connexion"""
    try:
        result = execute_single("SELECT 1 as test, datetime('now') as now")
        print(f"✅ SQLite connexion OK - Test: {result['test']}, Time: {result['now']}")
        return True
    except Exception as e:
        print(f"❌ SQLite connexion failed: {e}")
        return False

def close_connection():
    """Ferme la connexion thread-local"""
    if hasattr(_local, 'conn') and _local.conn:
        _local.conn.close()
        _local.conn = None