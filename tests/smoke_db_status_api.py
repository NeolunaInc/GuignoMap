import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import sqlite3
from guignomap.db import (
    init_street_status_schema,
    mark_street_in_progress,
    save_checkpoint,
    mark_street_complete,
    get_team_streets_status,
)
conn = sqlite3.connect("guignomap/guigno_map.db")
init_street_status_schema(conn)
mark_street_in_progress(conn, "Rue Test", "A1", "Départ")
save_checkpoint(conn, "Rue Test", "A1", "Porte 125: pas de réponse")
mark_street_complete(conn, "Rue Test", "A1")
rows = get_team_streets_status(conn, "A1")
print("ROWS:", rows)
assert any(r["street_name"] == "Rue Test" and r["status"] == "terminee" for r in rows)
print("OK")
