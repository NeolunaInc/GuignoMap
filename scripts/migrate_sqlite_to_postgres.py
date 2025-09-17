"""
Script de migration SQLite ‚Üí PostgreSQL pour GuignoMap v5.0
Copie toutes les donn√©es existantes de SQLite vers PostgreSQL
"""
import sqlite3
import sys
import os
from pathlib import Path

# Ajouter le r√©pertoire parent au PYTHONPATH pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from src.database.connection import get_engine, execute_transaction
from src.database.models import Base, Street, Team, Note, ActivityLog, Address
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import pandas as pd


def get_sqlite_connection():
    """Connexion en lecture seule √† la base SQLite existante"""
    sqlite_path = Path(__file__).parent.parent / "guignomap" / "guigno_map.db"
    if not sqlite_path.exists():
        print(f"‚ùå Base SQLite non trouv√©e: {sqlite_path}")
        return None
    
    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    return conn


def create_postgres_tables():
    """Cr√©er les tables PostgreSQL via Alembic/SQLAlchemy"""
    try:
        engine = get_engine()
        Base.metadata.create_all(engine)
        print("‚úÖ Tables PostgreSQL cr√©√©es")
        return True
    except Exception as e:
        print(f"‚ùå Erreur cr√©ation tables PostgreSQL: {e}")
        return False


def copy_teams(sqlite_conn, postgres_session):
    """Copier les √©quipes SQLite ‚Üí PostgreSQL"""
    try:
        # Lire depuis SQLite
        teams_data = pd.read_sql_query("""
            SELECT id, name, password_hash, created_at, active 
            FROM teams 
            ORDER BY created_at
        """, sqlite_conn)
        
        if teams_data.empty:
            print("‚ÑπÔ∏è Aucune √©quipe √† migrer")
            return 0
        
        # Ins√©rer dans PostgreSQL
        count = 0
        for _, row in teams_data.iterrows():
            team = Team(
                id=row['id'],
                name=row['name'],
                password_hash=row['password_hash'],
                created_at=pd.to_datetime(row['created_at']) if row['created_at'] else datetime.utcnow(),
                active=bool(row['active'])
            )
            postgres_session.merge(team)  # merge pour √©viter les doublons
            count += 1
        
        postgres_session.commit()
        print(f"‚úÖ {count} √©quipes migr√©es")
        return count
        
    except Exception as e:
        postgres_session.rollback()
        print(f"‚ùå Erreur migration √©quipes: {e}")
        return 0


def copy_streets(sqlite_conn, postgres_session):
    """Copier les rues SQLite ‚Üí PostgreSQL"""
    try:
        # Lire depuis SQLite
        streets_data = pd.read_sql_query("""
            SELECT id, name, sector, team, status 
            FROM streets 
            ORDER BY id
        """, sqlite_conn)
        
        if streets_data.empty:
            print("‚ÑπÔ∏è Aucune rue √† migrer")
            return 0
        
        # Ins√©rer dans PostgreSQL
        count = 0
        for _, row in streets_data.iterrows():
            street = Street(
                id=row['id'] if row['id'] else None,
                name=row['name'],
                sector=row['sector'],
                team=row['team'],
                status=row['status'] or 'a_faire'
            )
            postgres_session.merge(street)
            count += 1
        
        postgres_session.commit()
        print(f"‚úÖ {count} rues migr√©es")
        return count
        
    except Exception as e:
        postgres_session.rollback()
        print(f"‚ùå Erreur migration rues: {e}")
        return 0


def copy_notes(sqlite_conn, postgres_session):
    """Copier les notes SQLite ‚Üí PostgreSQL"""
    try:
        # Lire depuis SQLite
        notes_data = pd.read_sql_query("""
            SELECT id, street_name, team_id, address_number, comment, created_at 
            FROM notes 
            ORDER BY created_at
        """, sqlite_conn)
        
        if notes_data.empty:
            print("‚ÑπÔ∏è Aucune note √† migrer")
            return 0
        
        # Ins√©rer dans PostgreSQL
        count = 0
        for _, row in notes_data.iterrows():
            note = Note(
                id=row['id'] if row['id'] else None,
                street_name=row['street_name'],
                team_id=row['team_id'],
                address_number=row['address_number'],
                comment=row['comment'],
                created_at=pd.to_datetime(row['created_at']) if row['created_at'] else datetime.utcnow()
            )
            postgres_session.merge(note)
            count += 1
        
        postgres_session.commit()
        print(f"‚úÖ {count} notes migr√©es")
        return count
        
    except Exception as e:
        postgres_session.rollback()
        print(f"‚ùå Erreur migration notes: {e}")
        return 0


