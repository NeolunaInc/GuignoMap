"""
Connexion PostgreSQL avec SQLAlchemy pour GuignoMap v5.0
Engine + QueuePool + cache Streamlit + retry logic
"""
import time
import functools
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from src.config import get_database_url, get_database_pool_config


def db_retry(max_retries=3, backoff_factor=1):
    """
    Décorateur retry exponentiel pour opérations DB critiques
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except SQLAlchemyError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor * (2 ** attempt)
                        print(f"Retry DB operation {func.__name__} in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        print(f"Max retries reached for {func.__name__}")
                        break
            raise last_exception
        return wrapper
    return decorator


@st.cache_resource
def get_engine():
    """
    Engine PostgreSQL avec cache Streamlit et configuration pool
    Conformément au plan v5.0
    """
    database_url = get_database_url()
    pool_config = get_database_pool_config()
    
    # Configuration PostgreSQL avec QueuePool
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=pool_config["pool_size"],
        max_overflow=pool_config["max_overflow"],
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False  # Set to True for SQL debugging
    )
    
    return engine


def get_session():
    """Fabrique de session SQLAlchemy"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


@db_retry(max_retries=3)
def test_connection():
    """Test de connexion à la base PostgreSQL"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            return result.fetchone()[0] == 1
    except Exception as e:
        print(f"Erreur test connexion DB: {e}")
        return False


@db_retry(max_retries=3)
def execute_query(query, params=None):
    """
    Exécution de requête avec retry automatique
    Pour transition progressive vers SQLAlchemy
    """
    engine = get_engine()
    with engine.connect() as conn:
        if params:
            return conn.execute(text(query), params)
        else:
            return conn.execute(text(query))


@db_retry(max_retries=3)  
def execute_transaction(queries_and_params):
    """
    Exécution de transaction multi-requêtes avec retry
    queries_and_params: liste de tuples (query, params)
    """
    engine = get_engine()
    with engine.begin() as conn:
        results = []
        for query, params in queries_and_params:
            if params:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))
            results.append(result)
        return results


# Wrapper facultatif pour compatibilité avec l'ancien code/patrons
def get_session_factory():
    """Retourne un callable qui ouvre une session (usage: with Session() as s: ...)."""
    def _open():
        return get_session().__enter__()  # pour compat avec 'with Session() as s'
    # pour permettre 'with Session() as s', on expose un objet qui supporte __call__ et __enter__/__exit__
    class _Factory:
        def __call__(self):
            return get_session().__enter__()
        def __enter__(self):
            return get_session().__enter__()
        def __exit__(self, exc_type, exc, tb):
            return get_session().__exit__(exc_type, exc, tb)
    return _Factory()