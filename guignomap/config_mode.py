"""
GuignoMap - Configuration des modes d'exécution
Gère les modes demo/client avec fallback intelligent
"""
import os
import logging
from pathlib import Path
import sqlite3

# Détection du mode
def _get_mode():
    """Détermine le mode d'exécution depuis Streamlit secrets ou env vars"""
    try:
        import streamlit as st
        return st.secrets.get("MODE", "demo")
    except Exception:
        return os.environ.get("GUIGNOMAP_MODE", "demo")

MODE = _get_mode()

def is_demo():
    """Returns True si en mode démo"""
    return MODE == "demo"

def ensure_db_path():
    """
    Détermine le chemin de la DB selon le mode:
    - client: exige guigno_map.db présent
    - demo: fallback guigno_map.db -> guigno_map.sample.db -> création minimale
    """
    if MODE == "client":
        # Mode client: DB principale requise
        db_path = Path("guignomap/guigno_map.db")
        if not db_path.exists():
            raise FileNotFoundError(
                f"Mode client requiert la base de données {db_path}. "
                "Importez vos données ou basculez en mode demo."
            )
        return db_path
    
    elif MODE == "demo":
        # Mode démo: fallback intelligent
        primary_db = Path("guignomap/guigno_map.db")
        sample_db = Path("guignomap/guigno_map.sample.db")
        
        if primary_db.exists():
            logging.info(f"Mode démo: utilisation DB principale {primary_db}")
            return primary_db
        
        if sample_db.exists():
            logging.info(f"Mode démo: utilisation DB échantillon {sample_db}")
            return sample_db
        
        # Créer une DB minimale pour démo
        logging.warning(f"Mode démo: création DB minimale {sample_db}")
        _create_minimal_demo_db(sample_db)
        return sample_db
    
    else:
        raise ValueError(f"Mode '{MODE}' non supporté. Utilisez 'demo' ou 'client'.")

def _create_minimal_demo_db(db_path):
    """Crée une base de données minimale pour la démo"""
    db_path.parent.mkdir(exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        # Table teams
        conn.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT 1
            )
        """)
        
        # Table streets
        conn.execute("""
            CREATE TABLE IF NOT EXISTS streets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sector TEXT,
                team TEXT,
                status TEXT NOT NULL DEFAULT 'a_faire' 
                    CHECK (status IN ('a_faire', 'en_cours', 'terminee'))
            )
        """)
        
        # Table addresses
        conn.execute("""
            CREATE TABLE IF NOT EXISTS addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                street_name TEXT NOT NULL,
                house_number TEXT,
                sector TEXT,
                latitude REAL,
                longitude REAL,
                team TEXT,
                addr_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (street_name) REFERENCES streets(name)
            )
        """)
        
        # Table notes
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                street_name TEXT NOT NULL,
                team_id TEXT NOT NULL,
                address_number TEXT,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (street_name) REFERENCES streets(name),
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
        """)
        
        # Équipe admin par défaut
        conn.execute("""
            INSERT OR IGNORE INTO teams (id, name, password_hash) 
            VALUES ('ADMIN', 'Administrateur', '$2b$12$demo.hash.for.admin.access')
        """)
        
        # Quelques rues de démo
        demo_streets = [
            ("Rue de la Démo", "Centre", None, "a_faire"),
            ("Avenue Exemple", "Nord", None, "a_faire"), 
            ("Boulevard Test", "Sud", None, "a_faire")
        ]
        
        conn.executemany("""
            INSERT OR IGNORE INTO streets (name, sector, team, status) 
            VALUES (?, ?, ?, ?)
        """, demo_streets)
        
        conn.commit()
        logging.info(f"DB démo créée avec {len(demo_streets)} rues échantillon")

# Log du mode choisi à l'import
logging.info(f"GuignoMap démarré en mode: {MODE}")