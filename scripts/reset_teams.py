import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.connection import get_session
from sqlalchemy import text
from src.database import operations

TO_DELETE = ["EQUIPE1","EQUIPE2"]
NEW_TEAMS = [("EQUIPE1","Equipe 1","admin123"),
             ("EQUIPE2","Equipe 2","admin123")]

def list_teams(label):
    with get_session() as s:
        rows = s.execute(text("SELECT id,name,active,length(COALESCE(password_hash,'')) ph_len FROM teams ORDER BY id")).fetchall()
        print(f"{label}:")
        for r in rows:
            print("  ", r)

list_teams("Avant suppression")

# Supprimer (sauf ADMIN)
with get_session() as s:
    for tid in TO_DELETE:
        s.execute(text("DELETE FROM teams WHERE id=:id AND id<>'ADMIN'"), {"id": tid})
    s.commit()

list_teams("Après suppression")

# Recréer proprement (nouveau hash)
for tid, name, pwd in NEW_TEAMS:
    ok = operations.create_team(tid, name, pwd)
    print(f"create_team({tid}) ->", ok, "| verify ->", operations.verify_team(tid, pwd))

list_teams("Après recréation")
