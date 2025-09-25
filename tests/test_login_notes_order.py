import sqlite3
import pytest
from datetime import datetime, timedelta

def setup_temp_db():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE teams (
            id INTEGER PRIMARY KEY,
            name TEXT,
            password_hash TEXT
        );
    """)
    cursor.execute("""
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY,
            team_id INTEGER,
            street_name TEXT,
            created_at TEXT,
            FOREIGN KEY(team_id) REFERENCES teams(id)
        );
    """)
    # Insert team
    cursor.execute("INSERT INTO teams (id, name, password_hash) VALUES (1, 'TeamA', 'hash')")
    # Insert two notes for same street with different timestamps
    now = datetime.now()
    cursor.execute("INSERT INTO notes (team_id, street_name, created_at) VALUES (1, 'Rue Principale', ?)", (now - timedelta(days=1),))
    cursor.execute("INSERT INTO notes (team_id, street_name, created_at) VALUES (1, 'Rue Principale', ?)", (now,))
    conn.commit()
    return conn

def test_checkpoint_order():
    conn = setup_temp_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT street_name, MAX(created_at) as last_created
        FROM notes
        WHERE team_id = ?
        GROUP BY street_name
        ORDER BY last_created DESC
        LIMIT 1
    """, (1,))
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == 'Rue Principale'
    # The most recent timestamp should be returned
    assert result[1] is not None
    conn.close()