def copy_activity_logs(sqlite_conn, postgres_session):
    """Copier les logs d'activit√© SQLite ‚Üí PostgreSQL"""
    try:
        # V√©rifier si la table existe
        cursor = sqlite_conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='activity_log'
        """)
        if not cursor.fetchone():
            print("‚ÑπÔ∏è Table activity_log non pr√©sente dans SQLite")
            return 0
        
        # Lire depuis SQLite
        logs_data = pd.read_sql_query("""
            SELECT id, team_id, action, details, created_at 
            FROM activity_log 
            ORDER BY created_at
        """, sqlite_conn)
        
        if logs_data.empty:
            print("‚ÑπÔ∏è Aucun log d'activit√© √† migrer")
            return 0
        
        # Ins√©rer dans PostgreSQL
        count = 0
        for _, row in logs_data.iterrows():
            log = ActivityLog(
                id=row['id'] if row['id'] else None,
                team_id=row['team_id'],
                action=row['action'],
                details=row['details'],
                created_at=pd.to_datetime(row['created_at']) if row['created_at'] else datetime.utcnow()
            )
            postgres_session.merge(log)
            count += 1
        
        postgres_session.commit()
        print(f"‚úÖ {count} logs d'activit√© migr√©s")
        return count
        
    except Exception as e:
        postgres_session.rollback()
        print(f"‚ùå Erreur migration logs: {e}")
        return 0


def copy_addresses(sqlite_conn, postgres_session):
    """Copier les adresses OSM SQLite ‚Üí PostgreSQL"""
    try:
        # V√©rifier si la table existe
        cursor = sqlite_conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='addresses'
        """)
        if not cursor.fetchone():
            print("‚ÑπÔ∏è Table addresses non pr√©sente dans SQLite")
            return 0
        
        # Lire depuis SQLite
        addresses_data = pd.read_sql_query("""
            SELECT id, street_name, house_number, latitude, longitude, osm_type, created_at 
            FROM addresses 
            ORDER BY created_at
        """, sqlite_conn)
        
        if addresses_data.empty:
            print("‚ÑπÔ∏è Aucune adresse √† migrer")
            return 0
        
        # Ins√©rer dans PostgreSQL
        count = 0
        for _, row in addresses_data.iterrows():
            address = Address(
                id=row['id'] if row['id'] else None,
                street_name=row['street_name'],
                house_number=row['house_number'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                osm_type=row['osm_type'],
                created_at=pd.to_datetime(row['created_at']) if row['created_at'] else datetime.utcnow()
            )
            postgres_session.merge(address)
            count += 1
        
        postgres_session.commit()
        print(f"‚úÖ {count} adresses migr√©es")
        return count
        
    except Exception as e:
        postgres_session.rollback()
        print(f"‚ùå Erreur migration adresses: {e}")
        return 0


def main():
    """Migration compl√®te SQLite ‚Üí PostgreSQL"""
    print("üîÑ D√©but migration SQLite ‚Üí PostgreSQL...")
    
    # Connexions
    sqlite_conn = get_sqlite_connection()
    if not sqlite_conn:
        return False
    
    try:
        # Cr√©er les tables PostgreSQL
        if not create_postgres_tables():
            return False
        
        # Session PostgreSQL
        engine = get_engine()
        Session = sessionmaker(bind=engine)
        postgres_session = Session()
        
        # Migration par table
        total_migrated = 0
        total_migrated += copy_teams(sqlite_conn, postgres_session)
        total_migrated += copy_streets(sqlite_conn, postgres_session)
        total_migrated += copy_notes(sqlite_conn, postgres_session)
        total_migrated += copy_activity_logs(sqlite_conn, postgres_session)
        total_migrated += copy_addresses(sqlite_conn, postgres_session)
        
        postgres_session.close()
        sqlite_conn.close()
        
        print(f"üéâ Migration termin√©e ! {total_migrated} enregistrements migr√©s")
        return True
        
    except Exception as e:
        print(f"‚ùå Erreur g√©n√©rale migration: {e}")
        if 'postgres_session' in locals():
            postgres_session.close()
        sqlite_conn.close()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)