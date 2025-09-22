import os, sys, sqlite3
from datetime import datetime

# S'assure que la racine du projet est dans le PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from guignomap.db import (
    init_street_status_schema,
    update_street_status,
    get_street_notes_for_team,
    add_street_note,
    get_visited_addresses_for_street,
)

DB_PATH = "guignomap/guigno_map.db"
conn = sqlite3.connect(DB_PATH)
init_street_status_schema(conn)

# 1. Test update_street_status
update_street_status(conn, "Rue Test 2", "en_cours", "B1")

# 2. Ajout de note
add_street_note(conn, "Rue Test 2", "B1", "Maison 12: occupé")

# 3. Récupération des notes
notes = get_street_notes_for_team(conn, "Rue Test 2", "B1")
print("NOTES:", notes)
assert notes, "Les notes devraient contenir au moins une entrée"

# 4. Vérification des adresses visitées
visited = get_visited_addresses_for_street(conn, "Rue Test 2", "B1")
print("VISITED:", visited)  # peut être [] si la table notes n’existe plus

print("OK - toutes les API manquantes répondent")
