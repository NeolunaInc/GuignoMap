"""OSM helpers (stub minimal pour faire tourner l'app).
Remplace-le si tu retrouves la version complète plus tard."""
from pathlib import Path
import json

# fichiers de cache (même noms que ceux souvent vus dans tes projets)
CACHE_FILE = Path("osm_cache.json")
ADDR_CACHE_FILE = Path("osm_addresses.json")

def _read_json(p: Path):
    try:
        if p.exists(): return json.loads(p.read_text(encoding="utf-8"))
    except Exception: pass
    return {}

def _write_json(p: Path, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# Géométries des rues (polylines, etc.)
def build_geometry_cache() -> dict:
    data = _read_json(CACHE_FILE)
    if not data: data = {"meta": {"source": "stub", "items": 0}, "streets": {}}
    _write_json(CACHE_FILE, data)
    return data

def load_geometry_cache() -> dict:
    return _read_json(CACHE_FILE)

# Adresses par rue (si l'app en a besoin)
def build_addresses_cache() -> dict:
    data = _read_json(ADDR_CACHE_FILE)
    if not data: data = {"meta": {"source": "stub", "items": 0}, "addresses": {}}
    _write_json(ADDR_CACHE_FILE, data)
    return data

def load_addresses_cache() -> dict:
    return _read_json(ADDR_CACHE_FILE)

def generate_streets_csv(streets):
    """Stub: génère CSV des rues"""
    print(f"Stub osm: generate_streets_csv for {len(streets)} streets")
    return "rue,secteur\n" + "\n".join(f"{s},secteur" for s in streets)
