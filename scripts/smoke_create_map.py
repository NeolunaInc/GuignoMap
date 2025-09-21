import sys, pathlib, importlib
import pandas as pd
from importlib.util import spec_from_file_location, module_from_spec

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

mod = None
# Tentatives d'import par paquet (après ajout __init__.py)
for candidate in ("guignomap.app", "src.app"):
    try:
        mod = importlib.import_module(candidate)
        break
    except Exception:
        continue

# Fallback: import direct par chemin
app_path = ROOT / "guignomap" / "app.py"
if mod is None and app_path.exists():
    spec = spec_from_file_location("app_fallback", str(app_path))
    if spec is not None and spec.loader is not None:
        m = module_from_spec(spec)
        spec.loader.exec_module(m)
        mod = m

if mod is None or not hasattr(mod, "create_map"):
    raise SystemExit("[ERREUR] create_map introuvable (guignomap.app/src.app ou fallback fichier)")

# DataFrame minimal conforme à create_map(df, geo)
df = pd.DataFrame([
    {"name": "Rue Test A", "status": "a_faire", "team": "", "notes": "0"},
    {"name": "Rue Test B", "status": "terminee", "team": "EQUIPE1", "notes": "2"},
])

try:
    mod.create_map(df, {})  # geo vide: on valide la boucle DataFrame
    print("create_map(df) OK")
except Exception as e:
    print("create_map(df) FAILED:", e)
    sys.exit(1)