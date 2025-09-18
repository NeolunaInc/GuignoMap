"""
Connexion SQLite pure pour GuignoMap - Remplacement de l'ancien système PostgreSQL/SQLAlchemy
Compatibilité avec l'API existante pour transition en douceur
"""
import time
import functools
from pathlib import Path
from .sqlite_pure import (
    get_conn, get_cursor, execute_query, execute_single, 
    execute_write, test_connection as sqlite_test_connection
)

def db_retry(max_retries=3, backoff_factor=1):
    """
    Décorateur retry pour compatibilité avec l'ancien code
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        print(f"Retry DB operation {func.__name__} in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        print(f"Max retries reached for {func.__name__}")
                        break
            
            if last_exception is not None:
                raise RuntimeError(f"Échec d'opération DB: {last_exception}") from last_exception
            else:
                raise RuntimeError(f"Échec d'opération DB pour {func.__name__}: raison inconnue")
        return wrapper
    return decorator

# Compatibilité API - ces fonctions remplacent les anciennes fonctions SQLAlchemy
def get_engine():
    """
    Compatibilité avec l'ancien code qui appelait get_engine()
    Retourne un objet simple qui peut être utilisé pour la compatibilité
    """
    class SQLiteEngine:
        def connect(self):
            return SQLiteConnection()
        
        @property
        def url(self):
            return f"sqlite:///{Path('guignomap/guigno_map.db').absolute()}"
    
    return SQLiteEngine()

class SQLiteConnection:
    """Wrapper de connexion pour compatibilité avec SQLAlchemy"""
    def __enter__(self):
        self.conn = get_conn()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
    
    def execute(self, query, params=None):
        """Exécute une requête - compatibilité SQLAlchemy"""
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return SQLiteResult(cursor)

class SQLiteResult:
    """Wrapper de résultats pour compatibilité SQLAlchemy"""
    def __init__(self, cursor):
        self.cursor = cursor
        self._rows = None
    
    def fetchone(self):
        return self.cursor.fetchone()
    
    def fetchall(self):
        if self._rows is None:
            self._rows = self.cursor.fetchall()
        return self._rows

def get_session():
    """
    Compatibilité avec l'ancien code SQLAlchemy
    Retourne un context manager pour les sessions
    """
    class SQLiteSession:
        def __enter__(self):
            self.conn = get_conn()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
        
        def execute(self, query, params=None):
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return SQLiteResult(cursor)
    
    return SQLiteSession()

@db_retry(max_retries=3)
def test_connection():
    """Test de connexion à la base SQLite"""
    return sqlite_test_connection()

# Fonctions compatibles avec l'ancienne API
def execute_query_compat(query, params=None):
    """Compatibilité avec l'ancien execute_query SQLAlchemy"""
    return execute_query(query, params)

def execute_transaction(queries_and_params):
    """
    Exécution de transaction multi-requêtes
    queries_and_params: liste de tuples (query, params)
    """
    with get_cursor() as cursor:
        results = []
        for query, params in queries_and_params:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results.append(cursor.fetchall())
        return results