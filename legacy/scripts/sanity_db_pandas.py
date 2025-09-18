from sqlalchemy import text
import pandas as pd
import sys, pathlib

# 1) Injecte la racine du repo dans sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 2) Import de get_session() depuis src.database.connection
try:
    from src.database.connection import get_session
except Exception as e:
    raise SystemExit(f"[ERREUR] Import get_session introuvable depuis src.database.connection: {e}")

# 3) Test SELECT 1 + version pandas
try:
    with get_session() as s:
        print("DB OK:", s.execute(text("SELECT 1")).scalar_one())
except Exception as e:
    raise SystemExit(f"[ERREUR] DB SELECT 1 a échoué: {e}")

print("pandas OK:", pd.__version__)